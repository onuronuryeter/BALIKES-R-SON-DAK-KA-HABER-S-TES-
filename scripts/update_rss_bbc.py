import asyncio
import os
import sys

# Proje dizinini yola ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.future import select
from app.database.database import AsyncSessionLocal
from app.database.models import Source, Category

async def main():
    print("Mevcut RSS kaynakları devredışı bırakılıyor ve yeni BBC Türkçe kaynakları ekleniyor...")
    
    sources = [
        {"name": "BBC Türkçe - Haberler", "url": "http://www.bbc.co.uk/turkce/index.xml", "category_slug": "guncel"},
        {"name": "BBC Türkçe - Ekonomi", "url": "http://www.bbc.co.uk/turkce/ekonomi/index.xml", "category_slug": "ekonomi"},
        {"name": "BBC Türkçe - Dünyaya Açılan Pencere", "url": "http://www.bbc.co.uk/turkce/izlenim/index.xml", "category_slug": "dunya"},
        {"name": "BBC Türkçe - Özel Dosyalar", "url": "http://www.bbc.co.uk/turkce/ozeldosyalar/index.xml", "category_slug": "guncel"},
        {"name": "BBC Türkçe - Basın Özeti", "url": "http://www.bbc.co.uk/turkce/basinozeti/index.xml", "category_slug": "guncel"},
        {"name": "Sputnik Türkiye", "url": "https://tr.sputniknews.com/export/rss2/archive/index.xml", "category_slug": "guncel"},
        {"name": "Euronews - Türkiye", "url": "https://tr.euronews.com/haber/avrupa/turkiye", "category_slug": "guncel"},
    ]

    async with AsyncSessionLocal() as db:
        # 1. Mevcut tüm kaynakları pasife çek
        result = await db.execute(select(Source).where(Source.is_active == True))
        active_sources = result.scalars().all()
        for source in active_sources:
            source.is_active = False
            print(f"[{source.name}] devredışı bırakıldı.")
        
        # 2. Kategorileri belleğe al
        result = await db.execute(select(Category))
        categories = {cat.slug: cat.id for cat in result.scalars().all()}
        
        # 3. Yeni kaynakları ekle (Zaten varsa tekrar ekleme, sadece aktifleştir)
        for feed in sources:
            cat_id = categories.get(feed["category_slug"])
            if not cat_id:
                # Kategori yoksa guncel yapalım
                cat_id = categories.get("guncel")
                
            # Kaynak zaten var mı kontrol et
            result = await db.execute(select(Source).where(Source.url == feed["url"]))
            existing_source = result.scalar_one_or_none()
            
            if existing_source:
                existing_source.is_active = True
                existing_source.name = feed["name"]
                existing_source.category_id = cat_id
                print(f"[{feed['name']}] zaten vardı, aktifleştirildi ve güncellendi.")
            else:
                new_source = Source(
                    name=feed["name"],
                    url=feed["url"],
                    category_id=cat_id,
                    type="rss",
                    is_active=True
                )
                db.add(new_source)
                print(f"[{feed['name']}] yeni kaynak olarak eklendi.")
                
        await db.commit()
        print("\nTüm işlemler başarıyla tamamlandı! Artık sadece BBC Türkçe RSS kaynakları aktiftir.")

if __name__ == "__main__":
    asyncio.run(main())
