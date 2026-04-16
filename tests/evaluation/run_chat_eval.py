"""
Lightweight evaluation harness for repository Q&A quality.

Usage:
  python tests/evaluation/run_chat_eval.py \
    --base-url http://localhost:8000 \
    --job-id <job_id> \
    --token <jwt> \
    --dataset tests/evaluation/sample_eval_set.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class EvalCase:
    question: str
    must_include_terms: list[str]
    expected_files: list[str]


def load_dataset(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        payload = json.loads(line)
        cases.append(
            EvalCase(
                question=payload["question"],
                must_include_terms=list(payload.get("must_include_terms", [])),
                expected_files=list(payload.get("expected_files", [])),
            )
        )
    return cases


def _contains_all_terms(answer: str, terms: list[str]) -> bool:
    text = answer.lower()
    return all(term.lower() in text for term in terms)


def _citation_coverage(sources: list[dict], expected_files: list[str]) -> float:
    if not expected_files:
        return 1.0
    cited = {str(s.get("file", "")) for s in sources}
    hits = sum(1 for f in expected_files if f in cited)
    return hits / max(1, len(expected_files))


async def run_eval(base_url: str, job_id: str, token: str, cases: list[EvalCase]) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    endpoint = f"{base_url.rstrip('/')}/api/v1/jobs/{job_id}/chat"

    total = len(cases)
    term_pass = 0
    abstain_count = 0
    citation_scores: list[float] = []
    confidence_values: list[float] = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for idx, case in enumerate(cases, start=1):
            response = await client.post(endpoint, headers=headers, json={"query": case.question})
            response.raise_for_status()
            payload = response.json()

            answer = str(payload.get("answer", ""))
            sources = payload.get("sources", []) or []
            abstained = bool(payload.get("abstained", False))
            confidence = float(payload.get("confidence", 0.0))

            if _contains_all_terms(answer, case.must_include_terms):
                term_pass += 1
            if abstained:
                abstain_count += 1

            citation_scores.append(_citation_coverage(sources, case.expected_files))
            confidence_values.append(confidence)

            print(f"[{idx}/{total}] confidence={confidence:.3f} abstained={abstained} question={case.question}")

    term_accuracy = term_pass / max(1, total)
    avg_citation = sum(citation_scores) / max(1, len(citation_scores))
    avg_conf = sum(confidence_values) / max(1, len(confidence_values))

    print("\n=== Evaluation Summary ===")
    print(f"Cases: {total}")
    print(f"Term accuracy: {term_accuracy:.3f}")
    print(f"Avg citation coverage: {avg_citation:.3f}")
    print(f"Avg confidence: {avg_conf:.3f}")
    print(f"Abstain rate: {abstain_count / max(1, total):.3f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run chat quality evaluation against a completed job.")
    parser.add_argument("--base-url", required=True, help="API base URL, e.g. http://localhost:8000")
    parser.add_argument("--job-id", required=True, help="Completed job UUID")
    parser.add_argument("--token", required=True, help="Bearer token for authenticated API access")
    parser.add_argument("--dataset", required=True, help="Path to JSONL evaluation dataset")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    dataset = load_dataset(Path(args.dataset))
    asyncio.run(run_eval(args.base_url, args.job_id, args.token, dataset))
