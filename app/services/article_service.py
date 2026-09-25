# ===================================
# BALIKESİR SON DAKİKA HABER
# app/services/article_service.py
# ===================================

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.models import Article, ArticleStatus, Category, Source, Media
from app.services.duplicate_service import check_duplicate, generate_content_hash, find_similar_articles
from app.services.relevance_engine import evaluate_relevance
from app.services.ai_service import ai_service
from app.services.seo_service import generate_slug, generate_fallback_meta_title, generate_fallback_meta_description
from app.services.media_service import media_service
from app.services.scraper_service import scraper_service
from app.services.gatekeeper_service import image_gate_service
from app.config.settings import settings
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def process_and_save_article(db: AsyncSession, source: Source, item: Dict[str, Any]) -> Optional[Article]:
    """
    Bir RSS/Scraper öğesini alır,
    Duplicate ve Relevance kontrollerinden geçirir,
    Gerekirse AI ile işler ve veritabanına kaydeder.
    """
    title = item.get("title", "")
    content = item.get("content", "")
    link = item.get("link", "")
    guid = item.get("guid", link)
    published_at = item.get("published_at", datetime.now(timezone.utc))
    author = item.get("author", "")
    image_url = item.get("image_url", None)
    image_source = item.get("image_source", "rss")
    image_status = item.get("image_status", "available")

    # 1. Hızlı Original URL Duplicate Kontrolü
    existing_url = await db.execute(select(Article).where(Article.original_url == link))
    if existing_url.scalars().first():
        logger.info(f"[DUPLICATE] Atlanıyor (URL zaten var): {link}")
        return None

    # 2. İçerik ve Başlık Duplicate Kontrolü
    dup_article = await check_duplicate(
        db=db,
        title=title,
        original_url=link,
        content=content,
        check_days=7
    )

    if dup_article:
        logger.info(f"[DUPLICATE] Atlanıyor (Benzer içerik bulundu): {title[:30]}...")
        return None

    # 3. Balıkesir Relevance (Alaka Düzeyi) Kontrolü
    relevance_score, matched_regions, suggested_category = evaluate_relevance(title, content)
    
    if relevance_score < 10:
        logger.info(f"[RELEVANCE] Atlanıyor (Alakasız - Skor: {relevance_score}): {title[:30]}...")
        return None

    # --- ADVANCED IMAGE EXTRACTION (Eğer RSS'te kapak yoksa) ---
    body_images = []
    if not image_url or image_status == "missing":
        logger.info(f"[MEDIA] RSS kapak yok, sayfadan görsel aranıyor: {link}")
        extracted_imgs = await scraper_service.extract_images(link)
        if extracted_imgs.get("cover"):
            image_url = extracted_imgs["cover"]
            image_source = "scraper"
            image_status = "available"
        if extracted_imgs.get("body_images"):
            body_images = extracted_imgs["body_images"]
            
    # Eğer RSS'te varsa bile içerik görsellerini toplamak istersen:
    if image_url and not body_images:
        # Sadece gövde fotoğraflarını çekmek için scraper'a tekrar bakabiliriz
        extracted_imgs = await scraper_service.extract_images(link)
        if extracted_imgs.get("body_images"):
            body_images = extracted_imgs["body_images"]
            # Cover scraper'da daha kaliteli bulunduysa ve RSS placeholder'a düştüyse değiştirebiliriz.
            if extracted_imgs.get("cover") and image_source == "placeholder":
                image_url = extracted_imgs["cover"]
                image_source = "scraper"
                image_status = "available"
    # -------------------------------------------------------------

    # 4. Hazırlık ve Yapay Zeka İşlemi
    final_title = title
    final_summary = content[:300] + "..." if len(content) > 300 else content
    final_content = content
    final_meta_title = ""
    final_meta_desc = ""
    is_breaking = False
    is_ai_generated = False
    
    ai_processed = False
    ai_model = None
    ai_processed_at = None
    ai_error = None
    ai_source_count = 1
    ai_enrichment_status = "not_needed"
    
    cat_slug_to_assign = None

    if ai_service.is_enabled():
        multi_source_text = content
        similar_articles = await find_similar_articles(db, title=title, content=content, check_hours=24)
        high_conf_articles = [art for art, conf in similar_articles if conf >= 75]
        
        if high_conf_articles:
            logger.info(f"[MULTI-SOURCE] {len(high_conf_articles)} yüksek güvenli eşleşme bulundu.")
            ai_source_count = len(high_conf_articles) + 1
            ai_enrichment_status = "multi_source"
            
            multi_source_text = f"KAYNAK 1 (ANA KAYNAK - {source.name}):\n{content}\n\n"
            for idx, sa in enumerate(high_conf_articles, start=2):
                multi_source_text += f"KAYNAK {idx} ({sa.source_name}):\n{sa.content}\n\n"
        else:
            ai_enrichment_status = "single_source"

        ai_result = await ai_service.generate_news_article(title, multi_source_text, source.name)
        
        if ai_result and ai_result.get("content"):
            ai_text = ai_result["content"]
            ai_text_lower = ai_text.lower()
            is_valid = True
            
            if len(ai_text) < 50:
                logger.warning("[AI VALIDATION] AI metni çok kısa.")
                is_valid = False
            
            forbidden_phrases = [
                "detaylar ilerleyen saatlerde",
                "yetkililerden edinilen bilgiye göre",
                "olayın nedeni henüz bilinmiyor",
                "yapay zeka",
                "haber:"
            ]
            for phrase in forbidden_phrases:
                if phrase in ai_text_lower and phrase not in content.lower():
                    logger.warning(f"[AI VALIDATION] Yasaklı kalıp bulundu: {phrase}")
                    is_valid = False
                    break
                    
            if is_valid:
                clean_ai_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', ai_text)
                clean_ai_text = re.sub(r'#+\s*(.*?)\n', r'<h3>\1</h3>\n', clean_ai_text)
                clean_ai_text = clean_ai_text.replace('* ', '• ')
                
                final_content = clean_ai_text
                
                if ai_result.get("title"):
                    final_title = ai_result["title"]
                    
                if ai_result.get("excerpt"):
                    final_summary = ai_result["excerpt"]
                else:
                    first_p = re.search(r'<p>(.*?)</p>', clean_ai_text)
                    if first_p:
                        final_summary = first_p.group(1)[:500]
                    else:
                        final_summary = clean_ai_text[:500]
                
                is_ai_generated = True
                ai_processed = True
                ai_model = ai_service.model
                ai_processed_at = datetime.now(timezone.utc)
            else:
                ai_error = "AI Validation failed"
                ai_enrichment_status = "fallback"
                logger.warning("[NVIDIA] API validation failed - RSS fallback used")
        else:
            ai_error = "API request failed or returned None"
            ai_enrichment_status = "fallback"
            logger.info("[NVIDIA] API failed - RSS fallback used")
                
    if not final_meta_title:
        final_meta_title = generate_fallback_meta_title(final_title)
    if not final_meta_desc:
        clean_summary = re.sub(r'<[^>]+>', '', final_summary)
        final_meta_desc = generate_fallback_meta_description(clean_summary or final_content)
        
    base_slug = generate_slug(final_title)
    final_slug = base_slug
    counter = 1
    while True:
        existing = await db.execute(select(Article.id).where(Article.slug == final_slug))
        if not existing.scalar_one_or_none():
            break
        final_slug = f"{base_slug}-{counter}"
        counter += 1
    
    # Kategori Bulma Önceliği
    category_id = None
    
    # 1. RSS Source Mapping (En Yüksek Öncelik)
    if source and source.category_id:
        category_id = source.category_id
        
    # 2. cat_slug_to_assign (Yapay Zeka vb. dışarıdan müdahale)
    if not category_id and cat_slug_to_assign:
        cat_r = await db.execute(select(Category).where(Category.slug.like(f"%{cat_slug_to_assign}%")))
        cat = cat_r.scalars().first()
        if cat:
            category_id = cat.id
            
    # 3. Mevcut Relevance Engine
    if not category_id and suggested_category:
        cat_r = await db.execute(select(Category).where(Category.slug == suggested_category))
        cat = cat_r.scalar_one_or_none()
        if cat:
            category_id = cat.id

    if not category_id:
        if matched_regions:
            region = matched_regions[0]
            cat_r = await db.execute(select(Category).where(Category.slug == region))
            cat = cat_r.scalar_one_or_none()
            if cat:
                category_id = cat.id
        
        # 4. Fallback (Güncel)
        if not category_id:
            cat_r = await db.execute(select(Category).where(Category.slug == "guncel"))
            cat = cat_r.scalar_one_or_none()
            if cat:
                category_id = cat.id

    status = ArticleStatus.PUBLISHED.value
    is_published = True
    canonical_url = f"{settings.SITE_URL}/haber/{final_slug}"

    # --- KAPAK GÖRSELİNİ İNDİR ---
    local_image_url = None
    if image_url:
        logger.info(f"[MEDIA] Kapak görseli indiriliyor ({image_source})")
        local_image_url = await media_service.download_image(image_url, prefix=final_slug[:20])

    if not local_image_url:
        logger.info("[MEDIA] Kapak görseli başarısız, Fallback API aranıyor...")
        fallback_query = final_title
        fallback_url, fallback_source = await media_service.get_fallback_image(fallback_query, prefix=final_slug[:20])
        if fallback_url:
            local_image_url = fallback_url
            image_source = fallback_source
            image_status = "available"
            image_url = fallback_url
            logger.info(f"[MEDIA] Fallback bulundu: {fallback_source}")
        else:
            logger.info("[MEDIA] FALLBACK API BAŞARISIZ. Placeholder KULLANILMIYOR.")
            image_source = "none"
            image_status = "missing"
    else:
        logger.info("[MEDIA] KAPAK GÖRSELİ BAŞARILI.")

    # --- GÖVDE GÖRSELLERİNİ İNDİR VE HTML'E ENJEKTE ET ---
    # --- GÖVDE GÖRSELLERİNİ İNDİR VE HTML'E ENJEKTE ET KISMI İPTAL EDİLDİ ---
    # Kullanıcı talebi: İlgisiz haber görsellerinin (ilgili haberler widget'larından gelen) 
    # içeriğe karışmasını önlemek için body_images kullanılmayacak.
    # Kapak görseli (HD) zaten makalenin en üstünde sergileniyor.

    source_append = f"\n\n<hr><p><strong>Kaynak:</strong> {source.name}<br><strong>Orijinal Haber:</strong> <a href='{link}' target='_blank'>Orijinal haberi görüntüle</a></p>"
    final_content += source_append

    # --- HARD IMAGE GATE / PUBLISH BLOCK SİSTEMİ KONTROLÜ ---
    final_featured_image = local_image_url or image_url
    is_valid_image, gate_reason = image_gate_service.validate_publish_image(
        featured_image=final_featured_image,
        image_source=image_source,
        image_status=image_status
    )

    if not is_valid_image:
        logger.warning(f"[HARD IMAGE GATE] Yayınlama engellendi: {gate_reason}")
        status = ArticleStatus.PENDING_IMAGE.value
        is_published = False
    else:
        status = ArticleStatus.PUBLISHED.value
        is_published = True

    # --- 6. VERİTABANI KAYDI (Article) ---
    article = Article(
        title=final_title,
        original_title=title,
        slug=final_slug,
        excerpt=final_summary[:500],
        content=final_content,
        category_id=category_id,
        source_id=source.id,
        source_url=link,
        original_url=link,
        source_name=source.name,
        featured_image=local_image_url or image_url,
        image_source_url=image_url,
        image_source=image_source,
        image_status=image_status,
        status=status,
        is_published=is_published,
        is_breaking=is_breaking,
        is_ai_generated=is_ai_generated,
        ai_processed=ai_processed,
        ai_model=ai_model,
        ai_processed_at=ai_processed_at,
        ai_error=ai_error,
        ai_source_count=ai_source_count,
        ai_enrichment_status=ai_enrichment_status,
        published_at=published_at,
        meta_title=final_meta_title,
        meta_description=final_meta_desc,
        canonical_url=canonical_url,
        content_hash=generate_content_hash(final_content)
    )

    db.add(article)
    await db.flush() # ID almak için flush ediyoruz
    
    # --- 7. VERİTABANI KAYDI (Media) ---
    if local_image_url:
        filename = local_image_url.split("/")[-1]
        media_cover = Media(
            filename=filename,
            file_path=str(media_service.upload_dir / filename),
            url=local_image_url,
            article_id=article.id,
            is_cover=True
        )
        db.add(media_cover)
        
    for lb_img in local_body_images:
        filename = lb_img.split("/")[-1]
        media_body = Media(
            filename=filename,
            file_path=str(media_service.upload_dir / filename),
            url=lb_img,
            article_id=article.id,
            is_cover=False
        )
        db.add(media_body)

    await db.commit()
    await db.refresh(article)
    
    logger.info(f"[DATABASE] Article oluşturuldu [ID: {article.id}]: {final_title[:30]}")
    return article
