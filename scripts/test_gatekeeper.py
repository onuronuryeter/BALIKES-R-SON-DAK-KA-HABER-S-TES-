import asyncio
import os
import sys

# Proje dizinini sys.path'e ekleyelim
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.gatekeeper_service import image_gate_service
from app.database.models import ArticleStatus

async def run_tests():
    print("--- HARD IMAGE GATE TESTLERİ ---")

    # Senaryo 1: Görsel hiç yok
    valid, reason = image_gate_service.validate_publish_image(
        featured_image=None,
        image_source="none",
        image_status="missing"
    )
    print(f"Test 1 (Görsel Yok): {'PASS' if not valid else 'FAIL'} - {reason}")

    # Senaryo 2: Geçersiz statü (blocked)
    valid, reason = image_gate_service.validate_publish_image(
        featured_image="http://example.com/image.jpg",
        image_source="rss",
        image_status="blocked"
    )
    print(f"Test 2 (Blocked Status): {'PASS' if not valid else 'FAIL'} - {reason}")

    # Senaryo 3: Placeholder source
    valid, reason = image_gate_service.validate_publish_image(
        featured_image="/media/articles/placeholder.jpg",
        image_source="placeholder",
        image_status="available"
    )
    print(f"Test 3 (Placeholder Source): {'PASS' if not valid else 'FAIL'} - {reason}")

    # Senaryo 4: Local file bulunamadı
    valid, reason = image_gate_service.validate_publish_image(
        featured_image="/media/articles/does_not_exist_999.jpg",
        image_source="rss",
        image_status="available"
    )
    print(f"Test 4 (Missing Local File): {'PASS' if not valid else 'FAIL'} - {reason}")

    # Senaryo 5: Başarılı test (Uzak URL, kontrol basit olduğu için şimdilik valid dönmeli)
    valid, reason = image_gate_service.validate_publish_image(
        featured_image="https://www.example.com/valid_image.jpg",
        image_source="rss",
        image_status="available"
    )
    print(f"Test 5 (Valid Remote URL): {'PASS' if valid else 'FAIL'} - {reason}")

if __name__ == "__main__":
    asyncio.run(run_tests())
