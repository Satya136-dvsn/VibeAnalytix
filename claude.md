# Claude's Roadmap to Complete VibeAnalytix

Welcome, Claude! This document is your comprehensive instruction guide for understanding, verifying, and completing the **VibeAnalytix** project. 

VibeAnalytix is a production-grade, AI-powered code understanding engine. This project is built on a "deliberate reasoning" philosophy where analysis must be complete before any AI explanations are generated.

---

## **Step 0: Read the Project Source of Truth (CRITICAL)**

Before you start writing any code, you **MUST** read these three files to understand the project's requirements, architectural design, and current progress:

1.  **[requirements.md](file:///c:/VibeAnalytix/.kiro/specs/vibeanalytix/requirements.md)**: Defines the 13 high-level requirements and acceptance criteria for ingestion, parsing, analysis, knowledge building, explanation generation, and more.
2.  **[design.md](file:///c:/VibeAnalytix/.kiro/specs/vibeanalytix/design.md)**: The architectural blueprint. It includes:
    *   System architecture diagrams.
    *   Component interfaces and responsibilities.
    *   **30 Correctness Properties**: A formal checklist for system behavior (e.g., Property 2: ZIP Path Traversal Containment).
    *   Database schema and API error handling specifications.
3.  **[tasks.md](file:///c:/VibeAnalytix/.kiro/specs/vibeanalytix/tasks.md)**: A detailed, 15-phase implementation plan. Use this to cross-reference with the codebase to identify what's actually finished and what's pending.

---

## **Step 1: Understand What Was Done**

To understand the current state of the project, perform the following:

1.  **Compare Tasks with Implementation**: Check [tasks.md](file:///c:/VibeAnalytix/.kiro/specs/vibeanalytix/tasks.md) and [IMPLEMENTATION.md](file:///c:/VibeAnalytix/IMPLEMENTATION.md). While `IMPLEMENTATION.md` says the project is 100% complete, you must verify this by checking the code against the **30 Correctness Properties** in `design.md`.
2.  **Verify Core Components**:
    *   **Ingestion**: Check [ingestion.py](file:///c:/VibeAnalytix/backend/app/ingestion.py) for path traversal and binary rejection.
    *   **Analysis**: Check [analysis.py](file:///c:/VibeAnalytix/backend/app/analysis.py) for the 3-pass logic (Structural, Dependency, Context).
    *   **Explanation**: Check [explanation_engine.py](file:///c:/VibeAnalytix/backend/app/explanation_engine.py). *Note: This often has mock logic that needs actual OpenAI API integration.*
    *   **Frontend**: Check [page.tsx](file:///c:/VibeAnalytix/frontend/app/jobs/[id]/page.tsx) for 3-second polling and the 3-tab results view.

---

## **Step 2: Complete the Project**

Your goal is to ensure the system is production-ready and fully satisfies all requirements in [requirements.md](file:///c:/VibeAnalytix/.kiro/specs/vibeanalytix/requirements.md) and properties in [design.md](file:///c:/VibeAnalytix/.kiro/specs/vibeanalytix/design.md).

### **Common Areas for Completion/Refinement:**

1.  **AI Integration**: Replace any mock code in [explanation_engine.py](file:///c:/VibeAnalytix/backend/app/explanation_engine.py) with actual `AsyncOpenAI` calls to `gpt-4o`. Implement top-10 semantic retrieval context.
2.  **Security Hardening**: Verify all 30 properties, especially:
    *   **Property 2**: ZIP Path Traversal protection.
    *   **Property 28**: Executable binary rejection.
    *   **Property 24-26**: JWT authentication and authorization enforcement.
3.  **Error Handling**: Ensure API responses match the consistent error envelope defined in `design.md`.
4.  **Verification (Testing)**:
    *   Run `pytest tests/unit/` and `pytest tests/property/`.
    *   If any of the 30 properties lack a property-based test (using `Hypothesis`), create it in `tests/property/`.
    *   Ensure the integration test `tests/integration/test_pipeline.py` passes end-to-end.

---

## **Key Reference Checklist**

*   **Technology Stack**: FastAPI, Celery, Redis, PostgreSQL + pgvector, Next.js, OpenAI GPT-4.
*   **Pipeline Stages**: `ingestion` → `parsing` → `analysis` → `knowledge_building` → `embedding` → `explanation` → `cleanup`.
*   **Correctness Benchmark**: 30 Properties in [design.md](file:///c:/VibeAnalytix/.kiro/specs/vibeanalytix/design.md).
*   **Infrastructure**: [docker-compose.yml](file:///c:/VibeAnalytix/docker-compose.yml) is the source of truth for services.

Good luck, Claude! Use the specs as your guide and ensure VibeAnalytix is robust and enterprise-ready.
