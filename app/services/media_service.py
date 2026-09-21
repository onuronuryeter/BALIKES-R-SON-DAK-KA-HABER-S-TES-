# ===================================
# BALIKESİR SON DAKİKA HABER
# app/services/media_service.py
# ===================================

import os
import httpx
import logging
import hashlib
import io
import asyncio
from typing import Optional
from pathlib import Path
from PIL import Image

from app.config.settings import settings

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif"
}

MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

class MediaService:
    def __init__(self):
        self.upload_dir = settings.upload_dir_path / "articles"
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def download_image(self, url: str, prefix: str = "") -> Optional[str]:
        """
        Verilen URL'den görseli indirir, güvenlik kontrolünü yapar,
        ve lokal storage'a kaydeder.
        Dönüş: local file path (örn: /media/articles/...)
        """
        if not url:
            return None
            
        logger.info(f"Görsel indiriliyor: {url}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": url
        }
        
        max_retries = 3
        backoff_factor = 1.5
        
        content = None
        content_type = None

        # İndirme işlemi (Retry mekanizması ile)
        async with httpx.AsyncClient(timeout=15.0, verify=False, follow_redirects=True) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    content = response.content
                    content_type = response.headers.get("Content-Type", "").lower().split(";")[0]
                    break  # Başarılı
                except httpx.HTTPStatusError as e:
                    status = e.response.status_code
                    if status in (403, 429, 500, 502, 503, 504):
                        logger.warning(f"[MEDIA] HTTP {status} hatası, deneniyor ({attempt+1}/{max_retries}): {url}")
                        await asyncio.sleep(backoff_factor ** attempt)
                    else:
                        logger.error(f"[MEDIA] İndirme hatası (Kalıcı - HTTP {status}): {url}")
                        return None
                except Exception as e:
                    logger.warning(f"[MEDIA] Ağ hatası, deneniyor ({attempt+1}/{max_retries}): {e}")
                    await asyncio.sleep(backoff_factor ** attempt)
            
            if not content:
                logger.error(f"[MEDIA] Görsel indirilemedi (Tüm denemeler başarısız): {url}")
                return None
                
            content_length = len(content)
            
            if content_length > MAX_FILE_SIZE:
                logger.warning(f"Görsel çok büyük ({content_length} bytes): {url}")
                return None
            
            if content_length < 5000:
                logger.warning(f"Görsel anlamsız derecede küçük ({content_length} bytes), reddedildi: {url}")
                return None
                
            # Dosya imzası (Magic Bytes) & Çözünürlük doğrulaması (PIL Image.open)
            try:
                img = Image.open(io.BytesIO(content))
                img.verify() # Dosyanın bozuk olup olmadığını ve gerçekten image formatında olduğunu doğrular
                
                # verify() çağrısından sonra resmi okumak için tekrar açmak gerekir
                img = Image.open(io.BytesIO(content))
                w, h = img.size
                if w < 200 or h < 150:
                    logger.warning(f"Görsel çözünürlüğü çok küçük ({w}x{h}), reddedildi: {url}")
                    return None
            except Exception as e:
                logger.warning(f"Görsel doğrulanamadı (HTML veya bozuk dosya olabilir): {e}")
                return None
                
            ext = ""
            if content_type in ALLOWED_MIME_TYPES:
                ext = ALLOWED_MIME_TYPES[content_type]
            else:
                # URL uzantısından kurtarmayı dene
                if url.lower().endswith((".jpg", ".jpeg")):
                    ext = ".jpg"
                elif url.lower().endswith(".png"):
                    ext = ".png"
                elif url.lower().endswith(".webp"):
                    ext = ".webp"
                else:
                    ext = ".jpg" # Fallback uzantı
                
            # Dosya adını oluştur (İçeriğe göre SHA-256)
            content_hash = hashlib.sha256(content).hexdigest()[:16]
            safe_prefix = "".join(c for c in prefix if c.isalnum() or c in ('-', '_')).strip()
            if not safe_prefix:
                safe_prefix = "img"
            
            filename = f"{safe_prefix}_{content_hash}{ext}"
            file_path = self.upload_dir / filename
            local_url = f"/media/articles/{filename}"
            
            if file_path.exists():
                logger.info(f"[IMAGE] ACTION: EXISTING FILE REUSED (HASH: {content_hash})")
                return local_url
            
            # Dosyayı kaydet
            with open(file_path, "wb") as f:
                f.write(content)
                
            logger.info(f"[IMAGE] ACTION: NEW FILE CREATED (HASH: {content_hash})")
            return local_url

    async def get_fallback_image(self, query: str, prefix: str = "") -> tuple[Optional[str], Optional[str]]:
        """
        Pexels veya Pixabay API'lerini kullanarak görsel arar ve ilk bulduğunu indirir.
        Dönüş: (local_url, license_info)
        """
        words = query.split()
        search_query = " ".join(words[:3]) if len(words) > 3 else query
        
        # 1. Pexels Denemesi
        if settings.PEXELS_API_KEY:
            try:
                headers = {"Authorization": settings.PEXELS_API_KEY}
                params = {"query": search_query, "per_page": 1, "locale": "tr-TR"}
                logger.info(f"[MEDIA] Pexels'te görsel aranıyor: '{search_query}'")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get("https://api.pexels.com/v1/search", headers=headers, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("photos"):
                            photo_url = data["photos"][0]["src"]["large"]
                            logger.info(f"[MEDIA] Pexels görseli bulundu, indiriliyor...")
                            local_url = await self.download_image(photo_url, prefix=prefix)
                            if local_url:
                                return local_url, "pexels"
            except Exception as e:
                logger.warning(f"[MEDIA] Pexels API hatası: {e}")

        # 2. Pixabay Denemesi
        if settings.PIXABAY_API_KEY:
            try:
                params = {
                    "key": settings.PIXABAY_API_KEY,
                    "q": search_query,
                    "image_type": "photo",
                    "per_page": 3,
                    "safesearch": "true",
                    "lang": "tr"
                }
                logger.info(f"[MEDIA] Pixabay'da görsel aranıyor: '{search_query}'")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get("https://pixabay.com/api/", params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("hits"):
                            photo_url = data["hits"][0].get("largeImageURL") or data["hits"][0].get("webformatURL")
                            if photo_url:
                                logger.info(f"[MEDIA] Pixabay görseli bulundu, indiriliyor...")
                                local_url = await self.download_image(photo_url, prefix=prefix)
                                if local_url:
                                    return local_url, "pixabay"
            except Exception as e:
                logger.warning(f"[MEDIA] Pixabay API hatası: {e}")

        return None, None

media_service = MediaService()
