import asyncio
import sys
from pathlib import Path

# Proje kökünü Python yoluna ekle
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from app.database.database import AsyncSessionLocal
from app.database.models import Source, Category
from sqlalchemy import select

async def main():
    print("RSS kaynakları veritabanına ekleniyor...")
    
    async with AsyncSessionLocal() as session:
        # 1. Genel bir kategori oluştur
        cat_result = await session.execute(select(Category).where(Category.slug == "genel"))
        category = cat_result.scalar_one_or_none()
        
        if not category:
            category = Category(name="Genel", slug="genel", is_active=True)
            session.add(category)
            await session.commit()
            await session.refresh(category)
            print(" -> 'Genel' kategorisi oluşturuldu.")
            
        # 2. Örnek RSS kaynakları ve Kullanıcının Eklediği Yeni Kaynaklar
        rss_feeds = [
            {"name": "TRT Haber - Güncel", "url": "https://www.trthaber.com/xml_mobile.php?tur=xml_genel&kategori=guncel&adet=20"},
            {"name": "Habertürk - Manşet", "url": "https://www.haberturk.com/rss/manset.xml"},
            {"name": "AA - Güncel", "url": "https://www.aa.com.tr/tr/rss/default?cat=guncel"},
            {"name": "Sözcü Son Dakika", "url": "https://www.sozcu.com.tr/feeds-son-dakika"},
            {"name": "Sözcü Günün İçinden", "url": "https://www.sozcu.com.tr/feeds-rss-category-gunun-icinden"},
            {"name": "Yeni Yaşam Gazetesi", "url": "https://yeniyasamgazetesi9.com/feed/"},
            {"name": "Yeni Akit", "url": "https://www.yeniakit.com.tr/rss/haber/gundem"},
            {"name": "Ekonomi Gazetesi", "url": "https://www.ekonomigazetesi.com/rss.xml"}
        ]
        
        added_count = 0
        for feed in rss_feeds:
            result = await session.execute(select(Source).where(Source.url == feed["url"]))
            existing = result.scalar_one_or_none()
            
            if not existing:
                source = Source(
                    name=feed["name"],
                    url=feed["url"],
                    type="rss",
                    category_id=category.id,
                    is_active=True,
                    fetch_interval_minutes=15
                )
                session.add(source)
                print(f" -> Kaynak eklendi: {feed['name']}")
                added_count += 1
            else:
                print(f" -> Kaynak zaten mevcut: {feed['name']}")
                
        if added_count > 0:
            await session.commit()
            print("\nBaşarılı! Yeni RSS kaynakları veritabanına eklendi.")
        else:
            print("\nEklenecek yeni kaynak bulunamadı.")
            
        print("Lütfen uygulamanızı (run.bat) yeniden başlatın veya haberlerin çekilmesini bekleyin (15 dk).")

if __name__ == "__main__":
    asyncio.run(main())
