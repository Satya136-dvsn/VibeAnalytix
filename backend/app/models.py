"""
SQLAlchemy ORM models for all database tables.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TIMESTAMP,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

# pgvector Vector type - loaded lazily to avoid hard dependency
try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    from sqlalchemy.types import UserDefinedType
    class Vector(UserDefinedType):  # type: ignore
        def __init__(self, size, *args, **kwargs):
            self.size = size
        def get_col_spec(self, **kw):
            return f"VECTOR({self.size})"
    HAS_PGVECTOR = False
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: UUID = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: str = Column(String(255), unique=True, nullable=False, index=True)
    password_hash: str = Column(String(255), nullable=False)
    created_at: datetime = Column(TIMESTAMP(timezone=True), default=func.now())

    # Relationships
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")


class Job(Base):
    """Job record tracking analysis pipeline."""

    __tablename__ = "jobs"

    id: UUID = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: UUID = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    source_type: str = Column(String(50), nullable=False)  # 'github' or 'zip'
    source_ref: str = Column(String(1024), nullable=False)  # URL or filename
    status: str = Column(String(50), default="queued", nullable=False)
    current_stage: Optional[str] = Column(String(255), nullable=True)
    progress_pct: int = Column(Integer, default=0)
    error_message: Optional[str] = Column(Text, nullable=True)
    created_at: datetime = Column(TIMESTAMP(timezone=True), default=func.now())
    updated_at: datetime = Column(
        TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now()
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('github', 'zip')", name="valid_source_type"
        ),
        CheckConstraint(
            "status IN ('queued', 'in_progress', 'completed', 'failed')",
            name="valid_status",
        ),
        CheckConstraint("progress_pct >= 0 AND progress_pct <= 100", name="valid_progress"),
    )

    # Relationships
    user = relationship("User", back_populates="jobs")
    parsed_files = relationship("ParsedFile", back_populates="job", cascade="all, delete-orphan")
    function_summaries = relationship("FunctionSummary", back_populates="job", cascade="all, delete-orphan")
    file_summaries = relationship("FileSummary", back_populates="job", cascade="all, delete-orphan")
    module_summaries = relationship("ModuleSummary", back_populates="job", cascade="all, delete-orphan")
    project_results = relationship("ProjectResult", back_populates="job", cascade="all, delete-orphan")


class ParsedFile(Base):
    """Metadata for parsed source files."""

    __tablename__ = "parsed_files"

    id: UUID = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: UUID = Column(PG_UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    file_path: str = Column(String(1024), nullable=False)
    language: Optional[str] = Column(String(100), nullable=True)
    parse_error: Optional[str] = Column(Text, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="parsed_files")


class FunctionSummary(Base):
    """Function-level summaries with embeddings."""

    __tablename__ = "function_summaries"

    id: UUID = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: UUID = Column(PG_UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    file_path: str = Column(String(1024), nullable=False)
    function_name: str = Column(String(255), nullable=False)
    line_start: Optional[int] = Column(Integer, nullable=True)
    line_end: Optional[int] = Column(Integer, nullable=True)
    summary_text: Optional[str] = Column(Text, nullable=True)
    embedding = Column(Vector(768), nullable=True)  # type: ignore # Vector(768) matches Gemini text-embedding-004

    # Index for vector similarity search using IVFFlat
    __table_args__ = (
        Index(
            "idx_function_summaries_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    # Relationships
    job = relationship("Job", back_populates="function_summaries")


class FileSummary(Base):
    """File-level summaries."""

    __tablename__ = "file_summaries"

    id: UUID = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: UUID = Column(PG_UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    file_path: str = Column(String(1024), nullable=False)
    summary_text: Optional[str] = Column(Text, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="file_summaries")


class ModuleSummary(Base):
    """Module-level (directory) summaries."""

    __tablename__ = "module_summaries"

    id: UUID = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: UUID = Column(PG_UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    module_path: str = Column(String(1024), nullable=False)
    summary_text: Optional[str] = Column(Text, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="module_summaries")


class ProjectResult(Base):
    """Project-level analysis results."""

    __tablename__ = "project_results"

    id: UUID = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: UUID = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    project_summary: Optional[str] = Column(Text, nullable=True)
    overview_explanation: Optional[str] = Column(Text, nullable=True)
    flow_explanation: Optional[str] = Column(Text, nullable=True)
    dependency_graph: Optional[JSONB] = Column(JSONB, nullable=True)
    entry_points: Optional[JSONB] = Column(JSONB, nullable=True)
    circular_deps: Optional[JSONB] = Column(JSONB, nullable=True)
    external_deps: Optional[JSONB] = Column(JSONB, nullable=True)
    file_tree: Optional[JSONB] = Column(JSONB, nullable=True)
    per_file_explanations: Optional[JSONB] = Column(JSONB, nullable=True)
    architecture_diagrams: Optional[JSONB] = Column(JSONB, nullable=True)
    # {"dependency": "...", "module": "...", "class_diagram": "...", "flow": "..."}
    repo_metadata: Optional[JSONB] = Column(JSONB, nullable=True)
    # {"name": "...", "description": "...", "stars": N, "language": "...", "topics": [...]}

    # Relationships
    job = relationship("Job", back_populates="project_results")
