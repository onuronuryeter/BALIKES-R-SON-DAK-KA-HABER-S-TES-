import asyncio
import sys
from pathlib import Path

# Proje kökünü Python yoluna ekle
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

import logging
from sqlalchemy import text
from app.database.database import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_media():
    logger.info("Migrating Media table to add article_id and is_cover columns...")
    async with AsyncSessionLocal() as session:
        try:
            # article_id ekle
            await session.execute(text("ALTER TABLE media ADD COLUMN article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL;"))
            logger.info("Added article_id column to media table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                logger.info("article_id column already exists.")
            else:
                logger.error(f"Error adding article_id: {e}")

        try:
            # is_cover ekle
            await session.execute(text("ALTER TABLE media ADD COLUMN is_cover BOOLEAN DEFAULT 0 NOT NULL;"))
            logger.info("Added is_cover column to media table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                logger.info("is_cover column already exists.")
            else:
                logger.error(f"Error adding is_cover: {e}")

        await session.commit()
    logger.info("Migration complete.")

if __name__ == "__main__":
    asyncio.run(migrate_media())
