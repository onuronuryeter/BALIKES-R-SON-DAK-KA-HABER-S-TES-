import asyncio
import sys
import logging
from pathlib import Path

# Proje kökünü Python yoluna ekle
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database.database import AsyncSessionLocal
from app.database.models import Article, Media
from app.services.scraper_service import scraper_service
from app.services.media_service import media_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def main():
    logger.info("Eksik görselli haberleri kurtarma (Backfill) işlemi başlıyor...")
    
    async with AsyncSessionLocal() as db:
        # Sadece placeholder olan veya resmi olmayan haberleri getir
        query = select(Article).where(
            (Article.image_source == 'placeholder') | 
            (Article.image_status == 'missing') | 
            (Article.featured_image == None)
        ).order_by(Article.id.desc()).limit(100) # Test amaçlı 100 ile sınırlıyoruz
        
        result = await db.execute(query)
        articles = result.scalars().all()
        
        if not articles:
            logger.info("Eksik görselli haber bulunamadı.")
            return

        logger.info(f"İşlenecek makale sayısı: {len(articles)}")
        
        success_count = 0
        fail_count = 0
        
        for article in articles:
            if not article.original_url:
                continue
                
            logger.info(f"[{article.id}] İşleniyor: {article.original_url}")
            
            extracted = await scraper_service.extract_images(article.original_url)
            cover_url = extracted.get("cover")
            
            if cover_url:
                # İndir ve kaydet
                local_cover = await media_service.download_image(cover_url, prefix=article.slug[:15])
                if local_cover:
                    article.featured_image = local_cover
                    article.image_source = "scraper_backfill"
                    article.image_status = "available"
                    article.image_source_url = cover_url
                    
                    filename = local_cover.split("/")[-1]
                    media_cover = Media(
                        filename=filename,
                        file_path=str(media_service.upload_dir / filename),
                        url=local_cover,
                        article_id=article.id,
                        is_cover=True
                    )
                    db.add(media_cover)
                    
                    success_count += 1
                    logger.info(f"[{article.id}] Başarı: {local_cover}")
                else:
                    fail_count += 1
                    logger.warning(f"[{article.id}] Görsel indirilemedi: {cover_url}")
            else:
                fail_count += 1
                logger.info(f"[{article.id}] Orijinal sitede resim bulunamadı.")
                
            # DB yorulmasın ve Rate Limit'e takılmayalım
            await db.commit()
            await asyncio.sleep(1) # 1 Saniye bekleme süresi
            
        logger.info("="*50)
        logger.info(f"BAŞARILI: {success_count} | BAŞARISIZ: {fail_count}")
        logger.info("="*50)
        
    await scraper_service.close()

if __name__ == "__main__":
    asyncio.run(main())
