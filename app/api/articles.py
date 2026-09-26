# ===================================
# BALIKESİR SON DAKİKA HABER
# app/api/articles.py
# ===================================

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Header
from app.config.settings import settings
import os
import shutil
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc, update as sql_update
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import logging
import hashlib
import re

from app.database.database import get_db
from app.database.models import Article, Category, User, ArticleStatus
from app.api.auth import require_admin
from app.services.gatekeeper_service import image_gate_service
from app.services.push_service import broadcast_push_notification
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Pydantic Şemaları ────────────────────────────────────────────────────────

class ArticleOut(BaseModel):
    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    category_id: Optional[int] = None
    featured_image: Optional[str] = None
    status: str
    is_breaking: bool = False
    is_featured: bool = False
    published_at: Optional[datetime] = None
    created_at: datetime
    view_count: int = 0
    source_name: Optional[str] = None
    source_url: Optional[str] = None

    model_config = {"from_attributes": True}


class ArticleDetail(ArticleOut):
    content: Optional[str] = None
    original_title: Optional[str] = None
    original_url: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    canonical_url: Optional[str] = None
    keywords: Optional[str] = None
    featured_image_alt: Optional[str] = None
    featured_image_caption: Optional[str] = None
    author_id: Optional[int] = None
    source_id: Optional[int] = None


class ArticleCreate(BaseModel):
    title: str
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    category_id: Optional[int] = None
    featured_image: Optional[str] = None
    featured_image_alt: Optional[str] = None
    status: str = ArticleStatus.DRAFT.value
    is_breaking: bool = False
    is_featured: bool = False
    published_at: Optional[datetime] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    original_title: Optional[str] = None
    original_url: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    keywords: Optional[str] = None


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    category_id: Optional[int] = None
    featured_image: Optional[str] = None
    featured_image_alt: Optional[str] = None
    status: Optional[str] = None
    is_breaking: Optional[bool] = None
    is_featured: Optional[bool] = None
    published_at: Optional[datetime] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    original_title: Optional[str] = None
    original_url: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    keywords: Optional[str] = None


class PaginatedArticles(BaseModel):
    items: List[ArticleOut]
    total: int
    page: int
    per_page: int
    pages: int


# ─── Yardımcı ─────────────────────────────────────────────────────────────────

def slugify_title(title: str) -> str:
    """Başlıktan slug oluştur."""
    from slugify import slugify
    return slugify(title, allow_unicode=False)


def normalize_title(title: str) -> str:
    """Başlığı duplicate detection için normalize et."""
    title = title.lower().strip()
    title = re.sub(r"[^\w\s]", "", title, flags=re.UNICODE)
    title = re.sub(r"\s+", " ", title)
    return title


def content_hash(content: str) -> str:
    """İçerik hash'i (duplicate detection)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ─── Public Endpoint'ler ──────────────────────────────────────────────────────

@router.get("/", response_model=PaginatedArticles)
async def list_articles(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category_slug: Optional[str] = None,
    status: str = ArticleStatus.PUBLISHED.value,
    is_breaking: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """Haberleri listele (sayfalı)."""
    query = select(Article).where(Article.status == status)

    if category_slug:
        cat_result = await db.execute(
            select(Category).where(Category.slug == category_slug)
        )
        category = cat_result.scalar_one_or_none()
        if category:
            query = query.where(Article.category_id == category.id)

    if is_breaking is not None:
        query = query.where(Article.is_breaking == is_breaking)
    if is_featured is not None:
        query = query.where(Article.is_featured == is_featured)

    # Toplam sayı
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Sayfalama
    offset = (page - 1) * per_page
    query = query.order_by(desc(Article.published_at)).offset(offset).limit(per_page)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedArticles(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, (total + per_page - 1) // per_page),
    )


@router.get("/breaking", response_model=List[ArticleOut])
async def breaking_news(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Son dakika haberlerini getir."""
    result = await db.execute(
        select(Article)
        .where(Article.status == ArticleStatus.PUBLISHED.value, Article.is_breaking == True)
        .order_by(desc(Article.published_at))
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/featured", response_model=List[ArticleOut])
async def featured_articles(
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Öne çıkan haberleri getir."""
    result = await db.execute(
        select(Article)
        .where(Article.status == ArticleStatus.PUBLISHED.value, Article.is_featured == True)
        .order_by(desc(Article.published_at))
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/search", response_model=PaginatedArticles)
async def search_articles(
    q: str = Query(..., min_length=2),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Haber arama."""
    search_term = f"%{q}%"
    query = select(Article).where(
        Article.status == ArticleStatus.PUBLISHED.value,
        or_(
            Article.title.ilike(search_term),
            Article.excerpt.ilike(search_term),
            Article.content.ilike(search_term),
        ),
    )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * per_page
    query = query.order_by(desc(Article.published_at)).offset(offset).limit(per_page)
    result = await db.execute(query)

    return PaginatedArticles(
        items=result.scalars().all(),
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, (total + per_page - 1) // per_page),
    )


@router.get("/{slug}", response_model=ArticleDetail)
async def get_article(slug: str, db: AsyncSession = Depends(get_db)):
    """Slug ile haber detayı getir ve görüntülenme sayısını artır."""
    result = await db.execute(
        select(Article).where(
            Article.slug == slug,
            Article.status == ArticleStatus.PUBLISHED.value,
        )
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Haber bulunamadı")

    # Görüntülenme sayısını artır
    await db.execute(
        sql_update(Article).where(Article.id == article.id).values(view_count=Article.view_count + 1)
    )
    await db.commit()
    await db.refresh(article)
    return article


from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
import shutil
import uuid
import os

# ─── Admin Endpoint'leri ──────────────────────────────────────────────────────

@router.post("/upload_media")
async def upload_media(
    file: UploadFile = File(...),
    _: object = Depends(require_admin)
):
    """Admin: Manuel görsel yükle (Kapak & İçerik)"""
    
    # 1. İçerik ve Dosya Boyutu Kontrolü
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Yüklenen dosya boş.")
        
    # 2. Format Doğrulaması (İyileştirilmiş)
    content_type = (file.content_type or "").lower()
    filename_lower = (file.filename or "").lower()
    
    allowed_mimes = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif", "image/avif", "image/pjpeg", "image/x-png"]
    allowed_exts = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")
    
    is_valid_mime = any(mime in content_type for mime in allowed_mimes)
    is_valid_ext = filename_lower.endswith(allowed_exts)
    
    if not (is_valid_mime or is_valid_ext):
        raise HTTPException(status_code=400, detail=f"Desteklenmeyen dosya formatı: {content_type or 'Bilinmiyor'} veya geçersiz uzantı.")
    
    # Uzantıyı belirle
    ext = ".jpg"
    if "png" in content_type or filename_lower.endswith(".png"): ext = ".png"
    elif "webp" in content_type or filename_lower.endswith(".webp"): ext = ".webp"
    elif "gif" in content_type or filename_lower.endswith(".gif"): ext = ".gif"
    elif "avif" in content_type or filename_lower.endswith(".avif"): ext = ".avif"
    elif filename_lower.endswith(".jpeg"): ext = ".jpeg"
    
    # media_service klasörünü kullan
    from app.services.media_service import media_service
    import hashlib
    
    content_hash = hashlib.sha256(content).hexdigest()[:16]
    new_filename = f"manual_{content_hash}{ext}"
    
    # Dizin kontrolü ve oluşturma
    upload_dir = media_service.upload_dir
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Klasör oluşturulamadı: {str(e)}")
        
    file_path = upload_dir / new_filename
    local_url = f"/media/articles/{new_filename}"
    
    try:
        if not file_path.exists():
            with open(file_path, "wb") as f:
                f.write(content)
    except PermissionError:
        raise HTTPException(status_code=500, detail="Sunucuda klasör yazma izni (Permission) hatası var. Klasör izinlerini kontrol edin.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dosya kaydedilemedi: {str(e)}")
            
    return {"url": local_url}


@router.get("/admin/all", response_model=PaginatedArticles)
async def admin_list_articles(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    status: Optional[str] = None,
    category_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Admin: Tüm durumlarla haberleri listele."""
    query = select(Article)
    if status:
        query = query.where(Article.status == status)
    if category_id:
        query = query.where(Article.category_id == category_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * per_page
    query = query.order_by(desc(Article.created_at)).offset(offset).limit(per_page)
    result = await db.execute(query)

    return PaginatedArticles(
        items=result.scalars().all(),
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, (total + per_page - 1) // per_page),
    )


def extract_first_image_src(html_content: Optional[str]) -> Optional[str]:
    """İçerikten ilk resim etiketinin src değerini bulur."""
    if not html_content or html_content == "None":
        return None
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


@router.post("/", response_model=ArticleDetail, status_code=201)
async def create_article(
    data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Yeni haber oluştur (Admin)."""
    # Slug oluştur
    slug = data.slug or slugify_title(data.title)

    # Slug benzersizliği
    existing = await db.execute(select(Article).where(Article.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{int(datetime.now(timezone.utc).timestamp())}"

    # 'None' string temizliği
    content = "" if data.content in (None, "None") else data.content
    featured_image = None if data.featured_image in (None, "", "None") else data.featured_image
    featured_image_alt = None if data.featured_image_alt in (None, "", "None") else data.featured_image_alt
    source_url = None if data.source_url in (None, "", "None") else data.source_url
    source_name = None if data.source_name in (None, "", "None") else data.source_name
    meta_title = None if data.meta_title in (None, "", "None") else data.meta_title
    meta_description = None if data.meta_description in (None, "", "None") else data.meta_description
    excerpt = None if data.excerpt in (None, "", "None") else data.excerpt

    # Kapak görseli belirtilmemişse içerikteki ilk görseli kapak yap
    if not featured_image and content:
        featured_image = extract_first_image_src(content)

    is_pub = (data.status == ArticleStatus.PUBLISHED.value)

    # --- HARD IMAGE GATE ---
    if is_pub:
        is_valid, reason = image_gate_service.validate_publish_image(
            featured_image=featured_image,
            image_source="manual",
            image_status="available"
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Yayınlama reddedildi: {reason}")

    article = Article(
        title=data.title,
        slug=slug,
        excerpt=excerpt,
        content=content,
        category_id=data.category_id,
        author_id=current_user.id,
        featured_image=featured_image,
        featured_image_alt=featured_image_alt,
        status=data.status,
        is_published=is_pub,
        is_breaking=data.is_breaking,
        is_featured=data.is_featured,
        published_at=data.published_at or (
            datetime.now(timezone.utc) if is_pub else None
        ),
        source_url=source_url,
        source_name=source_name,
        original_title=data.original_title,
        original_url=data.original_url,
        meta_title=meta_title,
        meta_description=meta_description,
        keywords=data.keywords,
        title_normalized=normalize_title(data.title),
        content_hash=content_hash(content or ""),
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    
    if is_pub:
        asyncio.create_task(broadcast_push_notification(
            title="Yeni Haber: " + article.title,
            body=article.excerpt or "Balıkesir'den son dakika gelişmesi...",
            url=f"/haber/{article.slug}"
        ))
        
    return article


@router.patch("/{article_id}", response_model=ArticleDetail)
async def update_article(
    article_id: int,
    data: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Haber güncelle (Admin)."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Haber bulunamadı")

    update_data = data.model_dump(exclude_unset=True)

    # 'None' string temizliği
    for str_key in ["content", "featured_image", "featured_image_alt", "source_url", "source_name", "meta_title", "meta_description", "excerpt"]:
        if str_key in update_data:
            if update_data[str_key] in ("None", ""):
                update_data[str_key] = "" if str_key == "content" else None

    # Yayınlanıyorsa durum ve tarih güncelle
    if update_data.get("status") == ArticleStatus.PUBLISHED.value:
        update_data["is_published"] = True
        if not article.published_at:
            update_data["published_at"] = datetime.now(timezone.utc)
    elif "status" in update_data and update_data["status"] != ArticleStatus.PUBLISHED.value:
        update_data["is_published"] = False

    if "title" in update_data and update_data["title"]:
        update_data["title_normalized"] = normalize_title(update_data["title"])

    content_to_check = update_data.get("content", article.content)
    if "content" in update_data:
        update_data["content_hash"] = content_hash(update_data["content"] or "")

    # Kapak görseli boşsa ve içerikte görsel varsa otomatik ilk görseli kapak yap
    feat_img = update_data.get("featured_image")
    if feat_img in (None, ""):
        # Eğer mevcut makalede de yoksa veya sıfırlandıysa
        current_img = None if article.featured_image in (None, "", "None") else article.featured_image
        if not current_img or "featured_image" in update_data:
            extracted = extract_first_image_src(content_to_check)
            if extracted:
                update_data["featured_image"] = extracted
                update_data["image_status"] = "available"
                update_data["image_source"] = "extracted"
    elif "featured_image" in update_data:
        # Admin tarafından manuel bir görsel sağlandıysa (veya güncellendiyse) durumu düzelt
        update_data["image_status"] = "available"
        if not update_data.get("image_source"):
            update_data["image_source"] = "manual"

    # --- HARD IMAGE GATE ---
    if update_data.get("status") == ArticleStatus.PUBLISHED.value:
        final_img = update_data.get("featured_image", article.featured_image)
        is_valid, reason = image_gate_service.validate_publish_image(
            featured_image=final_img,
            image_source=article.image_source or "manual",
            image_status=article.image_status or "available"
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Yayınlama reddedildi: {reason}")

    for field, value in update_data.items():
        setattr(article, field, value)

    was_published = article.is_published
    await db.commit()
    await db.refresh(article)
    
    if update_data.get("status") == ArticleStatus.PUBLISHED.value and not was_published:
        asyncio.create_task(broadcast_push_notification(
            title="Yeni Haber: " + article.title,
            body=article.excerpt or "Balıkesir'den son dakika gelişmesi...",
            url=f"/haber/{article.slug}"
        ))
        
    return article


@router.delete("/{article_id}", status_code=204)
async def delete_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Haber sil (Admin)."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Haber bulunamadı")
    await db.delete(article)
    await db.commit()


@router.post("/{article_id}/publish", response_model=ArticleDetail)
async def publish_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
):
    """Haberi yayınla (Admin)."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Haber bulunamadı")

    # --- HARD IMAGE GATE ---
    is_valid, reason = image_gate_service.validate_publish_image(
        featured_image=article.featured_image,
        image_source=article.image_source or "manual",
        image_status=article.image_status or "available"
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Yayınlama reddedildi: {reason}")

    article.status = ArticleStatus.PUBLISHED.value
    if not article.published_at:
        article.published_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(article)
    
    asyncio.create_task(broadcast_push_notification(
        title="Yeni Haber: " + article.title,
        body=article.excerpt or "Balıkesir'den son dakika gelişmesi...",
        url=f"/haber/{article.slug}"
    ))
    
    return article

# ─── PUSH API (INTERNAL) ───────────────────────────────────────────────────────

@router.post("/internal/push")
async def internal_push_article(
    title: str = Form(...),
    slug: str = Form(...),
    content: str = Form(...),
    excerpt: str = Form(""),
    category_id: int = Form(0),
    original_url: str = Form(""),
    api_key: str = Header(...),
    image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    PC Worker üzerinden üretilen haberleri ve görsellerini sunucuya pushlamak için kullanılır.
    """
    if api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz API Anahtarı")
        
    # Benzersiz içerik kontrolü
    existing = await db.execute(select(Article).where(Article.slug == slug))
    if existing.scalars().first():
        return {"status": "skipped", "message": "Article already exists"}
        
    image_url = None
    if image:
        # Resmi kaydet
        filename = f"{slug}.webp"
        file_path = os.path.join(settings.upload_dir_path, "articles", filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/media/articles/{filename}"

    new_article = Article(
        title=title,
        slug=slug,
        content=content,
        excerpt=excerpt,
        category_id=category_id if category_id > 0 else None,
        original_url=original_url,
        featured_image=image_url,
        image_source="remote_worker",
        image_status="available" if image_url else "missing",
        status=ArticleStatus.PUBLISHED.value,
        published_at=datetime.now(timezone.utc),
        is_ai_generated=True,
    )
    
    db.add(new_article)
    await db.commit()
    
    asyncio.create_task(broadcast_push_notification(
        title="Yeni Haber: " + new_article.title,
        body=new_article.excerpt or "Balıkesir'den son dakika gelişmesi...",
        url=f"/haber/{new_article.slug}"
    ))
    
    # Yeni haber geldiğinde ana uygulamaya SSE eventini trigger edebiliriz,
    # frontend'deki stream zaten DB'den yeni article çekiyor, yani doğrudan düşecektir.
    
    return {"status": "success", "article_id": new_article.id}
