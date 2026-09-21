# ===================================
# BALIKESİR SON DAKİKA HABER
# app/api/auth.py — JWT Authentication
# ===================================

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging
import bcrypt

from jose import JWTError, jwt

from app.config.settings import settings
from app.database.database import get_db
from app.database.models import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── OAuth2 ──────────────────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

COOKIE_NAME = "access_token"

# ─── Yardımcı Fonksiyonlar ────────────────────────────────────────────────────

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Şifre doğrulama."""
    try:
        password_bytes = plain_password.encode("utf-8")
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error(f"Şifre doğrulama hatası: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Şifreyi hash'le."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT access token oluştur."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Kullanıcı adıyla kullanıcı bul."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """Kullanıcı adı ve şifre ile kimlik doğrula."""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


# ─── Dependency: Mevcut kullanıcıyı al ──────────────────────────────────────

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    JWT token'dan mevcut kullanıcıyı döndürür.
    Token önce cookie'den, sonra Authorization header'dan okunur.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    user = await get_user_by_username(db, username)
    return user


async def require_admin(
    current_user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Admin yetkisi gerektirir. Yetkisiz kullanıcı için 401/403 döner.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum açmanız gerekiyor",
        )
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için admin yetkisi gerekiyor",
        )
    return current_user


# ─── Endpoint'ler ─────────────────────────────────────────────────────────────

@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """API token endpoint (Swagger UI için)."""
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adı veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login")
async def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Form tabanlı login — cookie set eder."""
    user = await authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adı veya şifre hatalı",
        )

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin yetkisi gerekiyor",
        )

    access_token = create_access_token(data={"sub": user.username})

    # Last login güncelle
    from datetime import datetime, timezone
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,  # Production'da True yapın
    )
    return {"message": "Giriş başarılı", "username": user.username}


@router.post("/logout")
async def logout(response: Response):
    """Logout — cookie siler."""
    response.delete_cookie(COOKIE_NAME)
    return {"message": "Çıkış yapıldı"}


@router.get("/me")
async def get_me(current_user: User = Depends(require_admin)):
    """Mevcut kullanıcı bilgilerini döndür."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
        "is_superadmin": current_user.is_superadmin,
    }
