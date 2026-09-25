import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.database import AsyncSessionLocal
from app.database.models import Article
from sqlalchemy import select

async def delete_draft_articles():
    async with AsyncSessionLocal() as db:
        # Sadece PUBLISHED olmayan, yani hata vermiş veya bekleyen (pending_image vs) makaleleri bul
        res = await db.execute(select(Article).where(Article.status != "published"))
        articles = res.scalars().all()
        
        deleted_count = 0
        for article in articles:
            await db.delete(article)
            deleted_count += 1
            
        if deleted_count > 0:
            await db.commit()
            print(f"Başarıyla {deleted_count} adet hatalı/taslak/resimsiz haber VERİTABANINDAN SİLİNDİ!")
            print("Bu haberler eksik/bozuk oldukları için zaten yayına alınamıyordu.")
            print("Sistem yenilerini 1 dakika içinde kendi kendine HD görsellerle çekip anında yayınlayacak.")
        else:
            print("Silinecek taslak veya hatalı haber bulunamadı. Veritabanınız tertemiz.")

if __name__ == "__main__":
    asyncio.run(delete_draft_articles())
