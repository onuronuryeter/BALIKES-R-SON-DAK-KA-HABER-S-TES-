# ===================================
# BALIKESİR SON DAKİKA HABER
# app/api/sources.py — RSS Kaynak Yönetimi
# ===================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database.database import get_db
from app.database.models import Source
from app.api.auth import require_admin

router = APIRouter()


class SourceOut(BaseModel):
    id: int
    name: str
    url: str
    type: str
    category_id: Optional[int] = None
    is_active: bool
    priority: int = 0
    last_checked_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_error: Optional[str] = None
    last_article_count: int = 0
    total_fetched: int = 0
    total_imported: int = 0
    fetch_interval_minutes: int = 15
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SourceCreate(BaseModel):
    name: str
    url: str
    type: str = "rss"
    category_id: Optional[int] = None
    is_active: bool = True
    priority: int = 0
    fetch_interval_minutes: int = 15
    description: Optional[str] = None


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    type: Optional[str] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    fetch_interval_minutes: Optional[int] = None
    description: Optional[str] = None


@router.get("/", response_model=List[SourceOut])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Tüm RSS kaynaklarını listele (Admin)."""
    result = await db.execute(select(Source).order_by(Source.name))
    return result.scalars().all()


@router.post("/", response_model=SourceOut, status_code=201)
async def create_source(
    data: SourceCreate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Yeni RSS kaynağı ekle (Admin)."""
    source = Source(**data.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.patch("/{source_id}", response_model=SourceOut)
async def update_source(
    source_id: int,
    data: SourceUpdate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
):
    """RSS kaynağı güncelle (Admin)."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Kaynak bulunamadı")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
):
    """RSS kaynağı sil (Admin)."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Kaynak bulunamadı")
    await db.delete(source)
    await db.commit()
