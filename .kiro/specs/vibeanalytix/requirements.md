# Requirements Document

## Introduction

VibeAnalytix is a deliberate AI-powered code understanding engine that transforms software codebases into clear, structured, and beginner-friendly explanations. Unlike prompt-based AI tools, VibeAnalytix follows a multi-stage reasoning pipeline: it ingests a repository or ZIP file, parses and analyzes the code structure, builds hierarchical context, and then generates teaching-oriented explanations. The system targets students, developers, open-source contributors, and code reviewers who need to understand unfamiliar codebases quickly.

## Deliberate Reasoning Strategy

VibeAnalytix adopts a deliberate reasoning approach where responses are generated only after completing full codebase analysis. Unlike traditional AI systems that provide immediate responses, VibeAnalytix prioritizes structured understanding through multi-pass processing — each pass building on the last before any explanation is produced.

VibeAnalytix differentiates itself by adopting a delayed-response intelligence model, where understanding is constructed before explanation, rather than generating instant responses.

## Glossary

- **System**: The VibeAnalytix application as a whole
- **Ingestion_Service**: The component responsible for accepting and validating GitHub repository URLs and ZIP file uploads
- **Parser**: The component that detects programming languages and builds AST-based representations of source files
- **Analysis_Engine**: The component that identifies entry points, maps dependencies, and detects cross-file relationships
- **Knowledge_Builder**: The component that constructs function-level, file-level, and project-level summaries
- **Explanation_Engine**: The AI-powered component (backed by OpenAI API) that generates structured, beginner-friendly explanations
- **Output_UI**: The Next.js frontend that displays the Overview, Structure, and Flow tabs to the user
- **Cleanup_Service**: The component responsible for deleting temporary files and releasing resources after processing
- **Job**: A single analysis run initiated by a user for a given repository or ZIP file
- **AST**: Abstract Syntax Tree — a structured representation of source code produced by a parser
- **Embedding**: A vector representation of a code chunk used for semantic context building
- **User**: A person interacting with VibeAnalytix through the web interface

---

## Requirements

### Requirement 1: Repository Input via GitHub URL

**User Story:** As a developer, I want to provide a GitHub repository URL, so that VibeAnalytix can clone and analyze the codebase without requiring a manual download.

#### Acceptance Criteria

1. WHEN a User submits a valid public GitHub repository URL, THE Ingestion_Service SHALL clone the repository into a temporary isolated directory.
2. WHEN a User submits a GitHub URL that is malformed or does not resolve to a valid repository, THE Ingestion_Service SHALL return a descriptive error message within 5 seconds.
3. WHEN a cloned repository exceeds 500 MB in size, THE Ingestion_Service SHALL reject the repository and return an error message indicating the size limit.
4. THE Ingestion_Service SHALL support only HTTPS GitHub URLs and SHALL reject SSH or non-GitHub URLs with a descriptive error.
5. Size limits for repository cloning and ZIP uploads SHALL be configurable via environment variables.

---

### Requirement 2: ZIP File Upload

**User Story:** As a student, I want to upload a ZIP file of my project, so that I can analyze code that is not hosted on GitHub.

#### Acceptance Criteria

1. WHEN a User uploads a ZIP file, THE Ingestion_Service SHALL extract the contents into a temporary isolated directory.
2. WHEN a User uploads a file that is not a valid ZIP archive, THE Ingestion_Service SHALL reject the file and return a descriptive error message.
3. WHEN a User uploads a ZIP file exceeding 100 MB, THE Ingestion_Service SHALL reject the upload and return an error message indicating the size limit.
4. WHEN a ZIP file contains path traversal sequences (e.g., `../`), THE Ingestion_Service SHALL sanitize all extracted paths and SHALL NOT write files outside the designated temporary directory.

---

### Requirement 3: Language Detection and File Structure Mapping

**User Story:** As a developer, I want the system to automatically detect programming languages and map the file structure, so that analysis is accurate without manual configuration.

#### Acceptance Criteria

1. WHEN ingestion completes, THE Parser SHALL detect the programming language of each source file using file extension and content heuristics.
2. THE Parser SHALL build a hierarchical file structure map representing all directories and files in the repository.
3. WHEN a file cannot be parsed due to an unsupported language or syntax error, THE Parser SHALL log the failure and continue processing remaining files.
4. THE Parser SHALL support at minimum the following languages: Python, JavaScript, TypeScript, Java, Go, and C/C++.

---

### Requirement 4: AST-Based Syntax Parsing

**User Story:** As a developer, I want the system to parse source code into structured representations, so that analysis is based on code semantics rather than raw text.

#### Acceptance Criteria

1. WHEN a source file is identified as a supported language, THE Parser SHALL generate an AST for that file using tree-sitter.
2. WHEN AST generation fails for a file, THE Parser SHALL record the error, skip the file, and continue with remaining files.
3. THE Parser SHALL extract from each AST: function definitions, class definitions, import/export statements, and top-level variable declarations.
4. THE Pretty_Printer SHALL serialize each parsed AST back into a normalized source representation.
5. FOR ALL valid source files, parsing then printing then parsing SHALL produce an equivalent AST (round-trip property).

---

### Requirement 5: Entry Point and Dependency Analysis

**User Story:** As a developer, I want the system to identify entry points and map dependencies between files, so that I can understand how the codebase is structured and how execution flows.

#### Acceptance Criteria

1. WHEN parsing completes, THE Analysis_Engine SHALL identify entry point files (e.g., `main.py`, `index.js`, `App.tsx`) based on language-specific conventions.
2. THE Analysis_Engine SHALL build a dependency graph representing import and require relationships between files.
3. WHEN a circular dependency is detected in the dependency graph, THE Analysis_Engine SHALL record it and include it in the analysis output.
4. THE Analysis_Engine SHALL identify and record all external library dependencies referenced in the codebase.
5. THE Analysis_Engine SHALL perform analysis in three sequential passes: Pass 1 (structural mapping of files and directories), Pass 2 (dependency and relationship detection between files and modules), and Pass 3 (context refinement incorporating cross-file semantic relationships).

---

### Requirement 6: Hierarchical Knowledge Construction

**User Story:** As a student, I want the system to build understanding at multiple levels of abstraction, so that explanations are coherent from function level up to the full project level.

#### Acceptance Criteria

1. WHEN analysis completes, THE Knowledge_Builder SHALL generate a summary for each function and method extracted from the ASTs.
2. THE Knowledge_Builder SHALL aggregate function-level summaries into a file-level summary for each source file.
3. THE Knowledge_Builder SHALL aggregate file-level summaries into module-level summaries grouped by directory.
4. THE Knowledge_Builder SHALL produce a single project-level summary that describes the overall purpose, architecture, and key components of the codebase.
5. WHEN a function body exceeds 200 lines, THE Knowledge_Builder SHALL chunk the function into segments of no more than 200 lines before summarization.

---

### Requirement 7: Embedding and Context Building

**User Story:** As a developer, I want the system to build semantic context from the codebase, so that explanations are context-aware rather than isolated.

#### Acceptance Criteria

1. WHEN knowledge construction completes, THE Knowledge_Builder SHALL generate an Embedding for each function-level summary using the OpenAI embeddings API.
2. THE Knowledge_Builder SHALL store all Embeddings in PostgreSQL with the pgvector extension alongside their associated source metadata (file path, function name, line range), enabling efficient similarity search.
3. WHEN generating an explanation for a component, THE Explanation_Engine SHALL retrieve the top 10 most semantically similar Embeddings to use as context.

---

### Requirement 8: AI-Powered Explanation Generation

**User Story:** As a student preparing for a technical interview, I want to receive clear, structured, beginner-friendly explanations of the codebase, so that I can understand and articulate the project confidently.

#### Acceptance Criteria

1. WHEN knowledge construction and context building complete, THE Explanation_Engine SHALL generate a project overview explanation describing the purpose, architecture, and key technologies of the codebase.
2. THE Explanation_Engine SHALL generate a per-file explanation for each source file, describing its role, key functions, and relationships to other files.
3. THE Explanation_Engine SHALL generate an execution flow explanation describing how the program starts, processes input, and produces output.
4. THE Explanation_Engine SHALL produce all explanations in plain English at a level understandable by an entry-level developer.
5. WHEN the OpenAI API returns an error, THE Explanation_Engine SHALL retry the request up to 3 times with exponential backoff before marking the Job as failed.
6. THE Explanation_Engine SHALL complete explanation generation for a repository of up to 10,000 lines of code within 5 minutes.

---

### Requirement 9: Asynchronous Job Processing

**User Story:** As a user, I want analysis to run in the background, so that I am not blocked waiting for a long-running process to complete.

#### Acceptance Criteria

1. WHEN a User submits a repository URL or ZIP file, THE System SHALL create a Job record in PostgreSQL and return a Job ID to the User within 2 seconds.
2. THE System SHALL process each Job asynchronously using a Celery task queue backed by Redis.
3. WHEN a Job is in progress, THE System SHALL expose a status endpoint that returns the current stage and percentage completion of the Job.
4. WHEN a Job completes successfully, THE System SHALL update the Job record status to "completed" and make results available via the results endpoint.
5. WHEN a Job fails at any stage, THE System SHALL update the Job record status to "failed" and store a human-readable error message.
6. THE System SHALL be horizontally scalable, allowing distributed processing of Jobs using Celery workers deployed across multiple nodes.
7. THE System SHALL ensure that failure of one Job does not impact the processing of other Jobs.
8. THE System SHALL log key events across all stages (ingestion, parsing, analysis, explanation) to enable monitoring and debugging.

---

### Requirement 10: Output Display

**User Story:** As a user, I want to view the analysis results in a structured, interactive UI, so that I can navigate and understand the codebase easily.

#### Acceptance Criteria

1. WHEN a Job status is "completed", THE Output_UI SHALL display results across three tabs: Overview, Structure, and Flow.
2. THE Output_UI SHALL display a file and folder tree in the left panel, allowing the User to select any file and view its explanation in the right panel.
3. WHEN a User selects a file in the file tree, THE Output_UI SHALL display the file-level explanation in the right panel within 500ms.
4. THE Output_UI SHALL display Job progress (current stage and percentage) while a Job is in progress, polling the status endpoint at most every 3 seconds.
5. WHEN a Job status is "failed", THE Output_UI SHALL display the error message and provide an option to retry the submission.
6. WHEN partial results are available before a Job reaches "completed" status, THE Output_UI SHALL support progressive rendering by displaying available results (e.g., project overview) without waiting for full completion.

---

### Requirement 11: Authentication and Authorization

**User Story:** As a user, I want my analysis jobs to be private and secure, so that only I can view my results.

#### Acceptance Criteria

1. THE System SHALL require Users to authenticate using a JWT before submitting a Job or accessing results.
2. WHEN an unauthenticated request is made to any protected endpoint, THE System SHALL return an HTTP 401 response.
3. WHEN an authenticated User requests results for a Job that belongs to a different User, THE System SHALL return an HTTP 403 response.
4. THE System SHALL invalidate JWT tokens after 24 hours of issuance.

---

### Requirement 12: Security and Input Validation

**User Story:** As a platform operator, I want all inputs to be validated and sandboxed, so that malicious uploads cannot compromise the system.

#### Acceptance Criteria

1. THE Ingestion_Service SHALL validate that uploaded files have a `.zip` extension and a valid ZIP magic number before extraction.
2. THE System SHALL enforce a rate limit of 10 Job submissions per User per hour.
3. WHILE a Job is being processed, THE System SHALL perform all file analysis in a read-only sandboxed environment with no network access.
4. THE Ingestion_Service SHALL reject any repository or ZIP file that contains executable binaries (`.exe`, `.dll`, `.so`, `.bin`).

---

### Requirement 13: Cleanup and Resource Management

**User Story:** As a platform operator, I want temporary files to be deleted after processing, so that storage is not exhausted and user data is not retained unnecessarily.

#### Acceptance Criteria

1. WHEN a Job reaches "completed" or "failed" status, THE Cleanup_Service SHALL delete all temporary files associated with that Job within 10 minutes.
2. WHEN a Job has been in "in_progress" status for more than 30 minutes, THE Cleanup_Service SHALL mark the Job as "failed" with a timeout error and delete all associated temporary files.
3. THE Cleanup_Service SHALL log the deletion of each temporary directory, including the Job ID, timestamp, and total size freed.
