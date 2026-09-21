# ===================================
# BALIKESİR SON DAKİKA HABER
# app/services/market_service.py
# Piyasa fiyat servisi — Gold API + Frankfurter
# ===================================

import asyncio
import logging
import time
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ─── API Base URL'leri ────────────────────────────────────────────────────────
GOLD_API_BASE = "https://api.gold-api.com/price"
FRANKFURTER_BASE = "https://api.frankfurter.dev/v2/rate"

# ─── In-Memory Cache ─────────────────────────────────────────────────────────
_cache: Dict[str, dict] = {}
# Gold API: canlı veri — 10 sn cache
GOLD_CACHE_TTL = 10
# Frankfurter: günlük referans kur — 1 saatlik cache
FOREX_CACHE_TTL = 3600


def _is_valid_price(value: Any) -> bool:
    """Fiyat değerinin sayısal ve pozitif olduğunu doğrular."""
    try:
        v = float(value)
        return v > 0 and isinstance(v, (int, float)) and not (v != v)  # NaN kontrolü
    except (TypeError, ValueError):
        return False


async def _fetch_gold_api(symbol: str) -> Optional[dict]:
    """Gold API'den XAU veya BTC fiyatı çeker."""
    cache_key = f"gold_{symbol}"
    cached = _cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < GOLD_CACHE_TTL:
        return cached["data"]

    url = f"{GOLD_API_BASE}/{symbol}"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            raw = resp.json()

        price = raw.get("price")
        if not _is_valid_price(price):
            logger.warning(f"[MARKET] Gold API '{symbol}': geçersiz fiyat: {price!r}")
            return None

        result = {
            "price": float(price),
            "currency": raw.get("currency", "USD"),
            "updatedAt": raw.get("updatedAt"),
            "updatedAtReadable": raw.get("updatedAtReadable"),
            "name": raw.get("name", symbol),
        }
        _cache[cache_key] = {"ts": time.time(), "data": result}
        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"[MARKET] Gold API HTTP hatası ({symbol}): {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"[MARKET] Gold API bağlantı hatası ({symbol}): {e}")
        return None


async def _fetch_frankfurter(base: str, quote: str) -> Optional[dict]:
    """Frankfurter'dan günlük referans kur çeker."""
    cache_key = f"fx_{base}_{quote}"
    cached = _cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < FOREX_CACHE_TTL:
        return cached["data"]

    url = f"{FRANKFURTER_BASE}/{base.lower()}/{quote.lower()}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            raw = resp.json()

        rate = raw.get("rate")
        if not _is_valid_price(rate):
            logger.warning(f"[MARKET] Frankfurter '{base}/{quote}': geçersiz kur: {rate!r}")
            return None

        result = {
            "rate": float(rate),
            "date": raw.get("date"),
            "base": raw.get("base", base.upper()),
            "quote": raw.get("quote", quote.upper()),
        }
        _cache[cache_key] = {"ts": time.time(), "data": result}
        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"[MARKET] Frankfurter HTTP hatası ({base}/{quote}): {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"[MARKET] Frankfurter bağlantı hatası ({base}/{quote}): {e}")
        return None


def _build_item(
    id_: str,
    name: str,
    symbol: str,
    price: Optional[float],
    currency: str,
    is_live: bool,
    source: str,
    updated_at: Optional[str] = None,
    rate_type: Optional[str] = None,
    extra_date: Optional[str] = None,
) -> dict:
    """Normalize edilmiş piyasa öğesi döndürür."""
    item: dict = {
        "id": id_,
        "name": name,
        "symbol": symbol,
        "currency": currency,
        "isLive": is_live,
        "source": source,
    }
    if price is not None and _is_valid_price(price):
        item["price"] = price
        item["status"] = "ok"
    else:
        item["price"] = None
        item["status"] = "unavailable"

    if updated_at:
        item["updatedAt"] = updated_at
    if rate_type:
        item["rateType"] = rate_type
    if extra_date:
        item["rateDate"] = extra_date

    return item


async def get_market_prices() -> dict:
    """
    Tüm piyasa verilerini paralel olarak çeker, normalize eder ve döndürür.
    API hataları sistemi çökertmez — status: 'unavailable' döner.
    """
    # Paralel çekme
    xau_task = asyncio.create_task(_fetch_gold_api("XAU"))
    btc_task = asyncio.create_task(_fetch_gold_api("BTC"))
    usd_task = asyncio.create_task(_fetch_frankfurter("USD", "TRY"))
    eur_task = asyncio.create_task(_fetch_frankfurter("EUR", "TRY"))

    xau_data, btc_data, usd_data, eur_data = await asyncio.gather(
        xau_task, btc_task, usd_task, eur_task, return_exceptions=False
    )

    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()

    items = [
        _build_item(
            "gold", "Altın", "XAU",
            price=xau_data["price"] if xau_data else None,
            currency="USD",
            is_live=True,
            source="Gold API",
            updated_at=xau_data.get("updatedAt") if xau_data else None,
        ),
        _build_item(
            "btc", "Bitcoin", "BTC",
            price=btc_data["price"] if btc_data else None,
            currency="USD",
            is_live=True,
            source="Gold API",
            updated_at=btc_data.get("updatedAt") if btc_data else None,
        ),
        _build_item(
            "usdtry", "Dolar", "USD/TRY",
            price=usd_data["rate"] if usd_data else None,
            currency="TRY",
            is_live=False,
            source="Frankfurter",
            rate_type="reference",
            extra_date=usd_data.get("date") if usd_data else None,
        ),
        _build_item(
            "eurtry", "Euro", "EUR/TRY",
            price=eur_data["rate"] if eur_data else None,
            currency="TRY",
            is_live=False,
            source="Frankfurter",
            rate_type="reference",
            extra_date=eur_data.get("date") if eur_data else None,
        ),
    ]

    return {
        "updatedAt": now_iso,
        "items": items,
    }
