# ===================================
# BALIKESİR SON DAKİKA HABER
# app/services/ai_service.py
# ===================================

import logging
import asyncio
import time
from typing import Optional

from openai import AsyncOpenAI
import openai

from app.config.settings import settings

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower() if settings.AI_PROVIDER else "none"
        self.api_key = settings.NVIDIA_API_KEY
        self.model = settings.NVIDIA_MODEL or "nvidia/nemotron-3-ultra-550b-a55b"
        self.api_url = settings.NVIDIA_API_URL or "https://integrate.api.nvidia.com/v1"
        
        if self.api_url.endswith("/chat/completions"):
            self.api_url = self.api_url.replace("/chat/completions", "")
            
        self.temperature = settings.NVIDIA_TEMPERATURE or 1.0
        self.top_p = settings.NVIDIA_TOP_P or 0.95
        self.max_tokens = settings.NVIDIA_MAX_TOKENS or 16384
        self.reasoning_effort = settings.NVIDIA_REASONING_EFFORT or "medium"
        self.reasoning_budget = settings.NVIDIA_REASONING_BUDGET or 16384
        
        self.timeout_read = float(settings.NVIDIA_TIMEOUT) if hasattr(settings, "NVIDIA_TIMEOUT") else 180.0
        
        self.client = None
        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.api_url,
                timeout=self.timeout_read
            )

    def is_enabled(self) -> bool:
        if self.provider != "nvidia":
            return False
        if not self.api_key or not self.client:
            logger.warning("[NEMOTRON] API key missing")
            return False
        return True

    def _get_system_prompt(self) -> str:
        from app.services.ai_prompt import PROFESSIONAL_NEWS_EDITOR_PROMPT
        return PROFESSIONAL_NEWS_EDITOR_PROMPT

    async def _execute_request(self, title: str, source_text: str, source_name: Optional[str], is_stream: bool) -> Optional[str]:
        user_content = f"BAŞLIK:\n{title}\n\n"
        
        # Multi-source kontrolü için SOURCE 1, SOURCE 2 vb ayırımı article_service'te yapılır, 
        # buraya source_text olarak birleştirilmiş gelir. 
        # Fakat "Bu kaynakların aynı olayla ilişkili olduğunu varsayarak değil..." kuralını işletelim.
        if "SOURCE 2" in source_text:
            user_content += "DİKKAT: Bu kaynakların aynı olayla ilişkili olduğunu varsayarak değil, yalnızca verilen bilgilerdeki ortak olay sinyallerine göre haber oluştur.\n\n"
            
        if source_name:
            user_content += f"KAYNAK:\n{source_name}\n\n"
        user_content += f"KAYNAK İÇERİĞİ:\n{source_text}\n"

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": user_content}
        ]

        start_time = time.time()
        logger.debug(f"[NEMOTRON] Request started. Stream={is_stream} Model={self.model}")

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "max_tokens": self.max_tokens,
                "stream": is_stream,
                # NVIDIA API dökümantasyonuna göre Nemotron reasoning yapılandırması
                "extra_body": {
                    "chat_template_kwargs": {
                        "enable_thinking": True,
                        "medium_effort": (self.reasoning_effort == "medium")
                    }
                }
            }

            if is_stream:
                final_content = ""
                reasoning_log = ""
                first_chunk_time = None
                
                response = await self.client.chat.completions.create(**kwargs)
                
                async for chunk in response:
                    if first_chunk_time is None:
                        first_chunk_time = time.time() - start_time
                        logger.debug(f"[NEMOTRON] First chunk received: {first_chunk_time:.1f}s")

                    if not chunk.choices:
                        continue
                        
                    delta = chunk.choices[0].delta
                    # Düşünme kısımlarını (reasoning_content) atlıyoruz, konsola loglayabiliriz ama metne katmıyoruz.
                    reasoning = getattr(delta, "reasoning_content", None)
                    if reasoning:
                        reasoning_log += reasoning
                        
                    if delta.content is not None:
                        final_content += delta.content

                total_time = time.time() - start_time
                if reasoning_log:
                    logger.debug(f"[NEMOTRON] Reasoning accumulated. Length: {len(reasoning_log)}")
                    
                logger.info(f"[NEMOTRON] Response completed: {total_time:.1f}s")
                return final_content.strip() if final_content else None
            else:
                response = await self.client.chat.completions.create(**kwargs)
                total_time = time.time() - start_time
                logger.info(f"[NEMOTRON] Response completed: {total_time:.1f}s")
                
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    return content.strip() if content else None
                return None

        except openai.APITimeoutError as e:
            logger.error(f"[NEMOTRON] HTTP Timeout")
            raise e
        except openai.AuthenticationError as e:
            logger.error(f"[NEMOTRON] HTTP 401/403: API key invalid or access denied.")
            raise e
        except openai.UnprocessableEntityError as e:
            logger.error(f"[NEMOTRON] HTTP 422: Validation failed. Response: {e.response}")
            raise e
        except openai.RateLimitError as e:
            logger.error(f"[NEMOTRON] HTTP 429: Rate limit exceeded.")
            raise e
        except openai.APIStatusError as e:
            status_code = e.status_code
            if status_code in [500, 502, 503, 504]:
                logger.error(f"[NEMOTRON] HTTP {status_code}: Server/Gateway error.")
            elif status_code == 202:
                # 202 Pending ise 
                logger.warning(f"[NEMOTRON] HTTP 202: Result pending. (Polling simplified/aborted)")
                return None
            else:
                logger.error(f"[NEMOTRON] HTTP {status_code}: {e.message}")
            raise e
        except Exception as e:
            logger.error(f"[NEMOTRON] Unexpected Error: {e}")
            raise e

    async def generate_news_article(
        self,
        title: str,
        source_text: str,
        source_name: Optional[str] = None
    ) -> Optional[dict]:
        if not self.is_enabled():
            return None

        logger.info(f"[NEMOTRON] Article selected for generation. Source length: {len(source_text)}")

        # Önce Stream (veya config'deki stream)
        use_stream = getattr(settings, "NVIDIA_STREAM", True)
        max_attempts = 2
        
        for attempt in range(1, max_attempts + 1):
            is_stream = use_stream if attempt == 1 else False # Fallback to False
            
            try:
                logger.info(f"[NEMOTRON] Attempt {attempt}/{max_attempts} (Stream: {is_stream})")
                content = await self._execute_request(title, source_text, source_name, is_stream)
                
                if content:
                    import re
                    result = {
                        "title": None,
                        "excerpt": None,
                        "content": None,
                        "is_valid": False,
                        "reason": None,
                        "raw_output": content
                    }

                    title_match = re.search(r'BAŞLIK:\s*(.*?)\n+SPOT:', content, re.DOTALL)
                    if title_match:
                        result["title"] = title_match.group(1).strip()

                    spot_match = re.search(r'SPOT:\s*(.*?)\n+HABER:', content, re.DOTALL)
                    if spot_match:
                        result["excerpt"] = spot_match.group(1).strip()

                    haber_match = re.search(r'HABER:\s*(.*?)\n+(?:KAYNAK:|EDİTORYAL KONTROL:)', content, re.DOTALL)
                    if haber_match:
                        # Haber metnini paragraflara böl (eğer HTML etiketi yoksa)
                        raw_haber = haber_match.group(1).strip()
                        if "<p>" not in raw_haber:
                            paragraphs = [f"<p>{p.strip()}</p>" for p in raw_haber.split('\n\n') if p.strip()]
                            result["content"] = "\n".join(paragraphs)
                        else:
                            result["content"] = raw_haber
                    else:
                        # Eğer HABER bloğu tam bulunamazsa tüm metni içerik yap
                        if "<p>" not in content:
                            paragraphs = [f"<p>{p.strip()}</p>" for p in content.split('\n\n') if p.strip()]
                            result["content"] = "\n".join(paragraphs)
                        else:
                            result["content"] = content

                    yayin_karari = re.search(r'YAYIN KARARI:\s*(.*?)(?:\n|$)', content)
                    if yayin_karari:
                        karar = yayin_karari.group(1).strip()
                        if "YAYINA HAZIR" in karar:
                            result["is_valid"] = True
                        else:
                            result["is_valid"] = False

                    reason_match = re.search(r'GEREKÇE:\s*(.*)', content, re.DOTALL)
                    if reason_match:
                        result["reason"] = reason_match.group(1).strip()

                    # Fallback (Eğer yayın kararı veya formatı eksik yazarsa ama içerik varsa yine de kabul et)
                    if not yayin_karari and result["content"]:
                        result["is_valid"] = True

                    if result["is_valid"] and result["content"]:
                        word_count = len(result["content"].split())
                        logger.info(f"[NEMOTRON] Article parsed. {word_count} words. (Stream: {is_stream})")
                        return result
                    else:
                        logger.warning(f"[NEMOTRON] Validation failed. Reason: {result.get('reason')}")
                        if attempt == max_attempts:
                            return None
                else:
                    logger.error(f"[NEMOTRON] Content was empty on attempt {attempt}")
                    
            except (openai.AuthenticationError, openai.UnprocessableEntityError):
                # 401, 403, 422'de retry YOK
                return None 
            except (openai.APITimeoutError, openai.APIError) as e:
                # 429, 500, 502, 503, 504 için 1-2 sn backoff
                if attempt < max_attempts:
                    await asyncio.sleep(attempt)
            except Exception as e:
                if attempt < max_attempts:
                    await asyncio.sleep(attempt)
                    
        logger.error("[NEMOTRON] Max retries reached. RSS fallback will be used.")
        return None

ai_service = AIService()
