from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import logging

from app.database.database import get_db
from app.database.models import PushSubscription
from app.config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()

class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: dict

@router.get("/public-key")
async def get_public_key():
    """VAPID public key'i frontend'e gönderir."""
    return {"public_key": settings.VAPID_PUBLIC_KEY}

@router.post("/subscribe")
async def subscribe(sub: PushSubscriptionCreate, db: AsyncSession = Depends(get_db)):
    """Kullanıcının push aboneliğini veritabanına kaydeder."""
    try:
        # Check if exists
        result = await db.execute(select(PushSubscription).where(PushSubscription.endpoint == sub.endpoint))
        existing = result.scalar_one_or_none()
        
        p256dh = sub.keys.get("p256dh")
        auth = sub.keys.get("auth")
        
        if not p256dh or not auth:
            raise HTTPException(status_code=400, detail="Eksik anahtarlar")

        if existing:
            existing.p256dh = p256dh
            existing.auth = auth
        else:
            new_sub = PushSubscription(
                endpoint=sub.endpoint,
                p256dh=p256dh,
                auth=auth
            )
            db.add(new_sub)
            
        await db.commit()
        return {"status": "success", "message": "Abone olundu"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Push subscribe hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))
