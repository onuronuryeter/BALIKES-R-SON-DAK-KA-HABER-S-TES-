# ===================================
# BALIKESİR SON DAKİKA HABER
# app/services/scraper_service.py
# ===================================

import httpx
import logging
import json
import re
from typing import Optional, Dict, List, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# Örnek User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 BalikesirHaberBot/1.0"

class ScraperService:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=15.0,
            follow_redirects=True,
            verify=False
        )

    async def fetch_html(self, url: str) -> Optional[str]:
        """Verilen URL'nin HTML içeriğini çeker."""
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            logger.debug(f"HTTP Status Hatası ({url}): {e.response.status_code}")
            return None
        except Exception as e:
            logger.debug(f"HTML çekme hatası ({url}): {e}")
            return None

    async def scrape_article(self, url: str, selectors: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Belirli CSS selector'ları kullanarak bir makaleyi parse eder."""
        html = await self.fetch_html(url)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "lxml")
            result = {}
            
            for key, selector in selectors.items():
                element = soup.select_one(selector)
                if element:
                    result[key] = element.get_text(strip=True)
                else:
                    result[key] = None
                    
            return result
        except Exception as e:
            logger.error(f"Scrape hatası ({url}): {e}")
            return None

    def is_suspicious_image(self, url: str) -> bool:
        """Görselin placeholder, logo veya ikon olup olmadığını kontrol eder."""
        if not url:
            return True
        url_lower = url.lower()
        suspicious_words = [
            'placeholder', 'default', 'no-image', 'no_image', 'dummy', 
            'blank', 'logo', 'avatar', 'profile', 'fallback', 'icon', 
            '1x1', 'pixel', 'tracking', 'sprite', 'svg', 'banner', 'advertisement', 'social'
        ]
        if any(word in url_lower for word in suspicious_words):
            return True
        return False

    def extract_highest_res_from_srcset(self, srcset: str, base_url: str) -> Optional[str]:
        """srcset formatından en büyük görseli seçer."""
        if not srcset:
            return None
        candidates = []
        for part in srcset.split(','):
            part = part.strip()
            if not part:
                continue
            pieces = part.split()
            url = urljoin(base_url, pieces[0])
            width = 0
            if len(pieces) > 1 and pieces[1].endswith('w'):
                try:
                    width = int(pieces[1][:-1])
                except ValueError:
                    pass
            candidates.append((width, url))
        
        if candidates:
            # En yüksek width olanı seç (Yoksa ilkini al)
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]
        return None

    async def extract_images(self, url: str) -> Dict[str, any]:
        """
        Gelişmiş Görsel Yakalama Motoru.
        Returns: {
            "cover": "URL",
            "body_images": ["URL1", "URL2", ...]
        }
        """
        result = {"cover": None, "body_images": []}
        html = await self.fetch_html(url)
        if not html:
            return result
        
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. JSON-LD Kontrolü (NewsArticle, Article)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    types = data.get("@type", "")
                    if isinstance(types, str):
                        types = [types]
                    if any(t in ["NewsArticle", "Article", "WebPage"] for t in types):
                        img_data = data.get("image")
                        if isinstance(img_data, str):
                            result["cover"] = urljoin(url, img_data)
                        elif isinstance(img_data, list) and img_data:
                            result["cover"] = urljoin(url, img_data[0])
                        elif isinstance(img_data, dict) and img_data.get("url"):
                            result["cover"] = urljoin(url, img_data.get("url"))
                        
                        if result["cover"] and not self.is_suspicious_image(result["cover"]):
                            logger.info(f"[SCRAPER] Kapak görseli JSON-LD'den bulundu: {result['cover']}")
                            break
            except Exception:
                pass
                
        # 2. Meta Etiketleri (og:image, twitter:image)
        if not result["cover"]:
            meta_tags = [
                soup.find("meta", property="og:image"),
                soup.find("meta", property="og:image:url"),
                soup.find("meta", attrs={"name": "twitter:image"}),
                soup.find("meta", attrs={"name": "twitter:image:src"})
            ]
            for tag in meta_tags:
                if tag and tag.get("content"):
                    potential_url = urljoin(url, tag.get("content"))
                    if not self.is_suspicious_image(potential_url):
                        result["cover"] = potential_url
                        logger.info(f"[SCRAPER] Kapak görseli Meta Tag'den bulundu: {potential_url}")
                        break

        # 3. Makale İçeriğinden Görsellerin Toplanması (Body Images)
        body_images = []
        article_body = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile("content|article|post", re.I))
        
        if article_body:
            # picture ve img etiketleri
            for element in article_body.find_all(["img", "picture"]):
                img_url = None
                
                if element.name == "picture":
                    source = element.find("source")
                    if source and source.get("srcset"):
                        img_url = self.extract_highest_res_from_srcset(source.get("srcset"), url)
                    if not img_url:
                        img_tag = element.find("img")
                        if img_tag:
                            element = img_tag # picture içinde img'ye düş
                        else:
                            continue
                
                if element.name == "img":
                    # Özellikleri sırayla kontrol et (Lazy load vb.)
                    src_attrs = ["data-src", "data-original", "data-lazy-src", "src"]
                    for attr in src_attrs:
                        val = element.get(attr)
                        if val and not val.startswith("data:image"):
                            img_url = urljoin(url, val)
                            break
                    
                    if not img_url and element.get("srcset"):
                        img_url = self.extract_highest_res_from_srcset(element.get("srcset"), url)

                if img_url and not self.is_suspicious_image(img_url) and img_url not in body_images:
                    # En-Boy veya gereksiz resimleri basit filter ile geç
                    width = element.get("width", "")
                    height = element.get("height", "")
                    try:
                        if width and int(re.sub(r'\D', '', str(width))) < 200:
                            continue
                        if height and int(re.sub(r'\D', '', str(height))) < 150:
                            continue
                    except:
                        pass
                    
                    body_images.append(img_url)
                    
        result["body_images"] = body_images
        logger.info(f"[SCRAPER] Bulunan İçerik Görseli Sayısı: {len(body_images)}")

        # Eğer meta etiketlerinden cover bulunamadıysa ilk uygun body resmini cover yap
        if not result["cover"] and body_images:
            result["cover"] = body_images[0]
            logger.info(f"[SCRAPER] Kapak görseli ilk içerik fotoğrafından seçildi: {result['cover']}")

        return result

    async def close(self):
        await self.client.aclose()

scraper_service = ScraperService()
