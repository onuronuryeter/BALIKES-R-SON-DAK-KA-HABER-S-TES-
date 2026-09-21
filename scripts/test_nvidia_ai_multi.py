# ===================================
# BALIKESİR SON DAKİKA HABER
# scripts/test_nvidia_ai_multi.py
# ===================================

import asyncio
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai_service import ai_service
from app.config.settings import settings

async def run_tests():
    print("==================================================")
    print("NVIDIA KIMI-K3 MULTI-SOURCE API TESTİ")
    print("==================================================")
    
    if not settings.NVIDIA_API_KEY:
        print("[HATA] NVIDIA_API_KEY bulunamadı!")
        return

    # TEST 1: MULTI-SOURCE (Kısa AA Haberi + TRT Haberi)
    print("\n\n--- TEST 1: MULTI-SOURCE ---")
    multi_source_text = (
        "KAYNAK 1 (ANA KAYNAK - AA):\nBalıkesir Karesi'de 2 otomobil çarpıştı. Olay yerine polis ekipleri sevk edildi. "
        "Yaralanan 3 kişi hastaneye kaldırıldı.\n\n"
        "KAYNAK 2 (TRT Haber):\nKaresi ilçesinde meydana gelen trafik kazasında iki araç kafa kafaya çarpıştı. "
        "Kazada 3 vatandaş hafif yaralandı, polis yol güvenliğini sağladı.\n\n"
        "KAYNAK 3 (Yerel Haber):\nKaresi'deki feci kazada ölen olmadı. 3 yaralı var."
    )
    title_1 = "Karesi'de Trafik Kazası"
    try:
        res_1 = await ai_service.generate_news_article(title_1, multi_source_text, "AA")
        print("SONUÇ:")
        print(res_1[:300] + "..." if res_1 else "None")
    except Exception as e:
        print(f"HATA: {e}")

    # TEST 2: SINGLE-SOURCE KISA HABER
    print("\n\n--- TEST 2: SINGLE-SOURCE KISA HABER ---")
    single_source_text = "Balıkesir'in Edremit ilçesinde zeytin hasadı başladı."
    title_2 = "Edremit'te Zeytin Hasadı"
    try:
        res_2 = await ai_service.generate_news_article(title_2, single_source_text, "DHA")
        print("SONUÇ (Model uydurma yapmamalı):")
        print(res_2[:300] + "..." if res_2 else "None")
    except Exception as e:
        print(f"HATA: {e}")

    # TEST 3: ÇELİŞEN KAYNAKLAR
    print("\n\n--- TEST 3: ÇELİŞEN KAYNAKLAR ---")
    conflict_source_text = (
        "KAYNAK 1 (AA):\nBalıkesir festivaline 100 kişi katıldı.\n\n"
        "KAYNAK 2 (TRT Haber):\nBalıkesir'deki festivale yaklaşık 150 kişinin katıldığı bildirildi.\n\n"
    )
    title_3 = "Balıkesir Festivali"
    try:
        res_3 = await ai_service.generate_news_article(title_3, conflict_source_text, "AA")
        print("SONUÇ (100 veya 150 kesin dememeli):")
        print(res_3[:300] + "..." if res_3 else "None")
    except Exception as e:
        print(f"HATA: {e}")

if __name__ == "__main__":
    asyncio.run(run_tests())
