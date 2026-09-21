# ===================================
# BALIKESİR SON DAKİKA HABER
# app/services/gatekeeper_service.py
# ===================================

import os
import logging
from typing import Tuple
from pathlib import Path
from app.config.settings import settings

logger = logging.getLogger(__name__)

class ImageGateService:
    @staticmethod
    def validate_publish_image(featured_image: str, image_source: str, image_status: str) -> Tuple[bool, str]:
        """
        HARD IMAGE GATE / PUBLISH BLOCK SİSTEMİ
        Bir haberin yayına (published) alınıp alınamayacağına karar verir.
        Görsel geçerliyse (True, "OK") döner.
        Görsel yoksa veya geçersizse (False, "Hata Mesajı") döner.
        """
        if not featured_image:
            logger.warning("[IMAGE GATE BLOCKED] Kapak görseli (featured_image) boş.")
            return False, "Kapak görseli bulunamadı."

        if image_status in ["missing", "invalid", "blocked"]:
            logger.warning(f"[IMAGE GATE BLOCKED] image_status = {image_status}")
            return False, f"Görsel durumu uygun değil: {image_status}"

        if image_source in ["placeholder", "none", "error"]:
            logger.warning(f"[IMAGE GATE BLOCKED] image_source = {image_source}")
            return False, f"Görsel kaynağı geçerli bir fotoğraf değil ({image_source})."

        # Eğer görsel "local" path ise (/media/articles/...)
        if featured_image.startswith("/media/articles/"):
            filename = featured_image.split("/")[-1]
            file_path = settings.upload_dir_path / "articles" / filename
            if not file_path.exists():
                logger.warning(f"[IMAGE GATE BLOCKED] Lokal dosya bulunamadı: {file_path}")
                return False, "Fiziksel görsel dosyası sunucuda bulunamadı (404)."
            
            # Placeholder kontrolü (dosya boyutu vs.)
            if file_path.stat().st_size < 5000:
                logger.warning(f"[IMAGE GATE BLOCKED] Dosya çok küçük (Placeholder/Tracking pixel şüphesi): {file_path}")
                return False, "Görsel dosyası geçerli boyutlarda değil (Placeholder veya bozuk)."

        elif featured_image.startswith("http://") or featured_image.startswith("https://"):
            # Uzak URL için - Bu aslında download_image ile local'e alınıyor olmalı,
            # ama fallback veya manuel eklenen URL olabilir.
            # Şimdilik sadece URL varlık kontrolü (Detaylı HTTP HEAD yapılabilir ama performans için basit tutuyoruz)
            pass
            
        return True, "OK"

image_gate_service = ImageGateService()
