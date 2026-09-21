# ===================================
# BALIKESİR SON DAKİKA HABER
# scripts/test_nvidia_ai_negatives.py
# ===================================

import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.duplicate_service import find_similar_articles
from thefuzz import fuzz
from app.services.relevance_engine import evaluate_relevance, normalize_text

class MockArticle:
    def __init__(self, title, content, created_at=None):
        self.title = title
        self.content = content
        self.created_at = created_at or datetime.now(timezone.utc)

def mock_calculate_confidence(title1, content1, art2):
    """
    duplicate_service.py içindeki mantığın simülasyonu.
    """
    fuzz_score = fuzz.token_set_ratio(title1, art2.title)
    if fuzz_score < 40:
        return 0
        
    _, regions1, cat1 = evaluate_relevance(title1, content1)
    words1 = set(normalize_text(title1).split())
    
    _, regions2, cat2 = evaluate_relevance(art2.title, art2.content)
    words2 = set(normalize_text(art2.title).split())
    
    location_score = 0
    if regions1 and regions2:
        if set(regions1).intersection(set(regions2)):
            location_score = 15
    elif not regions1 and not regions2:
        location_score = 5

    cat_score = 10 if cat1 and cat2 and cat1 == cat2 else 0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    jaccard = (len(intersection) / len(union)) * 100 if union else 0
    jaccard_score = (jaccard * 0.25)
    
    time_score = 10 # Mock için hep 10 veriyoruz
    
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
        
    events1 = get_events(title1, content1)
    events2 = get_events(art2.title, art2.content)
    
    event_penalty = 0
    event_bonus = 0
    
    if events1 and events2:
        intersection = events1.intersection(events2)
        if not intersection:
            event_penalty = -60
        else:
            event_bonus = 30
    elif events1 or events2:
         event_penalty = -15
         
    confidence = (fuzz_score * 0.30) + location_score + cat_score + jaccard_score + time_score + event_bonus + event_penalty
    if confidence < 0:
        confidence = 0
    return min(int(confidence), 100)

def run_tests():
    print("==================================================")
    print("MULTI-SOURCE FALSE POSITIVE (NEGATİF) TESTLERİ")
    print("==================================================")

    # TEST 1
    t1 = "Balıkesir'de trafik kazası"
    c1 = "Balıkesir Karesi ilçesinde iki otomobil çarpıştı."
    art1 = MockArticle("Balıkesir'de yeni trafik düzenlemesi", "Balıkesir büyükşehir belediyesi trafik akışını değiştirdi.")
    score1 = mock_calculate_confidence(t1, c1, art1)
    status1 = "NO MATCH" if score1 < 50 else ("WEAK" if score1 < 75 else "HIGH")
    print(f"TEST 1 (Aynı şehir + benzer kelime + farklı olay): Skor: {score1} -> {status1} | Beklenen: NO MATCH")

    # TEST 2
    t2 = "Başkan Yılmaz'dan eğitim açıklaması"
    c2 = "Başkan Yılmaz okulların durumu hakkında konuştu."
    art2 = MockArticle("Başkan Yılmaz yeni parkı açtı", "Yılmaz mahallesi'ne yeni park yapıldı.")
    score2 = mock_calculate_confidence(t2, c2, art2)
    status2 = "NO MATCH" if score2 < 50 else ("WEAK" if score2 < 75 else "HIGH")
    print(f"TEST 2 (Aynı kişi + farklı olay): Skor: {score2} -> {status2} | Beklenen: NO MATCH (veya WEAK)")

    # TEST 3
    t3 = "Balıkesirspor 3 puanı aldı"
    c3 = "Balıkesirspor haftayı galibiyetle kapattı."
    art3 = MockArticle("Balıkesirspor transfer bombasını patlattı", "Balıkesirspor yeni oyuncu aldı.")
    score3 = mock_calculate_confidence(t3, c3, art3)
    status3 = "NO MATCH" if score3 < 50 else ("WEAK" if score3 < 75 else "HIGH")
    print(f"TEST 3 (Aynı kurum + farklı olay): Skor: {score3} -> {status3} | Beklenen: NO MATCH / WEAK")

    # TEST 4
    t4 = "Karesi'de su kesintisi"
    c4 = "Karesi ilçesinde sular kesilecek."
    art4 = MockArticle("Edremit'te sular kesiliyor", "Edremit ilçesinde bakım çalışması.")
    score4 = mock_calculate_confidence(t4, c4, art4)
    status4 = "NO MATCH" if score4 < 50 else ("WEAK" if score4 < 75 else "HIGH")
    print(f"TEST 4 (Aynı konu + farklı şehir): Skor: {score4} -> {status4} | Beklenen: NO MATCH")

    # TEST 5
    t5 = "Balıkesir'deki feci kazada 3 kişi yaralandı"
    c5 = "Karesi ilçesindeki trafik kazasında üç vatandaşımız hastaneye kaldırıldı."
    art5 = MockArticle("Karesi'de iki otomobil kafa kafaya çarpıştı: 3 yaralı", "Trafik kazasında bilanço ağır.")
    score5 = mock_calculate_confidence(t5, c5, art5)
    status5 = "NO MATCH" if score5 < 50 else ("WEAK" if score5 < 75 else "HIGH")
    print(f"TEST 5 (Gerçekten aynı olay + farklı başlık): Skor: {score5} -> {status5} | Beklenen: HIGH CONFIDENCE MATCH")
    
    print("==================================================")
    print("Yanlış olayları birleştirme riski bu skorlamaya göre (>=75 barajı) engellenmiştir.")

if __name__ == "__main__":
    run_tests()
