# ===================================
# BALIKESİR SON DAKİKA HABER
# app/api/categories.py
# ===================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.database.database import get_db
from app.database.models import Category
from app.api.auth import require_admin

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Pydantic Şemaları ────────────────────────────────────────────────────────

class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    color: Optional[str] = None
    order: int = 0
    is_active: bool = True
    show_in_nav: bool = True

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    color: Optional[str] = "#e63946"
    icon: Optional[str] = None
    order: int = 0
    show_in_nav: bool = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None
    show_in_nav: Optional[bool] = None


# ─── Endpoint'ler ─────────────────────────────────────────────────────────────

@router.get("/", response_model=List[CategoryOut])
async def list_categories(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Tüm kategorileri listele."""
    query = select(Category).order_by(Category.order, Category.name)
    if active_only:
        query = query.where(Category.is_active == True)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/nav", response_model=List[CategoryOut])
async def nav_categories(db: AsyncSession = Depends(get_db)):
    """Navigasyonda gösterilecek kategorileri getir."""
    result = await db.execute(
        select(Category)
        .where(Category.is_active == True, Category.show_in_nav == True, Category.parent_id == None)
        .order_by(Category.order)
    )
    return result.scalars().all()


@router.get("/{slug}", response_model=CategoryOut)
async def get_category(slug: str, db: AsyncSession = Depends(get_db)):
    """Slug ile kategori getir."""
    result = await db.execute(select(Category).where(Category.slug == slug))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Kategori bulunamadı")
    return category


@router.post("/", response_model=CategoryOut, status_code=201)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Yeni kategori oluştur (Admin)."""
    existing = await db.execute(select(Category).where(Category.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bu slug zaten kullanımda")

    category = Category(**data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Kategori güncelle (Admin)."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Kategori bulunamadı")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Kategori sil (Admin)."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Kategori bulunamadı")
    await db.delete(category)
    await db.commit()
