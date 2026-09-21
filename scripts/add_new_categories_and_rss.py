# ===================================
# BALIKESİR SON DAKİKA HABER
# scripts/add_new_categories_and_rss.py
# Yeni kategorileri ve Sözcü RSS kaynaklarını veritabanına ekleme scripti
# ===================================

import asyncio
import sys
from pathlib import Path

# Proje kökünü Python yoluna ekle
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.database.database import AsyncSessionLocal
from app.database.models import Category, Source
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)


# Yeni eklenecek kategoriler ve özellikleri
NEW_CATEGORIES = [
    # Top Nav (Orange)
    {"name": "Son Dakika", "slug": "son-dakika", "color": "#e63946", "is_top_nav": True},
    {"name": "Güncel", "slug": "guncel", "color": "#fca311", "is_top_nav": True},
    {"name": "Dünya", "slug": "dunya", "color": "#14213d", "is_top_nav": True},
    {"name": "Ekonomi", "slug": "ekonomi", "color": "#2a9d8f", "is_top_nav": True},
    {"name": "Spor", "slug": "spor", "color": "#0077b6", "is_top_nav": True},
    {"name": "Magazin", "slug": "magazin", "color": "#e0a96d", "is_top_nav": True},
    # "Yerel" ve "İlçeler" parent-child durumu frontend.py'de ele alınabilir
    
    # Sub Nav (Black)
    {"name": "Politika", "slug": "politika", "color": "#4a4e69", "is_sub_nav": True},
    {"name": "Finans", "slug": "finans", "color": "#219ebc", "is_sub_nav": True},
    {"name": "Teknoloji", "slug": "teknoloji", "color": "#8338ec", "is_sub_nav": True},
    {"name": "Kültür Sanat", "slug": "kultur-sanat", "color": "#ff006e", "is_sub_nav": True},
    {"name": "Kadın", "slug": "kadin", "color": "#ffb703", "is_sub_nav": True},
    {"name": "Moda", "slug": "moda", "color": "#fb8500", "is_sub_nav": True},
    {"name": "Otomobil", "slug": "otomobil", "color": "#d90429", "is_sub_nav": True},
    {"name": "Yaşam", "slug": "yasam", "color": "#06d6a0", "is_sub_nav": True},
    {"name": "Sağlık", "slug": "saglik", "color": "#118ab2", "is_sub_nav": True},
    {"name": "Turizm", "slug": "turizm", "color": "#ffd166", "is_sub_nav": True},
    {"name": "Eğitim", "slug": "egitim", "color": "#ef476f", "is_sub_nav": True},
    {"name": "3.Sayfa", "slug": "3-sayfa", "color": "#000000", "is_sub_nav": True},
    
    # Reklam (Gizli / Özel kullanım)
    {"name": "Reklam", "slug": "reklam", "color": "#ffc300", "is_hidden": True},
    {"name": "İlan", "slug": "ilan", "color": "#b5838d", "is_hidden": True}
]

# Sözcü RSS Kaynakları ve Eşleşecekleri Kategori Slug'ları
RSS_SOURCES = [
    {"name": "Transfer Günlüğü", "url": "https://www.sozcu.com.tr/feeds-rss-category-transfer-gunlugu", "category_slug": "spor"},
    {"name": "2026 FIFA Dünya Kupası", "url": "https://www.sozcu.com.tr/feeds-rss-category-2026-fifa-dunya-kupasi", "category_slug": "spor"},
    {"name": "Resmi İlanlar", "url": "https://www.sozcu.com.tr/feeds-rss-category-resmi-ilanlar", "category_slug": "ilan"},
    {"name": "2024 Paris Olimpiyatları", "url": "https://www.sozcu.com.tr/feeds-rss-category-2024-paris-olimpiyatlari", "category_slug": "spor"},
    {"name": "Voleybol", "url": "https://www.sozcu.com.tr/feeds-rss-category-voleybol", "category_slug": "spor"},
    {"name": "Euro 2024", "url": "https://www.sozcu.com.tr/feeds-rss-category-euro-2024", "category_slug": "spor"},
    {"name": "Kripto", "url": "https://www.sozcu.com.tr/feeds-rss-category-kripto", "category_slug": "finans"},
    {"name": "Emlak", "url": "https://www.sozcu.com.tr/feeds-rss-category-emlak", "category_slug": "ekonomi"},
    {"name": "Emtia", "url": "https://www.sozcu.com.tr/feeds-rss-category-emtia", "category_slug": "finans"},
    {"name": "Borsa", "url": "https://www.sozcu.com.tr/feeds-rss-category-borsa", "category_slug": "finans"},
    {"name": "Keşfet", "url": "https://www.sozcu.com.tr/feeds-rss-category-kesfet", "category_slug": "yasam"},
    {"name": "İlan", "url": "https://www.sozcu.com.tr/feeds-rss-category-ilan", "category_slug": "ilan"},
    {"name": "Dünyadan Futbol", "url": "https://www.sozcu.com.tr/feeds-rss-category-dunyadan-spor", "category_slug": "spor"},
    {"name": "Hayat", "url": "https://www.sozcu.com.tr/feeds-rss-category-hayat", "category_slug": "yasam"},
    {"name": "Sözcü", "url": "https://www.sozcu.com.tr/feeds-rss-category-sozcu", "category_slug": "guncel"},
    {"name": "Diğer Sporlar", "url": "https://www.sozcu.com.tr/feeds-rss-category-diger-sporlar", "category_slug": "spor"},
    {"name": "Basketbol", "url": "https://www.sozcu.com.tr/feeds-rss-category-basketbol", "category_slug": "spor"},
    {"name": "Futbol", "url": "https://www.sozcu.com.tr/feeds-rss-category-futbol", "category_slug": "spor"},
    {"name": "Kültür Sanat", "url": "https://www.sozcu.com.tr/feeds-rss-category-kultur-sanat", "category_slug": "kultur-sanat"},
    {"name": "Günün İçinden", "url": "https://www.sozcu.com.tr/feeds-rss-category-gunun-icinden", "category_slug": "guncel"},
    {"name": "Otomotiv", "url": "https://www.sozcu.com.tr/feeds-rss-category-otomotiv", "category_slug": "otomobil"},
    {"name": "Eğitim", "url": "https://www.sozcu.com.tr/feeds-rss-category-egitim", "category_slug": "egitim"},
    {"name": "Astroloji", "url": "https://www.sozcu.com.tr/feeds-rss-category-astroloji", "category_slug": "yasam"},
    {"name": "Bilim ve Teknoloji", "url": "https://www.sozcu.com.tr/feeds-rss-category-bilim-teknoloji", "category_slug": "teknoloji"},
    {"name": "Sigorta", "url": "https://www.sozcu.com.tr/feeds-rss-category-sigorta", "category_slug": "finans"},
    {"name": "Finans", "url": "https://www.sozcu.com.tr/feeds-rss-category-finans", "category_slug": "finans"},
    {"name": "Ekonomi", "url": "https://www.sozcu.com.tr/feeds-rss-category-ekonomi", "category_slug": "ekonomi"},
    {"name": "Yazarlar", "url": "https://www.sozcu.com.tr/feeds-rss-category-yazar", "category_slug": "guncel"},
    {"name": "Yaşam", "url": "https://www.sozcu.com.tr/feeds-rss-category-yasam", "category_slug": "yasam"},
    {"name": "Spor", "url": "https://www.sozcu.com.tr/feeds-rss-category-spor", "category_slug": "spor"},
    {"name": "Sağlık", "url": "https://www.sozcu.com.tr/feeds-rss-category-saglik", "category_slug": "saglik"},
    {"name": "Magazin", "url": "https://www.sozcu.com.tr/feeds-rss-category-magazin", "category_slug": "magazin"},
    {"name": "Dünya", "url": "https://www.sozcu.com.tr/feeds-rss-category-dunya", "category_slug": "dunya"},
    {"name": "Gündem", "url": "https://www.sozcu.com.tr/feeds-rss-category-gundem", "category_slug": "guncel"},
    {"name": "Son Dakika", "url": "https://www.sozcu.com.tr/feeds-son-dakika", "category_slug": "son-dakika"},
    {"name": "Haberler", "url": "https://www.sozcu.com.tr/feeds-haberler", "category_slug": "guncel"}
]


async def update_database():
    async with AsyncSessionLocal() as session:
        # 1. Kategorileri Ekle
        logger.info("--- KATEGORİLER EKLENİYOR ---")
        category_map = {}
        for idx, cat_data in enumerate(NEW_CATEGORIES):
            slug = cat_data["slug"]
            stmt = select(Category).where(Category.slug == slug)
            result = await session.execute(stmt)
            category = result.scalar_one_or_none()
            
            if not category:
                category = Category(
                    name=cat_data["name"],
                    slug=slug,
                    color=cat_data["color"],
                    order=idx + 10,  # Mevcut kategorilerden sonra gelmesi için
                    is_active=True,
                    show_in_nav=not cat_data.get("is_hidden", False)
                )
                session.add(category)
                logger.info(f"Yeni Kategori: {category.name}")
            else:
                category.show_in_nav = not cat_data.get("is_hidden", False)
                logger.info(f"Kategori Mevcut: {category.name}")
            
            # DB ID'sini ileride RSS mapping için alabilmek amacıyla flush ediyoruz.
            await session.flush()
            category_map[slug] = category.id

        # 2. RSS Kaynaklarını Ekle
        logger.info("\n--- RSS KAYNAKLARI EKLENİYOR ---")
        for rss_data in RSS_SOURCES:
            url = rss_data["url"]
            stmt = select(Source).where(Source.url == url)
            result = await session.execute(stmt)
            source = result.scalar_one_or_none()
            
            category_id = category_map.get(rss_data["category_slug"])
            
            if not category_id:
                # Kategori DB'de farklı bir slug'la varsa veya oluşturulmadıysa bulmaya çalış
                cat_stmt = select(Category).where(Category.slug == rss_data["category_slug"])
                cat_res = await session.execute(cat_stmt)
                cat = cat_res.scalar_one_or_none()
                if cat:
                    category_id = cat.id
                else:
                    logger.warning(f"Kategori bulunamadı: {rss_data['category_slug']} - Kaynak atlanıyor: {rss_data['name']}")
                    continue

            if not source:
                source = Source(
                    name=f"Sözcü - {rss_data['name']}",
                    url=url,
                    type="rss",
                    category_id=category_id,
                    is_active=True,
                    fetch_interval_minutes=15
                )
                session.add(source)
                logger.info(f"Yeni Kaynak Eklendi: {source.name} -> {rss_data['category_slug']}")
            else:
                source.category_id = category_id
                logger.info(f"Kaynak Mevcut: {source.name} -> Güncellendi: {rss_data['category_slug']}")

        await session.commit()
        logger.info("\nVeritabanı başarıyla güncellendi.")

if __name__ == "__main__":
    asyncio.run(update_database())
