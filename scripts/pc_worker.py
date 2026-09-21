import os
import sys
import asyncio
import httpx
import logging
import json
from datetime import datetime

# Uygulama kök dizinini PYTHONPATH'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import AsyncSessionLocal
from sqlalchemy import select
from app.database.models import Article

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("pc_worker")

# ----------------- YAPILANDIRMA -----------------
REMOTE_API_URL = os.getenv("REMOTE_API_URL", "http://localhost:8000/api/internal/push") # Canlı sunucu adresi (örn: https://balikesirsondakika.com/api/internal/push)
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "my-super-secret-internal-key-for-pc-worker")
LAST_PUSHED_FILE = "data/last_pushed_id.txt"
# ------------------------------------------------

def get_last_pushed_id():
    if os.path.exists(LAST_PUSHED_FILE):
        with open(LAST_PUSHED_FILE, "r") as f:
            return int(f.read().strip() or 0)
    return 0

def set_last_pushed_id(article_id):
    os.makedirs(os.path.dirname(LAST_PUSHED_FILE), exist_ok=True)
    with open(LAST_PUSHED_FILE, "w") as f:
        f.write(str(article_id))

async def push_article(article, image_path):
    data = {
        "title": article.title,
        "slug": article.slug,
        "content": article.content or "",
        "excerpt": article.excerpt or "",
        "category_id": str(article.category_id or 0),
        "original_url": article.original_url or "",
    }
    
    headers = {
        "api-key": INTERNAL_API_KEY
    }

    files = {}
    file_obj = None
    if image_path and os.path.exists(image_path):
        file_obj = open(image_path, "rb")
        files["image"] = (os.path.basename(image_path), file_obj, "image/webp")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(REMOTE_API_URL, data=data, files=files if files else None, headers=headers)
            response.raise_for_status()
            logger.info(f"✅ Başarıyla sunucuya gönderildi: {article.title}")
            return True
    except Exception as e:
        logger.error(f"❌ Sunucuya gönderilirken hata oluştu: {article.title} - {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Sunucu Yanıtı: {e.response.text}")
        return False
    finally:
        if file_obj:
            file_obj.close()

async def sync_to_remote():
    """Yerel veritabanındaki yeni haberleri canlı sunucuya gönderir."""
    last_id = get_last_pushed_id()
    logger.info(f"Senkronizasyon başlatılıyor. (Son Gönderilen ID: {last_id})")
    
    async with AsyncSessionLocal() as db:
        # Sadece pushlanmamış (ID'si son gönderilenden büyük) olanları al
        query = select(Article).where(Article.id > last_id).order_by(Article.id.asc())
        result = await db.execute(query)
        new_articles = result.scalars().all()
        
        if not new_articles:
            logger.info("Gönderilecek yeni haber bulunamadı.")
            return

        logger.info(f"Gönderilecek {len(new_articles)} yeni haber bulundu.")

        for article in new_articles:
            image_path = None
            if article.featured_image:
                # Localdeki dosya yolunu bul
                # Örn: /media/articles/slug.webp -> data/media/articles/slug.webp
                rel_path = article.featured_image.lstrip("/")
                image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", rel_path)
            
            success = await push_article(article, image_path)
            
            if success:
                set_last_pushed_id(article.id)
            else:
                logger.warning("Senkronizasyon durduruldu. Sonraki çalışmada tekrar denenecek.")
                break

async def main():
    logger.info("PC Worker başlatıldı. Önce yerel haber çekimi yapılıyor...")
    # 1. Önce yerelde RSS botunu çalıştır
    from app.services.scheduler_service import fetch_all_sources_job
    await fetch_all_sources_job()
    
    # 2. Yeni haberleri canlı sunucuya pushla
    logger.info("Yerel çekim bitti. Canlı sunucuya senkronize ediliyor...")
    await sync_to_remote()

if __name__ == "__main__":
    asyncio.run(main())
