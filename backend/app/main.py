"""
FastAPI application factory and entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, close_db
from app.redis_store import init_redis, close_redis
from app.routers import auth, jobs
from app.celery_app import celery_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.

    Executed on startup and shutdown.
    """
    # Startup
    print("Initializing database...")
    await init_db()
    print("Database initialized")
    
    print("Initializing Redis connection pool...")
    await init_redis(settings.redis_url)
    print("Redis pool initialized")

    yield

    # Shutdown
    print("Closing Redis connections...")
    await close_redis()
    print("Redis connections closed")
    
    print("Closing database connections...")
    await close_db()
    print("Application shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI app instance
    """
    app = FastAPI(
        title="VibeAnalytix API",
        description="AI-powered code understanding engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, configure specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth.router)
    app.include_router(jobs.router)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": "0.1.0"}

    return app


# Create app instance
app = create_app()
