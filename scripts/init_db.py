# ===================================
# BALIKESİR SON DAKİKA HABER
# scripts/init_db.py
# Veritabanını başlatma scripti
# ===================================

"""
Kullanım:
    python scripts/init_db.py

Bu script:
    1. SQLite veritabanını oluşturur
    2. Tüm tabloları oluşturur
    3. Admin kullanıcıyı oluşturur (eğer yoksa)
    4. Varsayılan site ayarlarını ekler
"""

import asyncio
import sys
import os
from pathlib import Path

# Proje kökünü Python yoluna ekle
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# .env dosyasını yükle
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from app.config.settings import settings
from app.database.database import init_db, AsyncSessionLocal
from app.database.models import User, SiteSetting
from sqlalchemy import select
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Şifreyi bcrypt ile hash'le."""
    import bcrypt
    password_bytes = password.encode("utf-8")
    # bcrypt max 72 byte — uzun şifreler için güvenli kırp
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


async def create_admin_user(session):
    """Admin kullanıcısı oluştur (yoksa)."""
    result = await session.execute(
        select(User).where(User.username == settings.ADMIN_USERNAME)
    )
    existing = result.scalar_one_or_none()

    if existing:
        logger.info(f"✅ Admin kullanıcı zaten mevcut: '{settings.ADMIN_USERNAME}'")
        return existing

    admin = User(
        username=settings.ADMIN_USERNAME,
        email=settings.ADMIN_EMAIL,
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        full_name="Sistem Yöneticisi",
        is_active=True,
        is_admin=True,
        is_superadmin=True,
    )
    session.add(admin)
    await session.commit()
    logger.info(f"✅ Admin kullanıcı oluşturuldu: '{settings.ADMIN_USERNAME}'")
    return admin


async def create_default_settings(session):
    """Varsayılan site ayarlarını ekle."""
    defaults = [
        {
            "key": "site_name",
            "value": settings.SITE_NAME,
            "label": "Site Adı",
            "setting_type": "text",
            "is_public": True,
        },
        {
            "key": "site_description",
            "value": settings.SITE_DESCRIPTION,
            "label": "Site Açıklaması",
            "setting_type": "text",
            "is_public": True,
        },
        {
            "key": "site_url",
            "value": settings.SITE_URL,
            "label": "Site URL",
            "setting_type": "text",
            "is_public": True,
        },
        {
            "key": "articles_per_page",
            "value": "20",
            "label": "Sayfa Başına Haber",
            "setting_type": "text",
            "is_public": True,
        },
        {
            "key": "breaking_news_enabled",
            "value": "true",
            "label": "Son Dakika Bandı Aktif",
            "setting_type": "bool",
            "is_public": True,
        },
        {
            "key": "contact_email",
            "value": settings.ADMIN_EMAIL,
            "label": "İletişim E-postası",
            "setting_type": "text",
            "is_public": True,
        },
        {
            "key": "footer_text",
            "value": f"© 2024 {settings.SITE_NAME}. Tüm hakları saklıdır.",
            "label": "Footer Metni",
            "setting_type": "text",
            "is_public": True,
        },
    ]

    for setting_data in defaults:
        result = await session.execute(
            select(SiteSetting).where(SiteSetting.key == setting_data["key"])
        )
        existing = result.scalar_one_or_none()
        if not existing:
            setting = SiteSetting(**setting_data)
            session.add(setting)
            logger.info(f"   + Ayar eklendi: {setting_data['key']}")
        else:
            logger.info(f"   ✓ Ayar mevcut: {setting_data['key']}")

    await session.commit()


async def main():
    """Ana init fonksiyonu."""
    logger.info("=" * 50)
    logger.info("BALIKESİR SON DAKİKA HABER — Veritabanı Kurulumu")
    logger.info("=" * 50)
    logger.info(f"Veritabanı: {settings.DATABASE_URL}")

    # Data dizinini oluştur
    data_dir = project_root / "data"
    media_dir = data_dir / "media"
    data_dir.mkdir(exist_ok=True)
    media_dir.mkdir(exist_ok=True)
    logger.info(f"✅ Data dizini: {data_dir}")

    # Tabloları oluştur
    logger.info("Tablolar oluşturuluyor...")
    await init_db()

    # Admin ve ayarları ekle
    async with AsyncSessionLocal() as session:
        logger.info("Admin kullanıcı kontrol ediliyor...")
        await create_admin_user(session)

        logger.info("Varsayılan site ayarları kontrol ediliyor...")
        await create_default_settings(session)

    logger.info("=" * 50)
    logger.info("✅ Kurulum tamamlandı!")
    logger.info(f"   Admin: {settings.ADMIN_USERNAME}")
    logger.info(f"   URL  : {settings.SITE_URL}")
    logger.info(f"   Docs : {settings.SITE_URL}/api/docs")
    logger.info("=" * 50)
    logger.info("Başlatmak için: run.bat")


if __name__ == "__main__":
    asyncio.run(main())
