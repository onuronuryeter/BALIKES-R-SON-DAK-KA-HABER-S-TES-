# ===================================
# BALIKESİR SON DAKİKA HABER
# scripts/test_nemotron_real.py
# ===================================

import asyncio
import os
import time

from dotenv import load_dotenv
import openai
from openai import AsyncOpenAI

async def run_test():
    print("============================================================")
    print("GERCEK NVIDIA NEMOTRON API TESTI")
    
    # 1. DOTENV VE KEY KONTROLÜ
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    
    model_name = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
    print(f"MODEL: {model_name}")
    
    if not api_key or api_key == "API_ANAHTARINIZI_BURAYA_GIRIN":
        print("API KEY: NOT FOUND (Veya varsayılan placeholder kullanılıyor)")
        print("RESULT: FAIL")
        print("ERROR TYPE: ConfigurationError")
        print("ERROR: NVIDIA_API_KEY .env dosyasında bulunamadı veya değiştirilmedi.")
        return

    print("API KEY: FOUND")
    print()

    # 2. CLIENT BAŞLATMA
    client = AsyncOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        max_retries=0,
        timeout=180.0,
    )

    start = time.perf_counter()

    # 3. API İSTEĞİ (KISA, TARAFTARSIZ, BASİT)
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": "Balıkesir hakkında tek cümlelik kısa ve tarafsız bir bilgi ver."
                }
            ],
            temperature=1.0,
            top_p=0.95,
            max_tokens=64,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            },
            stream=False,
        )

        elapsed = time.perf_counter() - start

        print("HTTP: 200")
        print(f"RESPONSE TIME: {elapsed:.2f} sec")

        if not response.choices:
            print("RESULT: FAIL")
            print("ERROR TYPE: EmptyResponseError")
            print("ERROR: Model API cevap döndürdü ancak choices dizisi boş geldi.")
            return

        content = response.choices[0].message.content or ""

        print("--- MODEL CEVABI ---")
        print(content)
        print("--------------------")
        print(f"CONTENT LENGTH: {len(content)}")
        print("RESULT: PASS")

    except openai.AuthenticationError as e:
        elapsed = time.perf_counter() - start
        print(f"RESPONSE TIME: {elapsed:.2f} sec")
        print("RESULT: FAIL")
        print("ERROR TYPE: AuthenticationError")
        print("ERROR: NVIDIA_API_KEY geçersiz veya süresi dolmuş olabilir. Lütfen anahtarı kontrol edin.")
    except openai.RateLimitError as e:
        elapsed = time.perf_counter() - start
        print(f"RESPONSE TIME: {elapsed:.2f} sec")
        print("RESULT: FAIL")
        print("ERROR TYPE: RateLimitError")
        print("ERROR: NVIDIA API limitlerine ulaşıldı. Lütfen daha sonra tekrar deneyin.")
    except openai.APIConnectionError as e:
        elapsed = time.perf_counter() - start
        print(f"RESPONSE TIME: {elapsed:.2f} sec")
        print("RESULT: FAIL")
        print("ERROR TYPE: APIConnectionError")
        print("ERROR: NVIDIA API endpoint'ine bağlantı kurulamadı. Ağ veya DNS problemi olabilir.")
    except openai.APITimeoutError as e:
        elapsed = time.perf_counter() - start
        print(f"RESPONSE TIME: {elapsed:.2f} sec")
        print("RESULT: FAIL")
        print("ERROR TYPE: APITimeoutError")
        print("ERROR: Model yanıtı belirtilen 180 saniyelik süre içinde alınamadı.")
    except openai.NotFoundError as e:
        elapsed = time.perf_counter() - start
        print(f"RESPONSE TIME: {elapsed:.2f} sec")
        print("RESULT: FAIL")
        print("ERROR TYPE: NotFoundError")
        print(f"ERROR: Belirtilen model ({model_name}) API tarafından bulunamadı veya erişim yetkisi yok.")
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"RESPONSE TIME: {elapsed:.2f} sec")
        print("RESULT: FAIL")
        print(f"ERROR TYPE: {type(e).__name__}")
        print("ERROR: Beklenmeyen bir hata oluştu.")

if __name__ == "__main__":
    asyncio.run(run_test())
