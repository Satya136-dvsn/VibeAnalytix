"""
Celery tasks for pipeline orchestration.

Main pipeline task chains:
ingestion → parsing → analysis → knowledge_building → embedding → explanation → cleanup
"""

import traceback
from uuid import UUID

from sqlalchemy import update

from app.celery_app import celery_app
from app.database import async_session_maker
from app.models import Job
from app.ingestion import ingest_github, ingest_zip, IngestionError
from app.parser import parse_repository
from app.analysis import run_analysis
from app.knowledge_builder import (
    build_knowledge,
    generate_and_store_embeddings,
)
from app.explanation_engine import generate_explanations
from app.diagram_generator import generate_all_diagrams
from app.cleanup import (
    cleanup_on_completion,
    update_job_progress,
    mark_job_failed,
    timeout_watchdog,
)


@celery_app.task(bind=True, name="app.tasks.run_pipeline")
def run_pipeline(
    self,
    job_id: str,
    source_type: str,
    source_ref: str,
) -> dict:
    """
    Orchestrate complete analysis pipeline for a job.

    Pipeline stages:
    1. Ingestion (clone repo or extract ZIP)
    2. Parsing (generate ASTs)
    3. Analysis (3-pass analysis)
    4. Knowledge Building (hierarchical summaries)
    5. Embedding (pgvector storage)
    6. Explanation (OpenAI generation)
    7. Cleanup (delete temp files)

    Args:
        job_id: Unique job identifier
        source_type: 'github' or 'zip'
        source_ref: GitHub URL or ZIP path

    Returns:
        Result dictionary
    """
    import asyncio

    # Run async pipeline
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            _run_pipeline_async(job_id, source_type, source_ref)
        )
        return result
    finally:
        loop.close()


async def _run_pipeline_async(
    job_id: str,
    source_type: str,
    source_ref: str,
) -> dict:
    """Async implementation of pipeline orchestration."""

    temp_dir = None
    session = None

    try:
        # Get database session
        session = async_session_maker()

        # ============ Stage 1: Ingestion ============
        await update_job_progress(job_id, "ingestion", 5, session)

        try:
            if source_type == "github":
                ingestion_result = await ingest_github(job_id, source_ref)
            elif source_type == "zip":
                import base64
                file_bytes = base64.b64decode(source_ref)
                ingestion_result = await ingest_zip(job_id, file_bytes)
            else:
                raise ValueError(f"Invalid source type: {source_type}")

            temp_dir = ingestion_result.temp_dir
            await update_job_progress(job_id, "ingestion", 15, session)

        except IngestionError as e:
            await mark_job_failed(job_id, f"Ingestion failed: {str(e)}", session)
            return {"success": False, "error": str(e)}

        # ============ Stage 2: Parsing ============
        await update_job_progress(job_id, "parsing", 20, session)

        try:
            parsed_files = await parse_repository(temp_dir)

            if not parsed_files:
                await mark_job_failed(job_id, "No source files found in repository", session)
                return {"success": False, "error": "No source files found"}

            await update_job_progress(job_id, "parsing", 30, session)

        except Exception as e:
            await mark_job_failed(job_id, f"Parsing failed: {str(e)}", session)
            return {"success": False, "error": str(e)}

        # ============ Stage 3: Analysis (3-pass) ============
        await update_job_progress(job_id, "analysis_pass1", 35, session)
        await update_job_progress(job_id, "analysis_pass2", 45, session)

        try:
            analysis = await run_analysis(parsed_files, temp_dir)
            await update_job_progress(job_id, "analysis_pass3", 60, session)

        except Exception as e:
            await mark_job_failed(job_id, f"Analysis failed: {str(e)}", session)
            return {"success": False, "error": str(e)}

        # ============ Stage 4: Knowledge Building ============
        await update_job_progress(job_id, "knowledge_building", 65, session)

        try:
            knowledge = await build_knowledge(parsed_files, analysis)
            await update_job_progress(job_id, "knowledge_building", 70, session)

        except Exception as e:
            await mark_job_failed(job_id, f"Knowledge building failed: {str(e)}", session)
            return {"success": False, "error": str(e)}

        # ============ Stage 5: Embedding ============
        await update_job_progress(job_id, "embedding", 75, session)

        try:
            await generate_and_store_embeddings(job_id, knowledge, session)
            await update_job_progress(job_id, "embedding", 80, session)

        except Exception as e:
            print(f"Error generating embeddings: {e}")
            # Don't fail the job on embedding errors
            await update_job_progress(job_id, "embedding", 80, session)

        # ============ Stage 6: Explanation ============
        await update_job_progress(job_id, "explanation", 85, session)

        try:
            explanations = await generate_explanations(job_id, knowledge, session)

            # Store explanations in database
            from app.models import ProjectResult

            project_result = ProjectResult(
                job_id=UUID(job_id),
                project_summary=explanations.project_summary,
                overview_explanation=explanations.overview_explanation,
                flow_explanation=explanations.flow_explanation,
                entry_points=analysis.entry_points,
                dependency_graph=analysis.dependency_graph,
                circular_deps=analysis.circular_deps,
                external_deps=analysis.external_deps,
                per_file_explanations=explanations.per_file_explanations,
            )
            session.add(project_result)
            await session.commit()

            await update_job_progress(job_id, "explanation", 90, session)

        except Exception as e:
            print(f"Error generating explanations: {e}")
            # Don't fail the job on explanation errors
            await update_job_progress(job_id, "explanation", 90, session)

        # ============ Stage 6.5: Architecture Diagram Generation ============
        await update_job_progress(job_id, "diagram_generation", 92, session)

        try:
            diagrams = generate_all_diagrams(parsed_files, analysis, knowledge)

            # Also fetch optional GitHub repo metadata (no API key required)
            repo_metadata = None
            if source_type == "github":
                try:
                    from app.github_metadata import fetch_repo_metadata
                    meta = await fetch_repo_metadata(source_ref)
                    repo_metadata = meta.to_dict() if meta else None
                except Exception as meta_err:
                    print(f"[PIPELINE] GitHub metadata fetch skipped: {meta_err}")

            # Update project_result with diagrams and metadata
            from app.models import ProjectResult
            from sqlalchemy import select

            pr_stmt = select(ProjectResult).where(ProjectResult.job_id == UUID(job_id))
            pr_row = await session.execute(pr_stmt)
            project_result_existing = pr_row.scalar_one_or_none()

            if project_result_existing:
                project_result_existing.architecture_diagrams = diagrams
                if repo_metadata:
                    project_result_existing.repo_metadata = repo_metadata
                await session.commit()

            await update_job_progress(job_id, "diagram_generation", 95, session)

        except Exception as e:
            print(f"[PIPELINE] Diagram generation error (non-fatal): {e}")
            await update_job_progress(job_id, "diagram_generation", 95, session)

        # ============ Stage 7: Cleanup ============
        await update_job_progress(job_id, "cleanup", 98, session)

        try:
            await cleanup_on_completion(job_id, temp_dir, session)
        except Exception as e:
            print(f"Error during cleanup: {e}")

        # Mark job as completed
        stmt = (
            update(Job)
            .where(Job.id == UUID(job_id))
            .values(status="completed", progress_pct=100)
        )
        await session.execute(stmt)
        await session.commit()

        return {"success": True, "job_id": job_id}

    except Exception as e:
        print(f"[PIPELINE] Unexpected error in pipeline: {e}")
        traceback.print_exc()

        if session:
            error_msg = f"Pipeline error: {str(e)}"
            await mark_job_failed(job_id, error_msg, session)

        return {"success": False, "error": str(e)}

    finally:
        if session:
            await session.close()

        # Always attempt cleanup
        if temp_dir and temp_dir.exists():
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"[PIPELINE] Error cleaning up {temp_dir}: {e}")


@celery_app.task(bind=True, name="app.tasks.cleanup_watchdog")
def cleanup_watchdog_task(self):
    """
    Watchdog task to timeout jobs stuck in progress > 30 minutes.

    Runs periodically via Celery beat (every 5 minutes).
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        session = async_session_maker()
        loop.run_until_complete(timeout_watchdog(session))
    finally:
        loop.close()
