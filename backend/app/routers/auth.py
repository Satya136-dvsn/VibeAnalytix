"""
Authentication router for user registration and login endpoints.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import (
    create_jwt_token,
    hash_password,
    verify_password,
    get_current_user,
)
from app.database import get_session
from app.models import User
from app.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    ErrorResponse,
    ErrorDetail,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def register(
    request: UserRegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    Register a new user.

    Args:
        request: User registration request
        session: Database session

    Returns:
        Newly created user

    Raises:
        HTTPException 409: If email already exists
        HTTPException 400: If validation fails
    """
    # Check if user already exists
    stmt = select(User).where(User.email == request.email.lower())
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create new user
    user = User(
        email=request.email.lower(),
        password_hash=hash_password(request.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse},
    },
)
async def login(
    request: UserLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """
    Authenticate user and issue JWT token.

    Args:
        request: User login request
        session: Database session

    Returns:
        JWT token response

    Raises:
        HTTPException 401: If credentials are invalid
    """
    # Find user by email
    stmt = select(User).where(User.email == request.email.lower())
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    # Verify credentials
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Issue JWT
    token = create_jwt_token(str(user.id))

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=24 * 3600,  # 24 hours in seconds
    )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse},
    },
)
async def get_current_user_info(
    user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current authenticated user info.

    Args:
        user: Current user from JWT

    Returns:
        User information
    """
    return UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
    )
