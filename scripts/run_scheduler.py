# ===================================
# BALIKESİR SON DAKİKA HABER
# scripts/run_scheduler.py
# 
# [!] DİKKAT: Bu script yalnızca FastAPI (run.bat) çalıştırılmadığında veya 
# ayrık (standalone) bir worker (ör: cron job) kurulduğunda kullanılmalıdır. 
# FastAPI halihazırda lifespan üzerinden scheduler'ı başlattığı için,
# bunu FastAPI çalışırken kullanmak Duplicate işlemler doğurabilir!
# ===================================

import sys
import logging
import asyncio
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from app.database.database import AsyncSessionLocal
from app.services.scheduler_service import fetch_all_sources_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("=" * 50)
    logger.info("BALIKESİR SON DAKİKA HABER — Scheduler Test")
    logger.info("=" * 50)
    
    # fetch_all_sources_job expects no arguments because it creates its own session inside.
    # Wait, let's check scheduler_service.py's fetch_all_sources_job signature first.
    await fetch_all_sources_job()
        
    logger.info("Test tamamlandı.")

if __name__ == "__main__":
    asyncio.run(main())
