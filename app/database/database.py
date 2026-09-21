# ===================================
# BALIKESİR SON DAKİKA HABER
# app/database/database.py
# Async SQLAlchemy veritabanı bağlantısı
# ===================================

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ─── Engine ────────────────────────────────────────────────────────────────────

def _get_engine_kwargs() -> dict:
    """SQLite ve PostgreSQL için farklı engine ayarları."""
    kwargs = {
        "echo": settings.DEBUG,
    }
    if settings.database_is_sqlite:
        # SQLite için özel bağlantı parametreleri
        kwargs["connect_args"] = {
            "check_same_thread": False,
            "timeout": 30,
        }
    return kwargs


engine = create_async_engine(
    settings.DATABASE_URL,
    **_get_engine_kwargs(),
)

@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.database_is_sqlite:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

# ─── Session Factory ────────────────────────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ─── Base Model ─────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Tüm SQLAlchemy model sınıflarının türeyeceği taban sınıf."""
    pass


# ─── Dependency ─────────────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:
    """
    FastAPI dependency injection için async veritabanı oturumu.
    Her istek için ayrı bir oturum açar ve işlem tamamlanınca kapatır.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error(f"Veritabanı hatası: {exc}")
            raise
        finally:
            await session.close()


# ─── Init Tables ────────────────────────────────────────────────────────────────

async def init_db():
    """
    Uygulama başlangıcında tabloları oluşturur.
    Alembic migration'ları olmayan ilk kurulum için kullanılır.
    """
    # Import models here to ensure they're registered with Base
    from app.database import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Veritabanı tabloları hazır.")


async def drop_all_tables():
    """
    Sadece development/test ortamında kullanılır.
    Tüm tabloları siler.
    """
    if settings.is_production:
        raise RuntimeError("Production ortamında drop_all_tables çağrılamaz!")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("⚠️ Tüm tablolar silindi.")
