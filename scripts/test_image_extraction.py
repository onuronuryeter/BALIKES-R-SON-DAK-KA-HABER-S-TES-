import asyncio
import sys
import logging
from pathlib import Path

# Proje kökünü Python yoluna ekle
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.services.scraper_service import scraper_service

logging.basicConfig(level=logging.INFO)

async def test_image_extraction(url: str):
    print(f"\n{'='*50}\nTEST EDILIYOR: {url}\n{'='*50}")
    
    # 1. Kaynak Analizi
    results = await scraper_service.extract_images(url)
    
    print("\n[SONUÇLAR]")
    print(f"COVER IMAGE: {results.get('cover') or 'YOK'}")
    print(f"BODY IMAGES: {len(results.get('body_images', []))} adet bulundu.")
    for idx, img in enumerate(results.get('body_images', [])):
        print(f"  - IMG {idx+1}: {img}")
    print(f"{'='*50}\n")

async def main():
    test_urls = [
        "https://www.sozcu.com.tr/bursa-da-feci-kaza-bir-olu-dort-yarali-p84518",
        "https://www.yeniakit.com.tr/haber/istanbul-kart-kullananlar-dikkat-puan-kampanyasinda-sona-gelindi-1875150.html",
        "https://yeniyasamgazetesi9.com/basta-kadinlar-tum-toplum-birlikte-mucadele-etmeli/",
        "https://www.ekonomigazetesi.com/haber/sanayi-ve-teknoloji-bakani-kacirtan-aciklamalariyla-dikkat-cekti-60341"
    ]
    
    for url in test_urls:
        await test_image_extraction(url)
        
    await scraper_service.close()

if __name__ == "__main__":
    asyncio.run(main())
