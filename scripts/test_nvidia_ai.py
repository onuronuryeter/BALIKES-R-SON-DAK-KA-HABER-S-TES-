# ===================================
# BALIKESİR SON DAKİKA HABER
# scripts/test_nvidia_ai.py
# ===================================

import asyncio
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings
import openai
from openai import AsyncOpenAI

async def run_tests():
    print("==================================================")
    print("NVIDIA NEMOTRON API TESTİ (HIZLI BAĞLANTI)")
    print("==================================================")
    print(f"API KEY: {'FOUND' if settings.NVIDIA_API_KEY else 'MISSING'}")
    if not settings.NVIDIA_API_KEY:
        return

    client = AsyncOpenAI(
        api_key=settings.NVIDIA_API_KEY,
        base_url="https://integrate.api.nvidia.com/v1",
        timeout=180.0
    )
    
    model_name = "nvidia/nemotron-3-ultra-550b-a55b"

    # ----------------------------------------------------
    # TEST B: BASIC NON-STREAM (THINKING OFF)
    # ----------------------------------------------------
    print("\nTEST B - BASIC NON-STREAM")
    print("REQUEST START: Testing without reasoning...")
    
    test_b_pass = False
    start_b = time.time()
    try:
        res_b = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Merhaba, tek cümleyle Balıkesir."}],
            temperature=1,
            top_p=0.95,
            max_tokens=16,
            stream=False,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            }
        )
        elapsed_b = time.time() - start_b
        print("HTTP STATUS: 200 OK")
        print(f"RESPONSE TIME: {elapsed_b:.2f}s")
        print(f"RESPONSE: {res_b.choices[0].message.content.strip()}")
        print("RESULT: PASS")
        test_b_pass = True
    except openai.APIStatusError as e:
        print(f"HTTP STATUS: {e.status_code}")
        print("RESULT: FAIL")
        print(f"ERROR TYPE: APIStatusError")
        print(f"ERROR: {e.message}")
    except Exception as e:
        print("RESULT: FAIL")
        print(f"ERROR TYPE: {type(e).__name__}")
        print(f"ERROR: {e}")

    if not test_b_pass:
        print("\nTEST B BAŞARISIZ OLDU. REASONING TESTLERİNE (C ve D) GEÇİLMİYOR.")
        return

    # ----------------------------------------------------
    # TEST C: THINKING NON-STREAM
    # ----------------------------------------------------
    print("\nTEST C - THINKING NON-STREAM")
    start_c = time.time()
    try:
        res_c = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Balıkesir'in coğrafi konumu hakkında 2 cümle yaz."}],
            temperature=1,
            top_p=0.95,
            max_tokens=64,
            stream=False,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": True,
                    "medium_effort": True
                }
            }
        )
        elapsed_c = time.time() - start_c
        print("HTTP: 200 OK")
        print(f"RESPONSE TIME: {elapsed_c:.2f}s")
        print(f"CONTENT LENGTH: {len(res_c.choices[0].message.content)}")
        print("THINKING ENABLED: TRUE")
        print("PASS")
    except Exception as e:
        print("FAIL")
        print(f"ERROR: {e}")
        return

    # ----------------------------------------------------
    # TEST D: STREAMING
    # ----------------------------------------------------
    print("\nTEST D - STREAMING")
    start_d = time.time()
    try:
        res_d = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Kısa bir hikaye başlat."}],
            temperature=1,
            top_p=0.95,
            max_tokens=128,
            stream=True,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": True,
                    "medium_effort": True
                }
            }
        )
        
        first_chunk_time = None
        chunk_count = 0
        async for chunk in res_d:
            if first_chunk_time is None:
                first_chunk_time = time.time() - start_d
            chunk_count += 1
            
        total_time_d = time.time() - start_d
        print(f"FIRST CHUNK: {first_chunk_time:.2f} seconds")
        print(f"CHUNK COUNT: {chunk_count}")
        print(f"TOTAL TIME: {total_time_d:.2f} seconds")
        print("STREAM: PASS")
    except Exception as e:
        print("STREAM: FAIL")
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(run_tests())
