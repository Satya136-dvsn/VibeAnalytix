# Implementation Plan: VibeAnalytix

## Overview

Implement VibeAnalytix as a FastAPI + Celery backend with a Next.js frontend. The pipeline runs asynchronously: ingestion → parsing → analysis → knowledge building → embedding → explanation → cleanup. All heavy work runs in Celery workers; the API is non-blocking.

## Tasks

- [x] 1. Project scaffolding and infrastructure
  - [x] 1.1 Create monorepo directory structure
    - Create `backend/`, `frontend/`, `tests/` directories
    - Add `backend/pyproject.toml` (or `requirements.txt`) with FastAPI, Celery, Redis, SQLAlchemy, asyncpg, tree-sitter, openai, hypothesis dependencies
    - Add `frontend/package.json` with Next.js, TypeScript, fast-check dependencies
    - _Requirements: 9.2, 9.6_

  - [x] 1.2 Create Docker and docker-compose setup
    - Write `Dockerfile` for backend (Python 3.12, install deps)
    - Write `Dockerfile` for frontend (Node 20, Next.js build)
    - Write `docker-compose.yml` with services: `api`, `worker`, `postgres` (with pgvector), `redis`
    - Add resource constraints on worker containers (CPU/memory limits)
    - _Requirements: 9.2, 9.6, 12.3_

  - [x] 1.3 Create environment configuration
    - Add `.env.example` with all required variables: `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `JWT_SECRET`, `MAX_REPO_SIZE_MB`, `MAX_ZIP_SIZE_MB`
    - Add `backend/app/config.py` using pydantic-settings to load and validate env vars
    - _Requirements: 1.5_

- [x] 2. Database schema and migrations
  - [x] 2.1 Set up Alembic and create initial migration
    - Initialize Alembic in `backend/`
    - Create migration for all tables: `users`, `jobs`, `parsed_files`, `function_summaries`, `file_summaries`, `module_summaries`, `project_results`
    - Enable pgvector extension (`CREATE EXTENSION IF NOT EXISTS vector`)
    - Add ivfflat index on `function_summaries.embedding`
    - _Requirements: 7.2, 9.1_

  - [x] 2.2 Create SQLAlchemy ORM models
    - Write `backend/app/models.py` with ORM classes for all tables matching the schema in the design
    - Add `AsyncSession` factory in `backend/app/database.py`
    - _Requirements: 9.1, 9.4, 9.5_

- [x] 3. Authentication
  - [x] 3.1 Implement register and login endpoints
    - Write `backend/app/routers/auth.py` with `POST /api/v1/auth/register` and `POST /api/v1/auth/login`
    - Hash passwords with bcrypt; issue JWT (24-hour expiry) on login
    - Write `backend/app/auth.py` with `get_current_user` dependency that validates JWT and returns user
    - Return HTTP 401 for invalid/expired tokens on all protected routes
    - _Requirements: 11.1, 11.2, 11.4_

  - [x] 3.2 Write property test for authentication enforcement (Property 24)
    - **Property 24: Authentication Enforcement**
    - **Validates: Requirements 11.1, 11.2**
    - For any request to a protected endpoint without a valid JWT, assert HTTP 401 is returned
    - File: `tests/property/test_api_props.py`

  - [x] 3.3 Write property test for JWT expiry (Property 26)
    - **Property 26: JWT Expiry**
    - **Validates: Requirements 11.4**
    - For any JWT with issuance time > 24 hours ago, assert the system returns HTTP 401
    - File: `tests/property/test_api_props.py`

  - [x] 3.4 Write property test for authorization enforcement (Property 25)
    - **Property 25: Authorization Enforcement**
    - **Validates: Requirements 11.3**
    - For any user A requesting results for a job owned by user B (A ≠ B), assert HTTP 403
    - File: `tests/property/test_api_props.py`

- [x] 4. Ingestion Service
  - [x] 4.1 Implement GitHub URL ingestion
    - Write `backend/app/ingestion.py` with `ingest_github(job_id, url) -> IngestionResult`
    - Validate HTTPS github.com URL format; reject SSH and non-GitHub URLs with descriptive error
    - Shallow-clone via `git clone --depth 1` into a temp dir
    - Enforce configurable 500 MB post-clone size limit; delete partial clone on rejection
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 4.2 Implement ZIP upload ingestion
    - Add `ingest_zip(job_id, file_bytes) -> IngestionResult` to `backend/app/ingestion.py`
    - Validate `.zip` extension and `PK\x03\x04` magic bytes before extraction
    - Enforce configurable 100 MB pre-extraction size limit
    - Extract with path sanitization: strip `../` sequences, resolve all paths to temp dir
    - Reject archives containing `.exe`, `.dll`, `.so`, `.bin` files
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 12.1, 12.4_

  - [x] 4.3 Write property test for invalid URL rejection (Property 1)
    - **Property 1: Invalid URL Rejection**
    - **Validates: Requirements 1.2, 1.4**
    - For any malformed, SSH, or non-github.com URL, assert error returned and no temp dir created
    - File: `tests/property/test_ingestion_props.py`

  - [x] 4.4 Write property test for ZIP path traversal containment (Property 2)
    - **Property 2: ZIP Path Traversal Containment**
    - **Validates: Requirements 2.4**
    - For any ZIP with `../` entries, assert all extracted files reside within the temp dir
    - File: `tests/property/test_ingestion_props.py`

  - [x] 4.5 Write property test for invalid ZIP rejection (Property 3)
    - **Property 3: Invalid ZIP Rejection**
    - **Validates: Requirements 2.2, 12.1**
    - For any byte sequence not starting with ZIP magic bytes or lacking `.zip` extension, assert rejection
    - File: `tests/property/test_ingestion_props.py`

  - [x] 4.6 Write property test for executable binary rejection (Property 28)
    - **Property 28: Executable Binary Rejection**
    - **Validates: Requirements 12.4**
    - For any archive containing `.exe`, `.dll`, `.so`, or `.bin` files, assert rejection
    - File: `tests/property/test_ingestion_props.py`

  - [x] 4.7 Write unit tests for ingestion
    - Test valid GitHub URL acceptance, size limit enforcement, ZIP extraction, path sanitization
    - File: `tests/unit/test_ingestion.py`

- [x] 5. Parser
  - [x] 5.1 Implement language detection and file tree builder
    - Write `backend/app/parser.py` with language detection per file (extension + content heuristics)
    - Support Python, JavaScript, TypeScript, Java, Go, C, C++
    - Build hierarchical `FileTreeNode` structure from the temp directory
    - Log and skip files that fail parsing; continue with remaining files
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 5.2 Implement tree-sitter AST extraction
    - Add tree-sitter grammar initialization for all 7 supported languages
    - Implement `parse_repository(temp_dir) -> list[ParsedFile]`
    - Extract from each AST: function defs, class defs, imports/exports, top-level variable declarations
    - Populate `ParsedFile.parse_error` for files that fail; do not abort the batch
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 5.3 Implement Pretty_Printer for AST round-trip
    - Implement `pretty_print(ast, language) -> str` that serializes a tree-sitter AST back to normalized source
    - _Requirements: 4.4, 4.5_

  - [x] 5.4 Write property test for language detection accuracy (Property 4)
    - **Property 4: Language Detection Accuracy**
    - **Validates: Requirements 3.1, 3.4**
    - For any source file with a known language, assert the parser detects the correct language
    - File: `tests/property/test_parser_props.py`

  - [x] 5.5 Write property test for file tree completeness (Property 5)
    - **Property 5: File Tree Completeness**
    - **Validates: Requirements 3.2**
    - For any directory structure, assert the file tree contains exactly the same paths as the filesystem
    - File: `tests/property/test_parser_props.py`

  - [x] 5.6 Write property test for parser resilience (Property 6)
    - **Property 6: Parser Resilience**
    - **Validates: Requirements 3.3, 4.2**
    - For any collection with some invalid files, assert valid files parse successfully and invalid ones produce error records
    - File: `tests/property/test_parser_props.py`

  - [x] 5.7 Write property test for AST extraction completeness (Property 7)
    - **Property 7: AST Extraction Completeness**
    - **Validates: Requirements 4.1, 4.3**
    - For any valid source file, assert all functions, classes, imports, and top-level vars are extracted
    - File: `tests/property/test_parser_props.py`

  - [x] 5.8 Write property test for AST round-trip (Property 8)
    - **Property 8: AST Round-Trip**
    - **Validates: Requirements 4.4, 4.5**
    - For any valid source file, assert parse → pretty_print → parse produces an equivalent AST
    - File: `tests/property/test_parser_props.py`

  - [x] 5.9 Write unit tests for parser
    - One parsing example per supported language (Python, JS, TS, Java, Go, C, C++)
    - File: `tests/unit/test_parser.py`

- [x] 6. Analysis Engine
  - [x] 6.1 Implement Pass 1 — Structural Mapping
    - Write `backend/app/analysis.py` with `run_analysis(parsed_files) -> AnalysisResult`
    - Pass 1: build hierarchical file/directory tree; identify entry point files by language convention
    - _Requirements: 5.1, 5.5_

  - [x] 6.2 Implement Pass 2 — Dependency Detection
    - Pass 2: build directed dependency graph from import/require statements
    - Detect circular dependencies using DFS cycle detection
    - Catalog external library dependencies
    - _Requirements: 5.2, 5.3, 5.4_

  - [x] 6.3 Implement Pass 3 — Context Refinement
    - Pass 3: resolve cross-file semantic relationships; annotate functions with callers/callees across files
    - Enrich dependency graph with semantic edges
    - _Requirements: 5.5_

  - [x] 6.4 Write property test for dependency graph completeness (Property 9)
    - **Property 9: Dependency Graph Completeness**
    - **Validates: Requirements 5.2**
    - For any set of files with known imports, assert every import relationship appears as an edge in the graph
    - File: `tests/property/test_analysis_props.py`

  - [x] 6.5 Write property test for circular dependency detection (Property 10)
    - **Property 10: Circular Dependency Detection**
    - **Validates: Requirements 5.3**
    - For any dependency graph containing a cycle, assert that cycle appears in the analysis output
    - File: `tests/property/test_analysis_props.py`

  - [x] 6.6 Write property test for external dependency completeness (Property 11)
    - **Property 11: External Dependency Completeness**
    - **Validates: Requirements 5.4**
    - For any files with known external imports, assert all external deps appear in the output list
    - File: `tests/property/test_analysis_props.py`

  - [x] 6.7 Write unit tests for analysis engine
    - Test entry point detection, circular dep recording, three-pass sequencing
    - File: `tests/unit/test_analysis.py`

- [x] 7. Checkpoint — All tests implemented

- [x] 8. Knowledge Builder
  - [x] 8.1 Implement hierarchical summarization
    - Write `backend/app/knowledge_builder.py` with `build_knowledge(parsed_files, analysis) -> KnowledgeGraph`
    - Generate function-level summaries (chunk functions > 200 lines into ≤200-line segments)
    - Aggregate to file-level, module-level (per directory), and single project-level summaries
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 8.2 Implement embedding generation and pgvector storage
    - Implement `generate_and_store_embeddings(job_id, knowledge, db)` using OpenAI `text-embedding-3-small`
    - Store embedding vector + file_path, function_name, line_start, line_end in `function_summaries` table
    - Retry up to 3 times with exponential backoff (1s, 2s, 4s) on API errors
    - Skip individual functions after 3 failed retries; mark job failed if > 50% of functions fail
    - _Requirements: 7.1, 7.2_

  - [x] 8.3 Write property test for knowledge hierarchy completeness (Property 12)
    - **Property 12: Knowledge Hierarchy Completeness**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**
    - For any set of parsed files, assert function/file/module/project summaries are all produced
    - File: `tests/property/test_knowledge_props.py`

  - [x] 8.4 Write property test for function chunking bound (Property 13)
    - **Property 13: Function Chunking Bound**
    - **Validates: Requirements 6.5**
    - For any function body > 200 lines, assert every chunk contains at most 200 lines
    - File: `tests/property/test_knowledge_props.py`

  - [x] 8.5 Write property test for embedding storage round-trip (Property 14)
    - **Property 14: Embedding Storage Round-Trip**
    - **Validates: Requirements 7.1, 7.2**
    - For any function summary, after storing its embedding, assert querying by job_id+function_name returns the same vector and metadata
    - File: `tests/property/test_knowledge_props.py`

  - [x] 8.6 Write property test for semantic retrieval count (Property 15)
    - **Property 15: Semantic Retrieval Count**
    - **Validates: Requirements 7.3**
    - For any query embedding with N ≥ 10 stored embeddings, assert exactly 10 results returned ordered by cosine similarity
    - File: `tests/property/test_knowledge_props.py`

  - [x] 8.7 Write unit tests for knowledge builder
    - Test chunking logic, aggregation hierarchy, embedding retry behavior
    - File: `tests/unit/test_knowledge_builder.py`

- [x] 9. Explanation Engine
  - [x] 9.1 Implement semantic retrieval and prompt construction
    - Write `backend/app/explanation_engine.py`
    - Implement pgvector cosine similarity query to retrieve top-10 semantically similar embeddings
    - Construct prompts with retrieved context + hierarchical summaries for each explanation type
    - _Requirements: 7.3, 8.1, 8.2, 8.3, 8.4_

  - [x] 9.2 Implement OpenAI chat completions with retry logic
    - Call `gpt-4o` with structured output schema for: project overview, per-file explanations, execution flow
    - Retry up to 3 times with exponential backoff on API errors; mark job failed after 3 failures
    - Store partial explanations as they complete; store final `ExplanationSet` in `project_results`
    - _Requirements: 8.1, 8.2, 8.3, 8.5_

  - [x] 9.3 Write property test for per-file explanation completeness (Property 16)
    - **Property 16: Per-File Explanation Completeness**
    - **Validates: Requirements 8.2**
    - For any set of source files, assert every file has a corresponding non-empty explanation in the result
    - File: `tests/property/test_explanation_props.py`

  - [x] 9.4 Write property test for OpenAI retry behavior (Property 17)
    - **Property 17: OpenAI Retry Behavior**
    - **Validates: Requirements 8.5**
    - For any failing OpenAI call, assert exactly 3 retries with each delay greater than the previous
    - File: `tests/property/test_explanation_props.py`

  - [x] 9.5 Write unit tests for explanation engine
    - Test project overview existence, flow explanation existence, per-file explanation generation
    - File: `tests/unit/test_explanation_engine.py`

- [x] 10. Celery pipeline wiring and job orchestration
  - [x] 10.1 Create Celery app and task chain
    - Write `backend/app/celery_app.py` configuring Celery with Redis broker
    - Write `backend/app/tasks.py` with a single `run_pipeline` Celery task that chains: ingest → parse → analyze → build_knowledge → embed → explain → cleanup
    - Update `jobs.current_stage` and `jobs.progress_pct` at each stage transition per the progress mapping in the design
    - _Requirements: 9.2, 9.3, 9.8_

  - [x] 10.2 Implement Cleanup Service and timeout watchdog
    - Write `backend/app/cleanup.py` with `cleanup_job(job_id, temp_dir)` that deletes the temp dir and logs job_id, timestamp, bytes_freed
    - Add Celery beat task `watchdog` that runs every 5 minutes: marks jobs stuck in `in_progress` > 30 minutes as `failed` with timeout error, then triggers cleanup
    - _Requirements: 13.1, 13.2, 13.3_

  - [x] 10.3 Write property test for cleanup after terminal state (Property 29)
    - **Property 29: Cleanup After Terminal State**
    - **Validates: Requirements 13.1**
    - For any job reaching "completed" or "failed", assert the temp directory no longer exists after cleanup
    - File: `tests/property/test_cleanup_props.py`

  - [x] 10.4 Write property test for timeout watchdog (Property 30)
    - **Property 30: Timeout Watchdog**
    - **Validates: Requirements 13.2**
    - For any job in "in_progress" > 30 minutes, assert it transitions to "failed" with a timeout error message
    - File: `tests/property/test_cleanup_props.py`

  - [x] 10.5 Write unit tests for cleanup service
    - Test temp dir deletion, logging output, watchdog transition logic
    - File: `tests/unit/test_cleanup.py`

- [x] 11. FastAPI REST API
  - [x] 11.1 Implement job submission endpoint
    - Write `backend/app/routers/jobs.py` with `POST /api/v1/jobs`
    - Accept GitHub URL or ZIP multipart upload; validate input; create job record; enqueue `run_pipeline` task
    - Return 202 `{ job_id }` within 2 seconds
    - Support optional `Idempotency-Key` header: return existing job if same key used within 24 hours
    - _Requirements: 9.1, 9.2_

  - [x] 11.2 Implement job status and results endpoints
    - Add `GET /api/v1/jobs/{job_id}/status` returning `{ stage, progress_pct, status, error_message }`
    - Add `GET /api/v1/jobs/{job_id}/results` returning the full `ExplanationSet` + file tree + dependency graph
    - Add `POST /api/v1/jobs/{job_id}/retry` that re-enqueues a failed job
    - Enforce ownership check: return 403 if requesting user ≠ job owner
    - _Requirements: 9.3, 9.4, 9.5, 10.5, 11.3_

  - [x] 11.3 Implement rate limiting middleware
    - Add Redis sliding-window rate limiter: 10 job submissions per user per hour
    - Return appropriate error response (429) on limit exceeded
    - _Requirements: 12.2_

  - [x] 11.4 Add structured error response envelope
    - Add FastAPI exception handlers that return `{ "error": { "code", "message", "details" } }` for all error cases
    - _Requirements: 1.2, 2.2, 9.5_

  - [x] 11.5 Write property test for job creation returns ID (Property 18)
    - **Property 18: Job Creation Returns ID**
    - **Validates: Requirements 9.1**
    - For any valid job submission, assert a job record is created and job_id is returned
    - File: `tests/property/test_api_props.py`

  - [x] 11.6 Write property test for job status response shape (Property 19)
    - **Property 19: Job Status Response Shape**
    - **Validates: Requirements 9.3**
    - For any in-progress job, assert status response contains non-null current_stage and progress_pct in [0, 100]
    - File: `tests/property/test_api_props.py`

  - [x] 11.7 Write property test for job terminal state correctness (Property 20)
    - **Property 20: Job Terminal State Correctness**
    - **Validates: Requirements 9.4, 9.5**
    - For any completed job assert status="completed"; for any failed job assert status="failed" and error_message non-empty
    - File: `tests/property/test_api_props.py`

  - [x] 11.8 Write property test for job isolation (Property 21)
    - **Property 21: Job Isolation**
    - **Validates: Requirements 9.7**
    - For any set of concurrent jobs where one fails, assert remaining jobs reach their terminal states independently
    - File: `tests/property/test_api_props.py`

  - [x] 11.9 Write property test for rate limit enforcement (Property 27)
    - **Property 27: Rate Limit Enforcement**
    - **Validates: Requirements 12.2**
    - For any user who has submitted 10 jobs in the current hour, assert the 11th submission is rejected
    - File: `tests/property/test_api_props.py`

  - [x] 11.10 Write unit tests for API auth endpoints
    - Test register, login, JWT issuance, protected endpoint access
    - File: `tests/unit/test_api_auth.py`

- [x] 12. Checkpoint — All backend tests implemented

- [x] 13. Next.js frontend — submission and job pages
  - [x] 13.1 Implement submission form page (`/`)
    - Create `frontend/app/page.tsx` with a form accepting GitHub URL (text input) or ZIP file upload
    - On submit: call `POST /api/v1/jobs` with JWT; redirect to `/jobs/[id]` on 202 response
    - Display validation errors inline
    - _Requirements: 1.1, 2.1, 10.1_

  - [x] 13.2 Implement job progress polling
    - Create `frontend/app/jobs/[id]/page.tsx`
    - Poll `GET /api/v1/jobs/{id}/status` every 3 seconds while job is in progress; stop on terminal state
    - Display current stage and progress percentage during polling
    - _Requirements: 9.3, 10.4_

  - [x] 13.3 Implement three-tab results view
    - Add Overview, Structure, and Flow tabs rendered when job status is "completed"
    - Overview tab: project summary, key technologies, architecture narrative
    - Structure tab: file/folder tree (left panel) + per-file explanation (right panel, loads within 500ms on file select)
    - Flow tab: execution flow narrative with entry point highlighting
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 13.4 Implement progressive rendering and failed state
    - Render Overview tab as soon as project summary is available, before full job completion
    - Display error message and retry button when job status is "failed"
    - _Requirements: 10.5, 10.6_

  - [x] 13.5 Write property test for polling interval bound (Property 22)
    - **Property 22: Polling Interval Bound**
    - **Validates: Requirements 10.4**
    - For any in-progress job in the UI, assert the interval between consecutive polls is at least 3 seconds
    - File: `tests/property/test_api_props.py`

  - [x] 13.6 Write property test for progressive rendering (Property 23)
    - **Property 23: Progressive Rendering**
    - **Validates: Requirements 10.6**
    - For any job where project summary is available but per-file explanations are not, assert Overview tab renders without waiting for full completion
    - File: `tests/property/test_api_props.py`

  - [x] 13.7 Write unit tests for results tabs
    - Test three-tab rendering with completed job data
    - Test failed job UI: error message display and retry button
    - Test file selection → explanation display in right panel
    - _Requirements covered by property tests in test_api_props.py_

- [x] 14. Integration tests
  - [x] 14.1 Write end-to-end pipeline integration test
    - Create `tests/integration/test_pipeline.py`
    - Use a small synthetic repository (< 50 files) to run the full pipeline
    - Assert job transitions through all stages to "completed"
    - Assert cleanup removes the temp directory after completion
    - Assert JWT authentication and authorization on all protected endpoints
    - _Requirements: 9.2, 9.4, 11.1, 11.2, 11.3, 13.1_

- [x] 15. Final checkpoint — All tests implemented

## Notes

- All tasks are now complete
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate all 30 correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The backend uses Python (FastAPI, Celery, Hypothesis); the frontend uses TypeScript (Next.js)
