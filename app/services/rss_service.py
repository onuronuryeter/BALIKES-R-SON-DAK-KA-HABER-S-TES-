# ===================================
# BALIKESİR SON DAKİKA HABER
# app/services/rss_service.py
# ===================================

import feedparser
import logging
import httpx
import re
from typing import List, Dict, Optional
from datetime import datetime, timezone
import dateutil.parser

from app.config.settings import settings
from app.services.scraper_service import scraper_service

logger = logging.getLogger(__name__)

class RssService:
    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        """Tarih string'ini datetime objesine dönüştürür."""
        if not date_str:
            return None
        try:
            dt = dateutil.parser.parse(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception as e:
            logger.debug(f"Tarih ayrıştırma hatası ({date_str}): {e}")
            return None

    @staticmethod
    async def extract_full_text(url: str) -> str:
        """Kısa içerikli haberler için orijinal URL'den metin çeker (Sadece metin)."""
        html = await scraper_service.fetch_html(url)
        if not html:
            return ""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup(["script", "style", "iframe", "nav", "footer", "header", "aside", "form", "button"]):
                tag.decompose()
            paragraphs = soup.find_all('p')
            text_parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 40:
                    text_parts.append(f"<p>{text}</p>")
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.debug(f"Haber metni çekilemedi ({url}): {e}")
            return ""

    @staticmethod
    async def fetch_feed(url: str, max_items: int = None) -> List[Dict]:
        """
        RSS/Atom beslemesini httpx ile çeker ve feedparser ile parse eder.
        Sınırlı sayıda (max_items) haber döndürür.
        """
        if max_items is None:
            max_items = settings.MAX_ARTICLES_PER_SOURCE

        logger.info(f"RSS Çekiliyor (HTTPX): {url}")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            async with httpx.AsyncClient(timeout=15.0, verify=False, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                feed_content = response.content

            feed = feedparser.parse(feed_content)
            
            if feed.bozo and hasattr(feed, "bozo_exception"):
                logger.warning(f"RSS Parse uyarısı ({url}): {feed.bozo_exception}")
                
            if not feed.entries:
                logger.info(f"RSS'te içerik bulunamadı veya parse edilemedi: {url}")
                return []

            results = []
            for entry in feed.entries[:max_items]:
                published_str = entry.get("published", entry.get("updated", None))
                published_dt = RssService.parse_date(published_str) if published_str else datetime.now(timezone.utc)
                
                # Kapak görseli (RSS)
                image_url = None
                
                # 1. media:content
                if "media_content" in entry and entry.media_content:
                    for media in entry.media_content:
                        if media.get("medium") == "image" or media.get("type", "").startswith("image/"):
                            image_url = media.get("url")
                            break
                        if not image_url and media.get("url"):
                            image_url = media.get("url")
                            
                # 2. enclosure
                if not image_url and "enclosures" in entry and entry.enclosures:
                    for enc in entry.enclosures:
                        if enc.get("type", "").startswith("image/") or enc.get("href", "").lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                            image_url = enc.get("href")
                            break
                            
                # 3. media:thumbnail
                if not image_url and "media_thumbnail" in entry and entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0].get("url")
                
                # 4. dc:image veya diğer özel taglar
                if not image_url and "image" in entry:
                    if isinstance(entry.image, dict) and entry.image.get("href"):
                        image_url = entry.image.get("href")
                    elif isinstance(entry.image, str):
                        image_url = entry.image

                content = ""
                if "content" in entry and entry.content:
                    content = entry.content[0].value
                elif "description" in entry and len(entry.description) > len(entry.get("summary", "")):
                    content = entry.description
                elif "summary" in entry:
                    content = entry.summary
                    
                if content:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, "html.parser")
                    
                    # Eğer RSS içinde resim yoksa, description html'i içinden <img> ara
                    if not image_url:
                        img_tag = soup.find("img")
                        if img_tag and img_tag.get("src") and not scraper_service.is_suspicious_image(img_tag.get("src")):
                            image_url = img_tag.get("src")
                            logger.info(f"[RSS IMAGE] description içi img bulundu: {image_url}")

                    for tag in soup(["script", "style", "iframe", "nav", "footer", "header"]):
                        tag.decompose()
                    
                    cleaned_html = str(soup)
                    if not any(tag in cleaned_html.lower() for tag in ["<p", "<div", "<br"]):
                        content = f"<p>{cleaned_html.strip()}</p>"
                    else:
                        content = cleaned_html

                link = entry.get("link", "")
                
                # Metin çok kısaysa full text scrape
                if link and len(content) < 400:
                    logger.debug(f"Sayfa metni yetersiz, scrape ediliyor: {link}")
                    full_text = await RssService.extract_full_text(link)
                    if len(full_text) > len(content):
                        content = full_text

                # Resim ayarları (image_source ve image_status article_service'te detaylanacak)
                image_source = "rss" if image_url else None
                image_status = "available" if image_url else "missing"

                item = {
                    "title": entry.get("title", ""),
                    "link": link,
                    "guid": entry.get("id", entry.get("guid", link)),
                    "content": content,
                    "published_at": published_dt,
                    "author": entry.get("author", ""),
                    "image_url": image_url,
                    "image_source": image_source,
                    "image_status": image_status
                }
                
                if item["title"] and item["link"]:
                    results.append(item)
                    
            logger.info(f"RSS Başarılı: {url} - {len(results)} haber alındı.")
            return results
            
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP Hatası ({exc.response.status_code}) - {url}")
            raise Exception(f"HTTP Error: {exc.response.status_code}")
        except httpx.RequestError as exc:
            logger.error(f"Bağlantı Hatası - {url} - {exc}")
            raise Exception(f"Connection Error: {str(exc)}")
        except Exception as e:
            logger.error(f"RSS Parse/İşleme hatası ({url}): {e}")
            raise Exception(f"Parse Error: {str(e)}")

rss_service = RssService()
