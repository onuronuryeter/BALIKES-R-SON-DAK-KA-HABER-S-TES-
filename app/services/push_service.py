import json
import logging
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pywebpush import webpush, WebPushException
from app.config.settings import settings
from app.database.models import PushSubscription
from app.database.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

async def broadcast_push_notification(title: str, body: str, url: str):
    """Veritabanındaki tüm abonelere push bildirimi gönderir."""
    if not settings.VAPID_PRIVATE_KEY_PATH:
        logger.warning("VAPID_PRIVATE_KEY_PATH tanımlı değil, push atlandı.")
        return

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url
    })

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(PushSubscription))
        subscriptions = result.scalars().all()

    if not subscriptions:
        return

    for sub in subscriptions:
        try:
            sub_info = {
                "endpoint": sub.endpoint,
                "keys": {
                    "p256dh": sub.p256dh,
                    "auth": sub.auth
                }
            }
            # Pywebpush senkron çalışır, asenkron loop'u bloklamamak için asyncio.to_thread kullanıyoruz
            await asyncio.to_thread(
                webpush,
                subscription_info=sub_info,
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY_PATH,
                vapid_claims={"sub": settings.VAPID_SUBJECT}
            )
        except WebPushException as ex:
            logger.error(f"Push bildirimi başarısız: {ex}")
            # Eğer abonelik geçersizse silebiliriz, şimdilik atlıyoruz
            if ex.response and ex.response.status_code in [404, 410]:
                logger.info(f"Geçersiz abonelik siliniyor: {sub.endpoint}")
                async with AsyncSessionLocal() as session:
                    await session.delete(sub)
                    await session.commit()
        except Exception as e:
            logger.error(f"Push bildirimi beklenmeyen hata: {e}")

