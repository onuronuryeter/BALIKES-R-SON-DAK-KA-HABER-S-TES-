# ===================================
# BALIKESİR SON DAKİKA HABER
# app/services/scheduler_service.py
# ===================================

import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.database import AsyncSessionLocal
from app.database.models import Source
from app.config.settings import settings
from app.services.rss_service import rss_service
from app.services.article_service import process_and_save_article

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def fetch_all_sources_job():
    """Tüm aktif RSS kaynaklarını dolaşır ve haberleri çeker."""
    logger.info("Zamanlanmış görev başladı: fetch_all_sources_job")
    
    async with AsyncSessionLocal() as db:
        # Sadece aktif ve RSS tipindeki kaynakları al
        sources_r = await db.execute(
            select(Source).where(Source.is_active == True, Source.type == "rss")
        )
        sources = sources_r.scalars().all()
        
        total_sources = len(sources)
        total_fetched_overall = 0
        total_saved_overall = 0
        total_failed_overall = 0
        start_time = datetime.now()

        for source in sources:
            try:
                logger.info(f"[SCHEDULER] Kaynak işleniyor: {source.name}")
                items = await rss_service.fetch_feed(source.url)
                total_fetched_overall += len(items)
                
                saved_count = 0
                failed_count = 0
                for item in items:
                    try:
                        article = await process_and_save_article(db, source, item)
                        if article:
                            saved_count += 1
                    except Exception as e:
                        failed_count += 1
                        total_failed_overall += 1
                        logger.error(f"[SCHEDULER] Haber işlenirken hata oluştu ({item.get('title', 'Unknown')}): {e}", exc_info=True)
                        
                total_saved_overall += saved_count
                        
                # Kaynağın durumunu güncelle
                source.last_checked_at = datetime.now(timezone.utc)
                source.last_success_at = datetime.now(timezone.utc)
                source.total_fetched += len(items)
                source.total_imported += saved_count
                source.last_article_count = len(items)
                source.last_error = None
                
                db.add(source)
                await db.commit()
                
                logger.info(f"[SCHEDULER] Kaynak tamamlandı: {source.name} - Yeni: {saved_count} / Hata: {failed_count} / Çekilen: {len(items)}")
                
            except Exception as e:
                logger.error(f"[SCHEDULER] Kaynak işlenirken hata ({source.name}): {e}", exc_info=True)
                source.last_error = str(e)
                source.last_checked_at = datetime.now(timezone.utc)
                db.add(source)
                await db.commit()
                # Hata durumunda diğer kaynaklara devam et

        duration = (datetime.now() - start_time).total_seconds()
        
        # Job Özet Raporu
        summary = (
            f"\n================================\n"
            f"SCHEDULER RUN SUMMARY\n"
            f"Sources: {total_sources}\n"
            f"Fetched: {total_fetched_overall}\n"
            f"Saved: {total_saved_overall}\n"
            f"Failed: {total_failed_overall}\n"
            f"Duration: {duration:.1f}s\n"
            f"================================"
        )
        logger.info(summary)


def start_scheduler():
    """Zamanlayıcıyı başlatır ve görevleri ekler."""
    if not scheduler.running:
        interval_minutes = int(settings.RSS_FETCH_INTERVAL_MINUTES or 15)
        
        scheduler.add_job(
            fetch_all_sources_job,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="fetch_all_sources",
            name="RSS ve Haber Kaynaklarını Tarama",
            replace_existing=True,
            next_run_time=datetime.now(timezone.utc) # İlk çalışmayı hemen başlat
        )
        
        scheduler.start()
        logger.info(f"APScheduler başlatıldı. RSS tarama aralığı: {interval_minutes} dakika.")

def shutdown_scheduler():
    """Zamanlayıcıyı durdurur."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler durduruldu.")
