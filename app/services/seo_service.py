# ===================================
# BALIKESİR SON DAKİKA HABER
# app/services/seo_service.py
# ===================================

import re
import uuid
from slugify import slugify

def generate_slug(text: str, max_length: int = 100) -> str:
    """
    Verilen metinden SEO uyumlu URL (slug) oluşturur.
    Boş veya geçersiz metin gelirse benzersiz bir UUID döndürür.
    """
    if not text:
        return str(uuid.uuid4())[:8]
        
    slug = slugify(text, max_length=max_length, word_boundary=True)
    if not slug:
        return str(uuid.uuid4())[:8]
        
    return slug

def generate_fallback_meta_title(title: str) -> str:
    """Yapay zeka çalışmadığında SEO başlığı üretir."""
    if not title:
        return ""
    # Maksimum 65 karakter olmalı
    if len(title) <= 65:
        return title
    
    # 60 karaktere kadar kesip üç nokta koy
    return title[:60].rsplit(' ', 1)[0] + "..."

def generate_fallback_meta_description(content: str) -> str:
    """Yapay zeka çalışmadığında içerikten SEO açıklaması üretir."""
    if not content:
        return ""
    
    # HTML etiketlerini temizle
    clean_text = re.sub(r'<[^>]+>', ' ', content)
    # Birden fazla boşluğu teke indir
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Maksimum 155 karakter
    if len(clean_text) <= 155:
        return clean_text
        
    return clean_text[:150].rsplit(' ', 1)[0] + "..."
