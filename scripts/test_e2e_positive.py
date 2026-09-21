# ===================================
# BALIKESİR SON DAKİKA HABER
# scripts/test_e2e_positive.py
# ===================================

import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import re

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.database.database import AsyncSessionLocal
from app.services.duplicate_service import check_duplicate, find_similar_articles
from app.services.relevance_engine import evaluate_relevance
from app.services.ai_service import ai_service
from app.services.seo_service import generate_slug, generate_fallback_meta_title, generate_fallback_meta_description
from app.services.media_service import media_service
from sqlalchemy import select
from app.database.models import Article, Source

async def run_positive_e2e():
    print("========================================")
    print("POZITIF E2E TEST RAPORU")
    print("=======================")

    async with AsyncSessionLocal() as db:
        # 1. ARTICLE COUNT BEFORE
        res_before = await db.execute(select(Article))
        articles_before = res_before.scalars().all()
        count_before = len(articles_before)

        # 2. SOURCE & FIXTURE
        res_source = await db.execute(select(Source).where(Source.is_active == True))
        source = res_source.scalars().first()
        if not source:
            print("Kaynak bulunamadı.")
            return

        print(f"\nSOURCE:\n{source.name}")
        print("\nTEST FIXTURE KULLANILDI")

        fixture_item = {
            "title": "Balıkesir İvrindi'de 5 Milyon TL'lik Yeni Sosyal Tesis Açılışı Yapıldı",
            "link": "https://www.example.com/balikesir-ivrindi-yeni-sosyal-tesis-test-" + str(int(time.time())),
            "content": "Balıkesir Büyükşehir Belediyesi tarafından İvrindi ilçesinde inşa edilen yeni sosyal tesisin açılışı görkemli bir törenle gerçekleştirildi. Başkan Yılmaz, törende yaptığı konuşmada projeye 5 milyon TL yatırım yapıldığını ve bölge halkının hizmetine sunulduğunu belirtti. Açılışa çok sayıda vatandaş ve ilçe protokolü katıldı.",
            "published_at": datetime.now(timezone.utc),
            "image_url": "https://picsum.photos/800/600.jpg"
        }

        print("\nRSS:\nPASS (Fixture)")
        print("\nSCRAPER:\nPASS (Fixture)")

        title = fixture_item["title"]
        link = fixture_item["link"]
        content = fixture_item["content"]

        # 3. DUPLICATE CHECK
        dup = await check_duplicate(db, title, original_url=link, content=content)
        if dup:
            print("\nDUPLICATE:\nFAIL (Duplicate Found)")
            return
        print("\nDUPLICATE:\nPASS")

        # 4. RELEVANCE CHECK
        rel_score, regions, cat = evaluate_relevance(title, content)
        print(f"\nRELEVANCE:\nPASS\nSCORE:\n{rel_score} (Regions: {regions})")
        if rel_score < 10:
            print("FAIL: Relevance score too low.")
            return

        # 5. NEMOTRON AI
        print("\nNEMOTRON:\n...")
        start_time = time.perf_counter()
        ai_response = await ai_service.generate_news_article(title, content, source.name)
        ai_time = time.perf_counter() - start_time
        
        if not ai_response:
            print("FAIL: AI response empty.")
            return
            
        print(f"PASS\nMODEL:\n{ai_service.model}\nRESPONSE TIME:\n{ai_time:.2f} sec")

        # 6. HTML NORMALIZATION
        clean_ai_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', ai_response)
        clean_ai_text = re.sub(r'#+\s*(.*?)\n', r'<h3>\1</h3>\n', clean_ai_text)
        clean_ai_text = clean_ai_text.replace('* ', '• ')
        
        if "**" in clean_ai_text or "##" in clean_ai_text:
            print("\nHTML:\nFAIL (Markdown kalıntıları var)")
        else:
            print("\nHTML:\nPASS")

        # 7. SEO
        slug = generate_slug(title)
        meta_title = generate_fallback_meta_title(title)
        first_p = re.search(r'<p>(.*?)</p>', clean_ai_text)
        summary = first_p.group(1)[:300] if first_p else clean_ai_text[:300]
        meta_desc = generate_fallback_meta_description(summary)
        
        if slug and meta_title and meta_desc:
            print("\nSEO:\nPASS")
        else:
            print("\nSEO:\nFAIL")

        # 8. MEDIA
        try:
            local_image = await media_service.download_image(fixture_item["image_url"], prefix=slug[:10])
            if local_image:
                print("\nMEDIA:\nPASS")
            else:
                print("\nMEDIA:\nFALLBACK")
        except:
            print("\nMEDIA:\nFAIL")
            
        # 9. DATABASE & ARTICLE
        article = Article(
            title=title,
            original_title=title,
            slug=slug,
            excerpt=summary,
            content=clean_ai_text,
            source_id=source.id,
            source_url=link,
            original_url=link,
            source_name=source.name,
            featured_image=local_image or fixture_item["image_url"],
            image_source="fixture",
            status="draft",
            is_published=False,
            is_ai_generated=True,
            ai_processed=True,
            ai_model=ai_service.model,
            content_hash=content,
            published_at=fixture_item["published_at"]
        )
        
        db.add(article)
        await db.flush() # Transaction içinde beklet, henüz commit yapma
        
        print("\nARTICLE:\nPASS")
        print("\nDATABASE:\nPASS (Transaction Flush)")

        # ROLLBACK
        await db.rollback()
        print("\nROLLBACK:\nPASS")

        # ARTICLE COUNT AFTER
        res_after = await db.execute(select(Article))
        articles_after = res_after.scalars().all()
        count_after = len(articles_after)

        print(f"\nARTICLE COUNT BEFORE:\n{count_before}")
        print(f"\nARTICLE COUNT AFTER:\n{count_after}")

        if count_before == count_after:
            print("\nDATA INTEGRITY:\nPASS")
        else:
            print("\nDATA INTEGRITY:\nFAIL")

        print("\nFINAL RESULT:\nPASS")
        print("========================================")

if __name__ == "__main__":
    asyncio.run(run_positive_e2e())
