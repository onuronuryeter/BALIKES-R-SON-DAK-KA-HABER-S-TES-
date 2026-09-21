# ===================================
# BALIKESİR SON DAKİKA HABER
# scripts/seed_demo.py — Demo haber seed
# ===================================

"""
3 adet demo haber ekler.
Kullanım: python scripts/seed_demo.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from app.database.database import AsyncSessionLocal, init_db
from app.database.models import Article, Category, User, ArticleStatus
from sqlalchemy import select
import hashlib
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

DEMO_ARTICLES = [
    {
        "title": "Balıkesir'de Belediye Meydanı Yenileme Projesi Başladı",
        "slug": "balikesir-belediye-meydani-yenileme-projesi-basladi",
        "excerpt": "Balıkesir Büyükşehir Belediyesi, şehir merkezindeki meydanın yenilenmesi için kapsamlı bir proje başlattı. Proje kapsamında yeni peyzaj düzenlemeleri ve oturma alanları yapılacak.",
        "content": """<p>Balıkesir Büyükşehir Belediyesi, şehir merkezinde uzun süredir beklenen meydan yenileme projesini hayata geçiriyor. Proje, vatandaşların yoğun ilgisini çekiyor.</p>

<p>Yenileme çalışmaları kapsamında meydan alanına yeni peyzaj düzenlemeleri, modern oturma grupları, çocuk oyun alanları ve açık hava aydınlatma sistemi kurulacak. Çalışmaların üç ay içinde tamamlanması planlanıyor.</p>

<p>Proje hakkında bilgi veren yetkililer, meydanın hem estetik hem de işlevsellik açısından büyük bir dönüşüm geçireceğini belirtti. Vatandaşların bu süreçte anlayışla yaklaşması ve alternatif güzergahları kullanması istendi.</p>""",
        "category_slug": "balikesir",
        "is_breaking": False,
        "is_featured": True,
        "meta_title": "Balıkesir Meydan Yenileme Projesi Başladı",
        "meta_description": "Balıkesir Büyükşehir Belediyesi şehir merkezindeki meydanın yenilenmesi için kapsamlı proje başlattı.",
    },
    {
        "title": "Bandırma'da Uluslararası Fuar Hazırlıkları Tamamlandı",
        "slug": "bandirmada-uluslararasi-fuar-hazirliklari-tamamlandi",
        "excerpt": "Bandırma'da bu yıl ilk kez düzenlenecek uluslararası ticaret fuarının hazırlıkları tamamlandı. 15 ülkeden 200'den fazla firma katılım sağlayacak.",
        "content": """<p>Bandırma'da bu yıl ilk kez organize edilen uluslararası ticaret fuarının tüm hazırlıkları tamamlandı. Fuarda Avrupa, Orta Doğu ve Orta Asya'dan 15 ülkeden 200'den fazla firma yer alacak.</p>

<p>Fuar, bölge ekonomisine önemli bir katkı sağlaması bekleniyor. Fuar organizasyon komitesinin açıklamasına göre etkinlik, üç gün boyunca devam edecek ve ziyaretçilere ücretsiz olacak.</p>

<p>Fuar alanında yerel üreticilerin ürünleri de sergilenecek. Özellikle tarım sektöründen katılımcıların yoğun ilgi gösterdiği belirtildi.</p>""",
        "category_slug": "bandirma",
        "is_breaking": False,
        "is_featured": False,
        "meta_title": "Bandırma Uluslararası Ticaret Fuarı Hazır",
        "meta_description": "Bandırma'da ilk kez düzenlenecek uluslararası ticaret fuarına 15 ülkeden 200 firma katılacak.",
    },
    {
        "title": "Edremit Körfezi'nde Zeytin Hasadı Başladı",
        "slug": "edremit-korfezinde-zeytin-hasadi-basladi",
        "excerpt": "Edremit Körfezi'nde bu yıl rekor beklentisiyle başlayan zeytin hasadı tüm hızıyla devam ediyor. Bölge üreticileri bereketli geçen sezonu büyük bir memnuniyetle karşılıyor.",
        "content": """<p>Türkiye'nin önemli zeytin üretim merkezlerinden Edremit Körfezi'nde zeytin hasadı başladı. Bu yıl yeterli yağış ve uygun iklim koşulları nedeniyle rekor hasat bekleniyor.</p>

<p>Bölgedeki üreticiler, zeytinliklerde sabahın erken saatlerinden itibaren çalışmaya başlıyor. El ile toplama yönteminin yanı sıra modern toplama makineleri de kullanılıyor.</p>

<p>Hasadın yaklaşık 6-8 hafta sürmesi bekleniyor. Zeytin yağı fabrikaları da mesaiye başladı. Uzmanlar, bu yılki ürünün kalitesinin çok yüksek olacağını vurguluyor.</p>

<p>Edremit Körfezi, yüzyıllık geleneksel zeytin tarımıyla hem bölgesel hem de ulusal ekonomiye önemli katkı sağlıyor.</p>""",
        "category_slug": "edremit",
        "is_breaking": True,
        "is_featured": True,
        "meta_title": "Edremit'te Zeytin Hasadı Başladı — Rekor Bekleniyor",
        "meta_description": "Edremit Körfezi'nde zeytin hasadı başladı. Yeterli yağış ve uygun iklim koşulları nedeniyle bu yıl rekor hasat bekleniyor.",
    },
]


async def seed_demo():
    await init_db()

    async with AsyncSessionLocal() as session:
        # Admin kullanıcıyı bul
        user_r = await session.execute(select(User).where(User.is_admin == True))
        admin = user_r.scalar_one_or_none()
        if not admin:
            logger.error("Admin kullanıcı bulunamadı. Önce init_db.py çalıştırın.")
            return

        for data in DEMO_ARTICLES:
            # Slug kontrolü
            existing = await session.execute(
                select(Article).where(Article.slug == data["slug"])
            )
            if existing.scalar_one_or_none():
                logger.info(f"   ✓ Mevcut: {data['title'][:50]}")
                continue

            # Kategori bul
            cat_r = await session.execute(
                select(Category).where(Category.slug == data["category_slug"])
            )
            category = cat_r.scalar_one_or_none()

            article = Article(
                title=data["title"],
                slug=data["slug"],
                excerpt=data["excerpt"],
                content=data["content"],
                category_id=category.id if category else None,
                author_id=admin.id,
                status=ArticleStatus.PUBLISHED.value,
                is_breaking=data["is_breaking"],
                is_featured=data["is_featured"],
                published_at=datetime.now(timezone.utc),
                meta_title=data.get("meta_title"),
                meta_description=data.get("meta_description"),
                content_hash=hashlib.sha256(data["content"].encode()).hexdigest(),
            )
            session.add(article)
            logger.info(f"   + Eklendi: {data['title'][:50]}")

        await session.commit()
        logger.info("✅ Demo haberler eklendi!")


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Demo Haber Seed")
    logger.info("=" * 50)
    asyncio.run(seed_demo())
