# ===================================
# BALIKESİR SON DAKİKA HABER
# scripts/seed_categories.py
# Kategorileri veritabanına ekle
# ===================================

"""
Kullanım:
    python scripts/seed_categories.py

Bu script: Tüm başlangıç kategorilerini veritabanına ekler.
Mevcut kategorileri güncellemez, yalnızca eksik olanları ekler.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from app.database.database import AsyncSessionLocal, init_db
from app.database.models import Category
from sqlalchemy import select
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


# ─── Kategori Tanımları ────────────────────────────────────────────────────────

CATEGORIES = [
    # ─── Ana Kategoriler (parent_slug=None) ───────────────────────────────────
    {
        "name": "Son Dakika",
        "slug": "son-dakika",
        "description": "Son dakika gelişmeleri ve acil haberler",
        "color": "#ef4444",
        "icon": "flash",
        "order": 1,
        "show_in_nav": True,
        "parent_slug": None,
    },
    {
        "name": "Balıkesir",
        "slug": "balikesir",
        "description": "Balıkesir merkez haberleri",
        "color": "#e63946",
        "icon": "map-pin",
        "order": 2,
        "show_in_nav": True,
        "parent_slug": None,
    },
    {
        "name": "İlçeler",
        "slug": "ilceler",
        "description": "Balıkesir ilçe haberleri",
        "color": "#d62828",
        "icon": "map",
        "order": 3,
        "show_in_nav": True,
        "parent_slug": None,
    },
    {
        "name": "Gündem",
        "slug": "gundem",
        "description": "Gündemdeki gelişmeler",
        "color": "#f77f00",
        "icon": "trending-up",
        "order": 4,
        "show_in_nav": True,
        "parent_slug": None,
    },
    {
        "name": "Ekonomi",
        "slug": "ekonomi",
        "description": "Ekonomi ve iş dünyası haberleri",
        "color": "#2d6a4f",
        "icon": "bar-chart",
        "order": 5,
        "show_in_nav": True,
        "parent_slug": None,
    },
    {
        "name": "Spor",
        "slug": "spor",
        "description": "Spor haberleri ve sonuçlar",
        "color": "#023e8a",
        "icon": "activity",
        "order": 6,
        "show_in_nav": True,
        "parent_slug": None,
    },
    {
        "name": "Eğitim",
        "slug": "egitim",
        "description": "Eğitim ve öğretime dair haberler",
        "color": "#7209b7",
        "icon": "book-open",
        "order": 7,
        "show_in_nav": True,
        "parent_slug": None,
    },
    {
        "name": "Sağlık",
        "slug": "saglik",
        "description": "Sağlık haberleri ve duyurular",
        "color": "#06d6a0",
        "icon": "heart",
        "order": 8,
        "show_in_nav": True,
        "parent_slug": None,
    },
    {
        "name": "Teknoloji",
        "slug": "teknoloji",
        "description": "Teknoloji ve dijital dünya haberleri",
        "color": "#4361ee",
        "icon": "cpu",
        "order": 9,
        "show_in_nav": True,
        "parent_slug": None,
    },
    {
        "name": "Yaşam",
        "slug": "yasam",
        "description": "Yaşam tarzı ve günlük hayat haberleri",
        "color": "#f4a261",
        "icon": "sun",
        "order": 10,
        "show_in_nav": True,
        "parent_slug": None,
    },
    {
        "name": "Kültür Sanat",
        "slug": "kultur-sanat",
        "description": "Kültür, sanat ve etkinlik haberleri",
        "color": "#9b2226",
        "icon": "image",
        "order": 11,
        "show_in_nav": True,
        "parent_slug": None,
    },
    {
        "name": "Etkinlikler",
        "slug": "etkinlikler",
        "description": "Balıkesir etkinlikleri ve duyuruları",
        "color": "#560bad",
        "icon": "calendar",
        "order": 12,
        "show_in_nav": True,
        "parent_slug": None,
    },

    # ─── İlçe Alt Kategorileri (parent_slug="ilceler") ────────────────────────
    {
        "name": "Karesi",
        "slug": "karesi",
        "description": "Karesi ilçesi haberleri",
        "color": "#d62828",
        "order": 1,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Altıeylül",
        "slug": "altieylul",
        "description": "Altıeylül ilçesi haberleri",
        "color": "#d62828",
        "order": 2,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Bandırma",
        "slug": "bandirma",
        "description": "Bandırma ilçesi haberleri",
        "color": "#d62828",
        "order": 3,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Edremit",
        "slug": "edremit",
        "description": "Edremit ilçesi haberleri",
        "color": "#d62828",
        "order": 4,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Ayvalık",
        "slug": "ayvalik",
        "description": "Ayvalık ilçesi haberleri",
        "color": "#d62828",
        "order": 5,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Burhaniye",
        "slug": "burhaniye",
        "description": "Burhaniye ilçesi haberleri",
        "color": "#d62828",
        "order": 6,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Gönen",
        "slug": "gonen",
        "description": "Gönen ilçesi haberleri",
        "color": "#d62828",
        "order": 7,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Erdek",
        "slug": "erdek",
        "description": "Erdek ilçesi haberleri",
        "color": "#d62828",
        "order": 8,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Susurluk",
        "slug": "susurluk",
        "description": "Susurluk ilçesi haberleri",
        "color": "#d62828",
        "order": 9,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Dursunbey",
        "slug": "dursunbey",
        "description": "Dursunbey ilçesi haberleri",
        "color": "#d62828",
        "order": 10,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Bigadiç",
        "slug": "bigadic",
        "description": "Bigadiç ilçesi haberleri",
        "color": "#d62828",
        "order": 11,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Sındırgı",
        "slug": "sindirgi",
        "description": "Sındırgı ilçesi haberleri",
        "color": "#d62828",
        "order": 12,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Havran",
        "slug": "havran",
        "description": "Havran ilçesi haberleri",
        "color": "#d62828",
        "order": 13,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "İvrindi",
        "slug": "ivrindi",
        "description": "İvrindi ilçesi haberleri",
        "color": "#d62828",
        "order": 14,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Kepsut",
        "slug": "kepsut",
        "description": "Kepsut ilçesi haberleri",
        "color": "#d62828",
        "order": 15,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Manyas",
        "slug": "manyas",
        "description": "Manyas ilçesi haberleri",
        "color": "#d62828",
        "order": 16,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Marmara",
        "slug": "marmara",
        "description": "Marmara ilçesi haberleri",
        "color": "#d62828",
        "order": 17,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Savaştepe",
        "slug": "savastepe",
        "description": "Savaştepe ilçesi haberleri",
        "color": "#d62828",
        "order": 18,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Balya",
        "slug": "balya",
        "description": "Balya ilçesi haberleri",
        "color": "#d62828",
        "order": 19,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
    {
        "name": "Gömeç",
        "slug": "gomec",
        "description": "Gömeç ilçesi haberleri",
        "color": "#d62828",
        "order": 20,
        "show_in_nav": False,
        "parent_slug": "ilceler",
    },
]


async def get_category_by_slug(session, slug: str):
    result = await session.execute(
        select(Category).where(Category.slug == slug)
    )
    return result.scalar_one_or_none()


async def seed_categories():
    """Kategorileri veritabanına ekle."""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Önce parent_slug=None olanları ekle (üst kategoriler)
        logger.info("Üst kategoriler ekleniyor...")
        for cat_data in CATEGORIES:
            if cat_data["parent_slug"] is None:
                existing = await get_category_by_slug(session, cat_data["slug"])
                if existing:
                    logger.info(f"   ✓ Mevcut: {cat_data['name']}")
                    continue

                category = Category(
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    description=cat_data.get("description"),
                    color=cat_data.get("color", "#e63946"),
                    icon=cat_data.get("icon"),
                    order=cat_data.get("order", 0),
                    is_active=True,
                    show_in_nav=cat_data.get("show_in_nav", True),
                    parent_id=None,
                )
                session.add(category)
                logger.info(f"   + Eklendi: {cat_data['name']}")

        await session.commit()

        # Sonra alt kategorileri ekle (parent gerektirir)
        logger.info("Alt kategoriler (ilçeler) ekleniyor...")
        for cat_data in CATEGORIES:
            if cat_data["parent_slug"] is not None:
                existing = await get_category_by_slug(session, cat_data["slug"])
                if existing:
                    logger.info(f"   ✓ Mevcut: {cat_data['name']}")
                    continue

                parent = await get_category_by_slug(session, cat_data["parent_slug"])
                if not parent:
                    logger.warning(f"   ⚠️ Parent bulunamadı: {cat_data['parent_slug']}")
                    continue

                category = Category(
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    description=cat_data.get("description"),
                    color=cat_data.get("color", "#d62828"),
                    icon=cat_data.get("icon"),
                    order=cat_data.get("order", 0),
                    is_active=True,
                    show_in_nav=cat_data.get("show_in_nav", False),
                    parent_id=parent.id,
                )
                session.add(category)
                logger.info(f"   + Eklendi: {cat_data['name']} (üst: {parent.name})")

        await session.commit()

    logger.info("=" * 50)
    logger.info(f"✅ Toplam {len(CATEGORIES)} kategori işlendi.")


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("BALIKESİR SON DAKİKA HABER — Kategori Seed")
    logger.info("=" * 50)
    asyncio.run(seed_categories())
    logger.info("Tamamlandı!")
