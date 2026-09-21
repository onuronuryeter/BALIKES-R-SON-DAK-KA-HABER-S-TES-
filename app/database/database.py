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

async def seed_db(session):
    from app.database.models import User, SiteSetting
    from app.api.auth import get_password_hash
    from app.config.settings import settings
    from sqlalchemy import select

    # Admin oluştur
    result = await session.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
    admin = result.scalar_one_or_none()
    if not admin:
        admin = User(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            full_name="Sistem Yöneticisi",
            is_active=True,
            is_admin=True,
            is_superadmin=True,
        )
        session.add(admin)
        logger.info(f"✅ Admin otomatik eklendi: '{settings.ADMIN_USERNAME}'")

    # Ayarları oluştur
    defaults = [
        {"key": "site_name", "value": settings.SITE_NAME, "label": "Site Adı", "setting_type": "text", "is_public": True},
        {"key": "site_description", "value": settings.SITE_DESCRIPTION, "label": "Site Açıklaması", "setting_type": "text", "is_public": True},
        {"key": "site_url", "value": settings.SITE_URL, "label": "Site URL", "setting_type": "text", "is_public": True},
        {"key": "articles_per_page", "value": "20", "label": "Sayfa Başına Haber", "setting_type": "text", "is_public": True},
        {"key": "breaking_news_enabled", "value": "true", "label": "Son Dakika Bandı Aktif", "setting_type": "bool", "is_public": True},
        {"key": "contact_email", "value": settings.ADMIN_EMAIL, "label": "İletişim E-postası", "setting_type": "text", "is_public": True},
        {"key": "footer_text", "value": f"© 2024 {settings.SITE_NAME}. Tüm hakları saklıdır.", "label": "Footer Metni", "setting_type": "text", "is_public": True},
    ]

    for setting_data in defaults:
        result = await session.execute(select(SiteSetting).where(SiteSetting.key == setting_data["key"]))
        existing = result.scalar_one_or_none()
        if not existing:
            setting = SiteSetting(**setting_data)
            session.add(setting)

    await session.commit()


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

    # Tohum verilerini (admin vb.) ekle
    async with AsyncSessionLocal() as session:
        await seed_db(session)


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
