# ===================================
# BALIKESİR SON DAKİKA HABER
# app/services/relevance_engine.py
# ===================================

import re
import logging
from collections import defaultdict
from typing import Tuple, List, Dict

logger = logging.getLogger(__name__)

# Balıkesir ilçe ve önemli bölgelerinin Türkçe karakter ve 
# varyasyonlarını (I-İ, ı-i, ş-s, vb.) kapsayacak regex/kelime listesi
KEYWORDS = {
    "balikesir": ["balıkesir", "balikesir", "balikesır", "balikesır"],
    "karesi": ["karesi"],
    "altieylul": ["altıeylül", "altieylul", "altıeylul", "altı eylül"],
    "bandirma": ["bandırma", "bandirma"],
    "edremit": ["edremit", "edremit körfezi"],
    "ayvalik": ["ayvalık", "ayvalik"],
    "burhaniye": ["burhaniye"],
    "gonen": ["gönen", "gonen"],
    "erdek": ["erdek"],
    "manyas": ["manyas"],
    "susurluk": ["susurluk"],
    "sindirgi": ["sındırgı", "sindirgi", "sındırgi", "sındırgö"],
    "dursunbey": ["dursunbey"],
    "bigadic": ["bigadiç", "bigadic"],
    "ivrindi": ["ivrindi"],
    "kepsut": ["kepsut"],
    "balya": ["balya"],
    "havran": ["havran"],
    "gomec": ["gömeç", "gomec"],
    "savastepe": ["savaştepe", "savastepe"],
    "marmara": ["marmara adası", "marmara ilçesi", "marmara"],
    "avsa": ["avşa", "avsa"],
    "sarikoy": ["sarıköy", "sarikoy"],
    "ocaklar": ["ocaklar"],
    "kucukkoy": ["küçükköy", "kucukkoy"],
    "cunda": ["cunda", "alibey adası"],
    "altinoluk": ["altınoluk", "altinoluk"],
    "akcay": ["akçay", "akcay"],
    "oren": ["ören", "oren"],
    "zeytinli": ["zeytinli"],
}

NATIONAL_KEYWORDS = {
    "spor": ["futbol", "basketbol", "voleybol", "fenerbahçe", "galatasaray", "beşiktaş", "trabzonspor", "milli takım", "şampiyonlar ligi", "premier lig"],
    "ekonomi": ["enflasyon", "merkez bankası", "ekonomi", "faiz", "dolar", "euro", "borsa", "ihracat", "ithalat", "altın", "kripto", "bitcoin"],
    "politika": ["cumhurbaşkanı", "bakan", "tbmm", "milletvekili", "siyaset", "seçim", "parti", "chp", "akp", "mhp", "iyi parti"],
    "guncel": ["polis", "jandarma", "operasyon", "kaza", "yangın", "deprem", "afad", "uyarı", "sondakika", "gelişme"],
    "saglik": ["sağlık bakanlığı", "hastane", "doktor", "tedavi", "salgın", "virüs", "kanser", "ilaç"],
    "egitim": ["milli eğitim", "meb", "okul", "öğrenci", "öğretmen", "üniversite", "yök", "sınav", "yks", "lgs"],
    "teknoloji": ["teknoloji", "yapay zeka", "yazılım", "internet", "sosyal medya", "google", "apple", "microsoft", "telefon", "bilgisayar"],
    "magazin": ["oyuncu", "şarkıcı", "ünlü", "konser", "dizi", "film", "sinema", "televizyon", "magazin", "aşk"],
    "dunya": ["abd", "avrupa", "rusya", "ukrayna", "savaş", "birleşmiş milletler", "nato", "israil", "filistin", "dünya"],
    "otomobil": ["otomobil", "araç", "araba", "togg", "motor", "trafik"],
    "turizm": ["turizm", "tatil", "otel", "turist", "plaj", "uçuş", "havalimanı"],
    "3-sayfa": ["cinayet", "silah", "saldırı", "hırsızlık", "gözaltı", "tutuklandı", "mahkeme", "dava"]
}

def normalize_text(text: str) -> str:
    """Metni küçük harfe çevirir, TR karakterleri normalize eder ve noktalama işaretlerini boşlukla değiştirir."""
    if not text:
        return ""
    text = text.lower()
    
    # TR karakter normalizasyonu (arama/kıyaslama için)
    tr_map = str.maketrans("çğıöşü", "cgiosu")
    text = text.translate(tr_map)
    
    # Özel Türkçe karakterleri koruyarak noktalama işaretlerini atalım
    text = re.sub(r'[^\w\s]', ' ', text)
    return text


def evaluate_relevance(title: str, content: str) -> Tuple[int, List[str], str]:
    """
    Haberin Balıkesir ile veya Ulusal ile alakasını 0-100 arasında bir skorla döndürür.
    Ayrıca eşleşen ilçeleri/bölgeleri liste olarak verir ve muhtemel kategoriyi önerir.
    
    Dönüş:
    (skor, bulunan_ilceler_listesi, onerilen_kategori_slug)
    """
    norm_title = normalize_text(title)
    norm_content = normalize_text(content)
    
    score = 0
    matched_regions = set()
    suggested_category = ""
    
    content_full = " " + norm_content + " "
    title_full = " " + norm_title + " "

    # 1. Balıkesir/İlçe Kontrolü
    for region_key, variations in KEYWORDS.items():
        for var in variations:
            var_norm = normalize_text(var)
            var_padded = f" {var_norm} "
            
            # Başlıkta geçiyorsa
            if var_padded in title_full:
                matched_regions.add(region_key)
                if region_key == "balikesir":
                    score += 60
                else:
                    score += 50

            # İçerikte geçiyorsa
            occurrences = content_full.count(var_padded)
            if occurrences > 0:
                matched_regions.add(region_key)
                if region_key == "balikesir":
                    score += min(40, occurrences * 15)
                else:
                    score += min(35, occurrences * 10)

    # 2. Ulusal/Dünya Kontrolü (Balıkesir bulunamadıysa bile skor üretir)
    for cat_slug, keywords in NATIONAL_KEYWORDS.items():
        cat_score = 0
        for kw in keywords:
            kw_norm = normalize_text(kw)
            if f" {kw_norm} " in title_full:
                cat_score += 40
            if f" {kw_norm} " in content_full:
                cat_score += 15
                
        if cat_score > 0:
            if cat_score > score:
                suggested_category = cat_slug
            # Ulusal haber skoru ekle
            score += min(30, cat_score)
            
    # Temel haber kelimesi varsa
    if "haber" in title_full or "gelişme" in title_full or "açıklandı" in title_full:
        score += 10
        
    # Skor limitleri
    if score > 100:
        score = 100
        
    # Balıkesir değilse fakat ulusal bir haberse, asgari barajı (40) aşması için destekle
    if score < 40 and suggested_category and (len(norm_title) > 15):
        score += 20 # Sadece ulusal kategoriye uyanlara ekle

    logger.debug(f"Relevance Score: {score}, Regions: {matched_regions}, Cat: {suggested_category}, Title: '{title[:30]}...'")
    
    return score, list(matched_regions), suggested_category
