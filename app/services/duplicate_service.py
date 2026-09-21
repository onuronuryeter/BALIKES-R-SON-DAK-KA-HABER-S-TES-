# ===================================
# BALIKESİR SON DAKİKA HABER
# app/services/duplicate_service.py
# ===================================

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from thefuzz import fuzz

from app.database.models import Article
from app.services.relevance_engine import evaluate_relevance, normalize_text

logger = logging.getLogger(__name__)


def generate_content_hash(text: str) -> str:
    """Metnin SHA-256 özetini çıkarır."""
    if not text:
        return ""
    return hashlib.sha256(text.encode('utf-8', errors='ignore')).hexdigest()


async def check_duplicate(
    db: AsyncSession,
    title: str,
    original_url: Optional[str] = None,
    content: Optional[str] = None,
    check_days: int = 7
) -> Optional[Article]:
    """
    Verilen haber bilgilerinin veritabanında daha önce kayıtlı olup olmadığını kontrol eder.
    Duplicate (mükerrer) bulunursa, bulunan Article nesnesini döndürür; aksi halde None.
    
    Kontrol adımları:
    1. original_url eşleşmesi
    2. content_hash eşleşmesi
    3. content_hash eşleşmesi
    4. Fuzzy Title (Başlık benzerliği) eşleşmesi (Son X gün içinde)
    """

    # 1. URL Kontrolü
    if original_url:
        result = await db.execute(select(Article).where(Article.original_url == original_url))
        dup = result.scalar_one_or_none()
        if dup:
            logger.debug(f"Duplicate bulundu (URL): {original_url}")
            return dup



    # 3. Content Hash Kontrolü
    if content:
        c_hash = generate_content_hash(content)
        result = await db.execute(select(Article).where(Article.content_hash == c_hash))
        dup = result.scalar_one_or_none()
        if dup:
            logger.debug(f"Duplicate bulundu (Content Hash): {c_hash}")
            return dup

    # 4. Fuzzy Title Kontrolü (Son N gün)
    if title:
        cutoff = datetime.now(timezone.utc) - timedelta(days=check_days)
        recent_articles_r = await db.execute(
            select(Article).where(Article.created_at >= cutoff)
        )
        recent_articles = recent_articles_r.scalars().all()

        for art in recent_articles:
            # Token set ratio, kelime sırasından bağımsız olarak benzerliği ölçer.
            similarity = fuzz.token_set_ratio(title, art.title)
            if similarity >= 90:  # %90 ve üzeri benzerlik duplicate kabul edilir
                logger.debug(f"Duplicate bulundu (Fuzzy Title - Skor: {similarity}): '{title}' vs '{art.title}'")
                return art

    return None

async def find_similar_articles(
    db: AsyncSession,
    title: str,
    content: str,
    check_hours: int = 24
) -> list[tuple[Article, int]]:
    """
    Verilen başlık ve içeriğe benzeyen haberleri döndürür.
    Dönen liste tuple formatındadır: [(article, confidence_score), ...]
    Sadece Yüksek Güvenilirlikli (High Confidence >= 75) veya Zayıf Güvenilirlikli (Weak Match >= 50) döner.
    """
    if not title:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=check_hours)
    recent_articles_r = await db.execute(
        select(Article).where(Article.created_at >= cutoff)
    )
    recent_articles = recent_articles_r.scalars().all()

    # Orijinal haberin özelliklerini çıkar
    _, regions1, cat1 = evaluate_relevance(title, content)
    words1 = set(normalize_text(title).split())
    
    similar_articles = []
    for art in recent_articles:
        # Aynı kaynak id ise (duplicate olabilir) atlama yapmıyoruz, birleştirebiliriz
        # ama genellikle farklı kaynaklardan birleştirmek isteriz.
        
        # 1. Fuzzy Token Set Ratio (Baz Puan: 0-100, ağırlığı 0.5)
        fuzz_score = fuzz.token_set_ratio(title, art.title)
        
        if fuzz_score < 40:
            continue # Çok alakasızsa diğer hesaplamalara girme
            
        _, regions2, cat2 = evaluate_relevance(art.title, art.content or "")
        words2 = set(normalize_text(art.title).split())
        
        # 2. Lokasyon Kesişimi (+15)
        location_score = 0
        if regions1 and regions2:
            if set(regions1).intersection(set(regions2)):
                location_score = 15
        elif not regions1 and not regions2:
            # İkisinin de özel lokasyonu yok (belki ulusal)
            location_score = 5

        # 3. Kategori Uyumu (+10)
        cat_score = 10 if cat1 and cat2 and cat1 == cat2 else 0
        
        # 4. Kelime Kesişimi (Jaccard) (+25)
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        jaccard = (len(intersection) / len(union)) * 100 if union else 0
        jaccard_score = (jaccard * 0.25)
        
        # 5. Zaman Yakınlığı (+10)
        time_score = 0
        if art.created_at:
            now_utc = datetime.now(timezone.utc)
            # art.created_at aware veya naive olabilir, db den UTC gelir.
            try:
                diff = now_utc - art.created_at
                if diff.total_seconds() < 10800: # 3 saat
                    time_score = 10
            except:
                pass
                
        # 6. Event (Olay Türü) Kesişimi (YENİ SİSTEM: False Positive'i Engeller)
        # Olay fiillerini kategorize et
        def get_events(t, c):
            text = (t + " " + c).lower()
            events = set()
            if any(x in text for x in ["kaza", "çarpıştı", "yaralı", "feci kaza", "devrildi"]): events.add("kaza")
            if any(x in text for x in ["cinayet", "ölü", "vefat", "intihar", "vuruldu", "ceset"]): events.add("olum")
            if any(x in text for x in ["operasyon", "uyuşturucu", "yakalandı", "polis", "jandarma", "gözaltı", "tutuklandı"]): events.add("asayis")
            if any(x in text for x in ["toplantı", "meclis", "ziyaret", "açılış", "etkinlik", "festival", "tören"]): events.add("etkinlik")
            if any(x in text for x in ["yangın", "itfaiye", "alev", "kundaklama"]): events.add("yangin")
            if any(x in text for x in ["spor", "maç", "galibiyet", "mağlubiyet", "puan", "transfer", "şampiyon"]): events.add("spor")
            if any(x in text for x in ["hava", "yağmur", "kar", "fırtına", "uyarı", "meteoroloji"]): events.add("hava")
            if any(x in text for x in ["su kesintisi", "elektrik kesintisi", "arıza", "bakım"]): events.add("kesinti")
            return events
            
        events1 = get_events(title, content)
        events2 = get_events(art.title, art.content or "")
        
        event_penalty = 0
        event_bonus = 0
        
        if events1 and events2:
            intersection = events1.intersection(events2)
            if not intersection:
                # Olaylar tamamen farklıysa ağır ceza
                event_penalty = -60
            else:
                event_bonus = 30 # Olay tipleri aynıysa büyük bonus
        elif events1 or events2:
             # Biri net bir olaysa diğeri belirsizse hafif ceza
             event_penalty = -15
             
        # Total Confidence Hesaplama
        # Fuzz_score max 100 * 0.30 = 30
        confidence = (fuzz_score * 0.30) + location_score + cat_score + jaccard_score + time_score + event_bonus + event_penalty
        
        confidence = min(int(confidence), 100) # Max 100
        if confidence < 0:
            confidence = 0
        
        if confidence >= 50:
            logger.debug(f"Benzer haber [Conf: {confidence}]: '{title}' vs '{art.title}'")
            similar_articles.append((art, confidence))

    return similar_articles
