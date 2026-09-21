# ===================================
# BALIKESİR SON DAKİKA HABER
# app/api/market.py
# Piyasa fiyat API endpoint'i
# ===================================

import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.market_service import get_market_prices

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/prices")
async def market_prices():
    """
    Piyasa fiyatlarını normalize edilmiş JSON olarak döndürür.
    GET /api/market/prices

    Her zaman 200 döner — bireysel item'lar status: 'unavailable' içerebilir.
    Bu endpoint haber sistemini ASLA etkilemez.
    """
    try:
        data = await get_market_prices()
        return JSONResponse(content=data)
    except Exception as e:
        logger.error(f"[MARKET API] Beklenmedik hata: {e}")
        # Güvenli fallback — asla 500 dönme, haber sitesi bozulmasın
        return JSONResponse(content={
            "updatedAt": None,
            "items": [
                {"id": "gold",   "name": "Altın",   "symbol": "XAU",     "price": None, "currency": "USD", "isLive": True,  "source": "Gold API",    "status": "unavailable"},
                {"id": "btc",    "name": "Bitcoin", "symbol": "BTC",     "price": None, "currency": "USD", "isLive": True,  "source": "Gold API",    "status": "unavailable"},
                {"id": "usdtry", "name": "Dolar",   "symbol": "USD/TRY", "price": None, "currency": "TRY", "isLive": False, "source": "Frankfurter", "status": "unavailable"},
                {"id": "eurtry", "name": "Euro",    "symbol": "EUR/TRY", "price": None, "currency": "TRY", "isLive": False, "source": "Frankfurter", "status": "unavailable"},
            ]
        })
