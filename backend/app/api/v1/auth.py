
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from backend.app.core.config import settings
from backend.app.db.database import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    UserResponse,
    TokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    password_fingerprint,
    create_password_reset_token,
    verify_password_reset_token,
)
from backend.app.services.email_service import send_password_reset_email


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
async def signup(
    data: SignupRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(func.lower(User.email) == data.email.lower())
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    hashed = await run_in_threadpool(hash_password, data.password)

    new_user = User(
        username=data.username,
        email=data.email,
        hashed_password=hashed
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(func.lower(User.email) == data.email.lower())
    )
    user = result.scalar_one_or_none()

    password_valid = (
        await run_in_threadpool(
            verify_password,
            data.password,
            user.hashed_password
        )
        if user
        else False
    )

    if not user or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    access_token = create_access_token(subject=str(user.id))

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


from backend.app.core.dependencies import get_current_user
@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_valid = await run_in_threadpool(
        verify_password,
        data.current_password,
        current_user.hashed_password
    )

    if not current_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    if data.new_password == data.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password."
        )

    current_user.hashed_password = await run_in_threadpool(
        hash_password,
        data.new_password
    )
    await db.commit()

    return {
        "message": "Password changed successfully."
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    return {
        "message": "Signed out successfully."
    }


def _resolve_reset_page_url(request: Request) -> str:
    """Build reset-password page URL from an allowlisted Referer/Origin or FRONTEND_URL."""
    referer = request.headers.get("referer")
    if referer:
        parsed = urlparse(referer)
        host = (parsed.hostname or "").lower()
        allowed_hosts = {
            "localhost",
            "127.0.0.1",
            "codebase-qa-assistant-frontend.vercel.app",
        }
        configured_host = (urlparse(settings.FRONTEND_URL).hostname or "").lower()
        if configured_host:
            allowed_hosts.add(configured_host)

        if parsed.scheme in {"http", "https"} and host in allowed_hosts:
            base_dir = parsed.path.rsplit("/", 1)[0]
            return f"{parsed.scheme}://{parsed.netloc}{base_dir}/reset-password.html"

    return f"{settings.FRONTEND_URL.rstrip('/')}/pages/reset-password.html"


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(func.lower(User.email) == data.email.lower())
    )
    user = result.scalar_one_or_none()

    if user is not None:
        reset_token = create_password_reset_token(user.id, user.hashed_password)
        reset_url = f"{_resolve_reset_page_url(request)}?token={reset_token}"

        try:
            await run_in_threadpool(
                send_password_reset_email,
                user.email,
                user.username,
                reset_url,
            )
        except Exception as exc:
            print("Failed to send password reset email:", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to send password reset email right now. Please try again later."
            )

    return {
        "message": "If an account with that email exists, a password reset link has been sent."
    }


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        user_id, token_fp = verify_password_reset_token(data.token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None or password_fingerprint(user.hashed_password) != token_fp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has already been used or is invalid."
        )

    user.hashed_password = await run_in_threadpool(
        hash_password,
        data.new_password
    )
    await db.commit()

    return {
        "message": "Password reset successfully. You can now log in."
    }

