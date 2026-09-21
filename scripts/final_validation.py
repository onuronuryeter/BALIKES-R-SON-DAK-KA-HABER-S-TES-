import asyncio
import sys
import logging
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.services.scraper_service import scraper_service
from app.database.database import AsyncSessionLocal
from app.database.models import Article, Media
from sqlalchemy import select

logging.basicConfig(level=logging.ERROR) # Sadece hataları ve bizim printlerimizi görelim

async def run_validation():
    print("\n--- FINAL VALIDATION SCRIPT ---")
    
    # 1. COVER IMAGE TESTLERİ & JSON-LD vs.
    urls_to_test = {
        "A_RSS_VE_OG": "https://www.sozcu.com.tr/bursa-da-feci-kaza-bir-olu-dort-yarali-p84518",
        "B_SADECE_OG": "https://www.yeniakit.com.tr/haber/istanbul-kart-kullananlar-dikkat-puan-kampanyasinda-sona-gelindi-1875150.html",
        "C_CONTENT_IMAGE": "https://www.aa.com.tr/tr/dunya/londradaki-yapay-zeka-etkinliginde-yapay-zeka-insanlardan-caliyor-eylemi/4062254", # AA JSON-LD var ama haber içi resimler vs test
        "D_NO_IMAGE": "https://yeniyasamgazetesi9.com/basta-kadinlar-tum-toplum-birlikte-mucadele-etmeli/",
        "E_PLACEHOLDER": "https://www.ekonomigazetesi.com/haber/sanayi-ve-teknoloji-bakani-kacirtan-aciklamalariyla-dikkat-cekti-60341"
    }

    print("\n[1] COVER IMAGE TESTLERI")
    for case_name, url in urls_to_test.items():
        print(f"\nSenaryo: {case_name}")
        print(f"URL: {url}")
        res = await scraper_service.extract_images(url)
        print(f"COVER IMAGE: {res.get('cover')}")
        print(f"BODY IMAGES: {len(res.get('body_images', []))}")

    # 2. PLACEHOLDER / LOGO TESTI
    print("\n[2] PLACEHOLDER / LOGO TESTI")
    suspicious_urls = [
        "https://example.com/logo.png",
        "https://example.com/default-image.jpg",
        "https://example.com/no-image.jpg",
        "https://example.com/placeholder_1x1.gif",
        "https://example.com/avatar_user1.jpg",
        "https://example.com/banner-ad.webp",
        "https://example.com/social-icon-fb.svg",
        "https://example.com/tracking-pixel.png"
    ]
    for su in suspicious_urls:
        is_susp = scraper_service.is_suspicious_image(su)
        print(f"URL: {su} -> Reddedildi mi?: {is_susp}")

    # 3. RELATIVE URL TESTI
    print("\n[3] RELATIVE URL TESTI (BeatifulSoup urljoin test)")
    # `scraper_service` içerisindeki BeautifulSoup ile yakalandığında `urljoin(url, img)` çalışıyor.
    # Doğrudan python `urllib.parse.urljoin` testi:
    from urllib.parse import urljoin
    base = "https://www.ornek.com/haber/123"
    print("Base:", base)
    print("/images/a.jpg ->", urljoin(base, "/images/a.jpg"))
    print("images/a.jpg ->", urljoin(base, "images/a.jpg"))
    print("../images/a.jpg ->", urljoin(base, "../images/a.jpg"))
    print("//cdn.site.com/a.jpg ->", urljoin(base, "//cdn.site.com/a.jpg"))

    # 4. DATABASE / BACKFILL TEST KONTROLÜ
    print("\n[4] DATABASE ve BACKFILL KONTROLU")
    async with AsyncSessionLocal() as session:
        # Son 10 article
        q = select(Article).order_by(Article.id.desc()).limit(10)
        res = await session.execute(q)
        articles = res.scalars().all()
        
        print(f"Son 10 Haber:\n")
        for a in articles:
            media_q = select(Media).where(Media.article_id == a.id)
            media_res = await session.execute(media_q)
            medias = media_res.scalars().all()
            
            cover_count = sum(1 for m in medias if m.is_cover)
            body_count = sum(1 for m in medias if not m.is_cover)
            
            print(f"ID: {a.id} | Başlık: {a.title[:30]}... | Kaynak: {a.image_source} | Durum: {a.image_status} | Kapak URL: {a.featured_image} | DB Cover Media: {cover_count} | DB Body Media: {body_count}")

    await scraper_service.close()

if __name__ == "__main__":
    asyncio.run(run_validation())
