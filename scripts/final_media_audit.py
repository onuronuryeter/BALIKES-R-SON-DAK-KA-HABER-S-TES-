import asyncio
import sys
import logging
from pathlib import Path

# Proje kökünü Python yoluna ekle
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from sqlalchemy import select, func, or_, text
from app.database.database import AsyncSessionLocal
from app.database.models import Article, Media
from app.services.scraper_service import scraper_service
from app.services.media_service import media_service
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

async def run_audit():
    logger.info("FINAL MEDIA AUDIT - BACKFILL STARTED")
    
    async with AsyncSessionLocal() as db:
        # 1. TOTAL STATS
        total_articles_query = await db.execute(select(func.count(Article.id)))
        total_articles = total_articles_query.scalar()
        
        # Kapak resmi eksik olanlar
        missing_cover_query = select(Article).where(
            or_(
                Article.image_source == 'placeholder',
                Article.image_status == 'missing',
                Article.featured_image == None
            )
        )
        missing_cover_res = await db.execute(missing_cover_query)
        missing_covers = missing_cover_res.scalars().all()
        
        # İçerik (Body) görseli hiç taranmamış/indirilmeyenler
        # Eğer Media tablosunda is_cover=False olan kaydı yoksa ve kaynakta resim varsa...
        # Basitçe, henüz scraper_backfill geçmemiş eski makaleler
        missing_body_query = select(Article).outerjoin(
            Media, (Media.article_id == Article.id) & (Media.is_cover == False)
        ).where(
            Media.id == None, 
            Article.content.not_like('%<figure%') # Henüz HTML içine <figure> enjekte edilmemiş olanlar
        )
        missing_body_res = await db.execute(missing_body_query)
        missing_bodies = missing_body_res.scalars().all()

        logger.info(f"DB TOTAL ARTICLES: {total_articles}")
        logger.info(f"TOTAL MISSING COVER: {len(missing_covers)}")
        logger.info(f"TOTAL MISSING BODY/CONTENT: {len(missing_bodies)}")

        # --- COVER IMAGE BACKFILL ---
        logger.info("\n--- STARTING COVER IMAGE BACKFILL ---")
        cover_scanned = 0
        cover_repaired = 0
        cover_no_image = 0
        cover_failed = 0
        
        sem = asyncio.Semaphore(10) # 10 Eşzamanlı istek
        
        async def process_cover(article_id):
            nonlocal cover_scanned, cover_repaired, cover_no_image, cover_failed
            async with AsyncSessionLocal() as session:
                art = await session.get(Article, article_id)
                if not art or not art.original_url:
                    cover_failed += 1
                    return
                
                cover_scanned += 1
                try:
                    extracted = await scraper_service.extract_images(art.original_url)
                    if extracted.get("cover"):
                        local_c = await media_service.download_image(extracted["cover"], prefix=art.slug[:15])
                        if local_c:
                            art.featured_image = local_c
                            art.image_source = "scraper_backfill"
                            art.image_status = "available"
                            art.image_source_url = extracted["cover"]
                            
                            media_c = Media(
                                filename=local_c.split("/")[-1],
                                file_path=str(media_service.upload_dir / local_c.split("/")[-1]),
                                url=local_c,
                                article_id=art.id,
                                is_cover=True
                            )
                            session.add(media_c)
                            await session.commit()
                            cover_repaired += 1
                            logger.info(f"[COVER] #{art.id} Başarılı: {local_c}")
                        else:
                            cover_failed += 1
                    else:
                        cover_no_image += 1
                except Exception as e:
                    cover_failed += 1
                    logger.error(f"[COVER] Hata #{art.id}: {e}")

        # Task list for cover
        tasks = []
        for art in missing_covers:
            async def bounded_process_cover(a_id):
                async with sem:
                    await process_cover(a_id)
            tasks.append(bounded_process_cover(art.id))
            
        await asyncio.gather(*tasks)
        
        # --- CONTENT IMAGE BACKFILL ---
        logger.info("\n--- STARTING CONTENT IMAGE BACKFILL ---")
        body_scanned = 0
        body_repaired = 0
        body_no_image = 0
        body_failed = 0
        
        detailed_old_articles = []
        
        async def process_body(article_id):
            nonlocal body_scanned, body_repaired, body_no_image, body_failed
            async with AsyncSessionLocal() as session:
                art = await session.get(Article, article_id)
                if not art or not art.original_url:
                    body_failed += 1
                    return
                    
                body_scanned += 1
                try:
                    extracted = await scraper_service.extract_images(art.original_url)
                    b_imgs = extracted.get("body_images", [])
                    
                    if not b_imgs:
                        body_no_image += 1
                        return
                        
                    local_b_imgs = []
                    for b_img in b_imgs[:5]: # Max 5
                        lb = await media_service.download_image(b_img, prefix=art.slug[:15])
                        if lb:
                            local_b_imgs.append(lb)
                            
                    if local_b_imgs:
                        # Enjekte et
                        soup = BeautifulSoup(art.content, "html.parser")
                        paragraphs = soup.find_all("p")
                        
                        for idx, l_img in enumerate(local_b_imgs):
                            target_p_idx = (idx + 1) * 2 - 1
                            figure_tag = soup.new_tag("figure")
                            figure_tag["class"] = "article-content-figure my-4 text-center"
                            img_tag = soup.new_tag("img", src=l_img, alt=f"{art.title} - Görsel {idx+1}")
                            img_tag["class"] = "img-fluid rounded w-100 shadow-sm"
                            img_tag["loading"] = "lazy"
                            figure_tag.append(img_tag)
                            figcaption = soup.new_tag("figcaption")
                            figcaption["class"] = "figure-caption mt-2 text-muted text-start"
                            figcaption.string = f"{art.title} - Haber Görseli {idx+1}"
                            figure_tag.append(figcaption)
                            
                            if target_p_idx < len(paragraphs):
                                paragraphs[target_p_idx].insert_after(figure_tag)
                            else:
                                soup.append(figure_tag)
                                
                        art.content = str(soup)
                        
                        for lb in local_b_imgs:
                            session.add(Media(
                                filename=lb.split("/")[-1],
                                file_path=str(media_service.upload_dir / lb.split("/")[-1]),
                                url=lb,
                                article_id=art.id,
                                is_cover=False
                            ))
                            
                        await session.commit()
                        body_repaired += 1
                        logger.info(f"[BODY] #{art.id} {len(local_b_imgs)} görsel HTML'e enjekte edildi.")
                        
                        # Detaylı rapor için 10 makale kaydet (eğer çok resim varsa)
                        if len(detailed_old_articles) < 10 and len(b_imgs) > 1:
                            detailed_old_articles.append({
                                "id": art.id,
                                "source": art.source_name,
                                "source_images": len(b_imgs) + (1 if extracted.get("cover") else 0), # Tahmini kaynak resmi sayısı
                                "extracted_images": len(b_imgs),
                                "valid_images": len(b_imgs), # ScraperService'den çıkanlar zaten validated
                                "downloaded": len(local_b_imgs),
                                "media_db_records": len(local_b_imgs),
                                "html_body_images": len(local_b_imgs)
                            })
                    else:
                        body_failed += 1
                except Exception as e:
                    body_failed += 1
                    logger.error(f"[BODY] Hata #{art.id}: {e}")

        b_tasks = []
        for art in missing_bodies:
            async def bounded_process_body(a_id):
                async with sem:
                    await process_body(a_id)
            b_tasks.append(bounded_process_body(art.id))
            
        await asyncio.gather(*b_tasks)

        # RE-CHECK REMAINING
        final_missing_cover_res = await db.execute(missing_cover_query)
        final_missing_covers = final_missing_cover_res.scalars().all()
        cover_remaining = len(final_missing_covers)
        
        final_missing_body_res = await db.execute(missing_body_query)
        final_missing_bodies = final_missing_body_res.scalars().all()
        body_remaining = len(final_missing_bodies)

        print("\n" + "="*50)
        print("COVER IMAGE BACKFILL STATS:")
        print(f"TOTAL MISSING IN DB: {len(missing_covers)}")
        print(f"SCANNED: {cover_scanned}")
        print(f"REPAIRED: {cover_repaired}")
        print(f"NO IMAGE: {cover_no_image}")
        print(f"FAILED: {cover_failed}")
        print(f"REMAINING: {cover_remaining}")
        print("="*50)
        
        print("\n" + "="*50)
        print("CONTENT IMAGE BACKFILL STATS:")
        print(f"TOTAL MISSING IN DB: {len(missing_bodies)}")
        print(f"SCANNED: {body_scanned}")
        print(f"REPAIRED: {body_repaired}")
        print(f"NO IMAGE: {body_no_image}")
        print(f"FAILED: {body_failed}")
        print(f"REMAINING: {body_remaining}")
        print("="*50)
        
        print("\nDETAILED ANALYSIS (OLD ARTICLES WITH MULTIPLE IMAGES):")
        for da in detailed_old_articles:
            print(f"Article ID: {da['id']} | Source: {da['source']}")
            print(f"  - SOURCE IMAGES: {da['source_images']}")
            print(f"  - EXTRACTED IMAGES: {da['extracted_images']}")
            print(f"  - VALID IMAGES: {da['valid_images']}")
            print(f"  - DOWNLOADED: {da['downloaded']}")
            print(f"  - MEDIA DB RECORDS: {da['media_db_records']}")
            print(f"  - HTML BODY IMAGES: {da['html_body_images']}")
            print("-" * 30)

    await scraper_service.close()

if __name__ == "__main__":
    asyncio.run(run_audit())
