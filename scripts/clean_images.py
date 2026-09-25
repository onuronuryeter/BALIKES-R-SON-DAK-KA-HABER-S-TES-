import asyncio
import os
import sys
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.database import AsyncSessionLocal
from app.database.models import Article
from sqlalchemy import select

async def clean_body_images():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Article))
        articles = res.scalars().all()
        updated_count = 0
        for article in articles:
            if article.content and "<figure class=\"article-content-figure" in article.content:
                soup = BeautifulSoup(article.content, "html.parser")
                for figure in soup.find_all("figure", class_="article-content-figure"):
                    figure.decompose()
                article.content = str(soup)
                updated_count += 1
        
        if updated_count > 0:
            await db.commit()
            print(f"Başarıyla {updated_count} makalenin içinden alakasız görseller temizlendi.")
        else:
            print("Temizlenecek görsel bulunamadı.")

if __name__ == "__main__":
    asyncio.run(clean_body_images())
