import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8000"

async def test_archive_system():
    logger.info("--- ARŞİV E2E TEST BAŞLIYOR ---")
    async with httpx.AsyncClient(timeout=10.0) as client:
        
        # 1. Arşiv Ana Sayfa
        logger.info("Test 1: /arsiv endpoint'i çağrılıyor...")
        resp = await client.get(f"{BASE_URL}/arsiv")
        if resp.status_code == 200:
            logger.info("✓ /arsiv başarılı.")
            if "Yıllara Göre Arşiv" in resp.text:
                logger.info("✓ /arsiv içeriği doğru (Yıllara Göre Arşiv bulundu).")
        else:
            logger.error(f"X /arsiv başarısız! HTTP {resp.status_code}")
            
        # 2. Gelişmiş Arama (Tarih filtreli)
        logger.info("Test 2: /arama endpoint'i (gelişmiş filtreler) çağrılıyor...")
        resp = await client.get(f"{BASE_URL}/arama?q=haber&start_date=2020-01-01&end_date=2030-01-01")
        if resp.status_code == 200:
            logger.info("✓ /arama başarılı.")
            if "Arama Sonuçları" in resp.text or "Sonuç bulunamadı" in resp.text:
                logger.info("✓ /arama içeriği doğru.")
        else:
            logger.error(f"X /arama başarısız! HTTP {resp.status_code}")
            
        # 3. Sitemap 
        logger.info("Test 3: /sitemap.xml çağrılıyor...")
        resp = await client.get(f"{BASE_URL}/sitemap.xml")
        if resp.status_code == 200:
            logger.info("✓ /sitemap.xml başarılı.")
            if "xml" in resp.text and "<urlset" in resp.text:
                logger.info("✓ /sitemap.xml içeriği geçerli XML.")
        else:
            logger.error(f"X /sitemap.xml başarısız! HTTP {resp.status_code}")

    logger.info("--- TESTLER TAMAMLANDI ---")

if __name__ == "__main__":
    asyncio.run(test_archive_system())
