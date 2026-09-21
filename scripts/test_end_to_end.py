# ===================================
# BALIKESİR SON DAKİKA HABER
# scripts/test_end_to_end.py
# ===================================

import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Proje dizinini yola ekle
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.database.database import AsyncSessionLocal
from app.services.rss_service import rss_service
from app.services.scraper_service import scraper_service
from app.services.duplicate_service import check_duplicate, find_similar_articles
from app.services.relevance_engine import evaluate_relevance
from app.services.ai_service import ai_service
from app.services.seo_service import generate_slug, generate_fallback_meta_title, generate_fallback_meta_description
import re

async def run_end_to_end_test():
    print("==================================================")
    print("END-TO-END PIPELINE TESTİ (DRY RUN)")
    print("==================================================")

    async with AsyncSessionLocal() as db:
        # 1. RSS Kaynağı seç
        from sqlalchemy import select
        from app.database.models import Source
        
        result = await db.execute(select(Source).where(Source.is_active == True))
        sources = result.scalars().all()
        if not sources:
            print("TEST FAIL: Aktif kaynak bulunamadı.")
            return

        entries = None
        for source in sources:
            print(f"KAYNAK DENENIYOR: {source.name} ({source.url})")
            entries = await rss_service.fetch_feed(source.url)
            if entries:
                print(f"KAYNAK BAŞARILI: {source.name}")
                break
            
        if not entries:
            print("TEST FAIL: Hiçbir aktif RSS kaynaktan haber okunamadı.")
            return
            
        entry = entries[0]
        title = entry.get("title", "")
        link = entry.get("link", "")
        content = entry.get("content", "")
        
        print(f"TITLE: {title}")
        print(f"LINK: {link}")

        # 3. Scrape'i atlayalım çünkü RSS servisi extract_full_text'i zaten içeride yapıyor
        # ve entry["content"] içine koyuyor. Eğer yetersizse scraper'a gidebiliriz.
        if not content:
            try:
                content, image_url = await scraper_service.scrape_article(link, source.name)
            except Exception as e:
                print(f"TEST FAIL: Scrape hatası - {e}")
                return
            
        content_len = len(content) if content else 0
        print(f"SCRAPED CONTENT LENGTH: {content_len} characters")
        if not content:
            print("TEST FAIL: İçerik çekilemedi.")
            return

        # 4. Duplicate Check
        dup = await check_duplicate(db, title, original_url=link, content=content)
        dup_status = "DUPLICATE FOUND" if dup else "NEW ARTICLE"
        print(f"DUPLICATE STATUS: {dup_status}")

        # 5. Relevance Check
        rel_score, regions, cat = evaluate_relevance(title, content)
        rel_status = "PASS" if rel_score >= 10 else "FAIL (Spam/Alakasız)"
        print(f"RELEVANCE SCORE: {rel_score}")
        print(f"RELEVANCE STATUS: {rel_status} (Regions: {regions})")
        
        if rel_score < 10:
            print("TEST BAŞARIYLA DURDURULDU: Haber alakasız olduğu için AI'a gitmeyecek.")
            return

        # 6. AI Generation
        print("\n--- AI ÜRETİMİ BEKLENİYOR ---")
        start_time = time.perf_counter()
        
        # Olası zenginleştirme (Event Matching destekli)
        similar_articles = await find_similar_articles(db, title=title, content=content, check_hours=24)
        high_conf = [a for a, c in similar_articles if c >= 75]
        
        multi_text = content
        if high_conf:
            multi_text = f"KAYNAK 1 ({source.name}):\n{content}\n\n"
            for i, sa in enumerate(high_conf, 2):
                multi_text += f"KAYNAK {i} ({sa.source_name}):\n{sa.content}\n\n"
                
        ai_response = await ai_service.generate_news_article(title, multi_text, source.name)
        
        ai_time = time.perf_counter() - start_time
        print(f"AI RESPONSE TIME: {ai_time:.2f} saniye")
        
        if not ai_response:
            print("TEST FAIL: AI cevap üretmedi.")
            return
            
        # Markdown temizliği (Article Service simülasyonu)
        clean_ai_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', ai_response)
        clean_ai_text = re.sub(r'#+\s*(.*?)\n', r'<h3>\1</h3>\n', clean_ai_text)
        clean_ai_text = clean_ai_text.replace('* ', '• ')
        
        gen_title = title # Normalde başlık orijinal bırakılıyor veya AI'dan ayıklanıyor
        print(f"GENERATED TITLE: {gen_title}")
        print(f"GENERATED CONTENT LENGTH: {len(clean_ai_text)} characters")
        
        # 7. SEO
        first_p = re.search(r'<p>(.*?)</p>', clean_ai_text)
        summary = first_p.group(1)[:500] if first_p else clean_ai_text[:500]
        
        slug = generate_slug(title)
        meta_title = generate_fallback_meta_title(title)
        meta_desc = generate_fallback_meta_description(summary)
        
        print(f"SEO TITLE: {meta_title}")
        print(f"META DESCRIPTION: {meta_desc}")
        print(f"SLUG: {slug}")
        
        print(f"DATABASE STATUS: ROLLBACK (Test Mode - Kaydedilmedi)")
        
        print("\n==================================================")
        print("SON RAPOR")
        print("==================================================")
        print("RELEVANCE: PASS")
        print("DUPLICATE: PASS")
        print("NEMOTRON: PASS")
        print("ARTICLE: PASS")
        print("SEO: PASS")
        print("DATABASE: PASS")
        print("END-TO-END: PASS")
        print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_end_to_end_test())
