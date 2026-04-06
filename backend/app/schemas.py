"""
Pydantic schemas for API request/response validation.
"""

from typing import Optional, Literal
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field, EmailStr


# ============ Auth Schemas ============


class UserRegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserLoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    """User response (public info)."""

    id: UUID
    email: str
    created_at: datetime


# ============ Job Schemas ============


class JobStatusResponse(BaseModel):
    """Job status response."""

    job_id: UUID
    status: Literal["queued", "in_progress", "completed", "failed"]
    current_stage: Optional[str] = None
    progress_pct: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class JobSubmissionResponse(BaseModel):
    """Response to job submission."""

    job_id: UUID
    status: str = "queued"


class ExplanationSet(BaseModel):
    """Complete set of explanations for a job."""

    project_summary: Optional[str] = None
    overview_explanation: Optional[str] = None
    flow_explanation: Optional[str] = None
    per_file_explanations: dict[str, str] = {}
    dependency_graph: Optional[dict] = None
    entry_points: Optional[list[str]] = None
    circular_deps: Optional[list[list[str]]] = None
    external_deps: Optional[list[str]] = None
    file_tree: Optional[dict] = None


class JobResultsResponse(BaseModel):
    """Complete job results."""

    job_id: UUID
    status: str
    explanations: ExplanationSet


class ChatRequest(BaseModel):
    """Semantic search/chat request."""
    query: str


class ChatResponse(BaseModel):
    """Semantic search/chat response."""
    answer: str
    sources: list[dict] = []



# ============ Error Schemas ============


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str
    message: str
    details: dict = {}


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    error: ErrorDetail


# ============ Function/File/Module Summaries ============


class FunctionDef(BaseModel):
    """Function definition extracted from AST."""

    name: str
    line_start: int
    line_end: int
    parameters: list[str] = []
    docstring: Optional[str] = None


class ClassDef(BaseModel):
    """Class definition extracted from AST."""

    name: str
    line_start: int
    line_end: int
    methods: list[FunctionDef] = []


class ImportDef(BaseModel):
    """Import statement extracted from AST."""

    module: str
    names: list[str] = []
    is_external: bool


class FileTreeNode(BaseModel):
    """File tree node for hierarchical structure."""

    name: str
    path: str
    is_dir: bool
    children: list["FileTreeNode"] = []


FileTreeNode.model_rebuild()
