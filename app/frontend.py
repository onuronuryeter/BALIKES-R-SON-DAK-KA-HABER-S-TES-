# ===================================
# BALIKESİR SON DAKİKA HABER
# app/frontend.py — Frontend HTML Sayfa Router
# ===================================

from fastapi import APIRouter, Request, Depends, HTTPException, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, and_
from sqlalchemy.orm import joinedload
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import logging
import asyncio
import json
from fastapi.responses import StreamingResponse
from app.config.settings import settings
from app.database.database import get_db, AsyncSessionLocal
from app.database.models import (
    Article, Category, Source, User, SiteSetting, ArticleStatus, Comment
)
from app.api.auth import get_current_user, require_admin, get_password_hash, authenticate_user, create_access_token, COOKIE_NAME

logger = logging.getLogger(__name__)
router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


# ─── Template Yardımcıları ────────────────────────────────────────────────────

async def get_base_context(db: AsyncSession, request: Request, active_category: str = "") -> dict:
    """Tüm sayfalarda ortak kullanılan template context verilerini döndürür."""
    current_user = await get_current_user(request, db)

    # Top Nav Kategorileri
    top_nav_slugs = ["son-dakika", "guncel", "dunya", "ekonomi", "spor", "magazin"]
    top_nav_result = await db.execute(
        select(Category)
        .where(Category.slug.in_(top_nav_slugs))
    )
    top_nav_categories_unordered = top_nav_result.scalars().all()
    top_nav_categories = sorted(top_nav_categories_unordered, key=lambda c: top_nav_slugs.index(c.slug))

    # Sub Nav Kategorileri
    sub_nav_slugs = ["politika", "finans", "teknoloji", "kultur-sanat", "kadin", "moda", "otomobil", "yasam", "saglik", "turizm", "egitim", "3-sayfa"]
    sub_nav_result = await db.execute(
        select(Category)
        .where(Category.slug.in_(sub_nav_slugs))
    )
    sub_nav_categories_unordered = sub_nav_result.scalars().all()
    sub_nav_categories = sorted(sub_nav_categories_unordered, key=lambda c: sub_nav_slugs.index(c.slug))

    # Son dakika haberleri (ticker için)
    breaking_result = await db.execute(
        select(Article)
        .where(Article.status == ArticleStatus.PUBLISHED.value, Article.is_breaking == True)
        .order_by(desc(Article.published_at))
        .limit(8)
    )
    breaking_news = breaking_result.scalars().all()

    # Popüler haberler
    popular_result = await db.execute(
        select(Article)
        .where(Article.status == ArticleStatus.PUBLISHED.value)
        .order_by(desc(Article.view_count))
        .limit(7)
    )
    popular_articles = popular_result.scalars().all()

    # İlçeler — parent slug "ilceler" olan alt kategorileri getir
    ilceler_parent_r = await db.execute(select(Category).where(Category.slug == "ilceler"))
    ilceler_parent = ilceler_parent_r.scalar_one_or_none()
    if ilceler_parent:
        ilceler_result = await db.execute(
            select(Category)
            .where(Category.parent_id == ilceler_parent.id, Category.is_active == True)
            .order_by(Category.order)
        )
        ilceler = ilceler_result.scalars().all()
    else:
        # "ilceler" slug yoksa — tüm parent_id'si olan kategorilerden ilk 12'yi al
        ilceler_result = await db.execute(
            select(Category)
            .where(Category.is_active == True, Category.parent_id != None)
            .order_by(Category.order)
            .limit(12)
        )
        ilceler = ilceler_result.scalars().all()

    return {
        "request": request,
        "site_name": settings.SITE_NAME,
        "site_url": settings.SITE_URL,
        "site_description": settings.SITE_DESCRIPTION,
        "top_nav_categories": top_nav_categories,
        "sub_nav_categories": sub_nav_categories,
        "breaking_news": breaking_news,
        "popular_articles": popular_articles,
        "ilceler": ilceler,
        "active_category": active_category,
        "search_query": request.query_params.get("q", ""),
        "current_year": datetime.now(timezone.utc).year,
        "current_user": current_user,
    }


# ─── ANA SAYFA ───────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, db: AsyncSession = Depends(get_db)):
    """Ana sayfa."""
    ctx = await get_base_context(db, request)

    # Öne çıkan haberler (manşet)
    featured_result = await db.execute(
        select(Article)
        .where(Article.status == ArticleStatus.PUBLISHED.value)
        .order_by(desc(Article.is_featured), desc(Article.published_at))
        .limit(26)
    )
    ctx["featured_articles"] = featured_result.scalars().all()

    # Son haberler
    latest_result = await db.execute(
        select(Article)
        .where(Article.status == ArticleStatus.PUBLISHED.value)
        .order_by(desc(Article.published_at))
        .limit(9)
    )
    ctx["latest_articles"] = latest_result.scalars().all()

    # Son dakika (sidebar)
    ctx["breaking_articles"] = ctx["breaking_news"]

    # Balıkesir haberleri
    balk_cat = await db.execute(select(Category).where(Category.slug == "balikesir"))
    balk_cat = balk_cat.scalar_one_or_none()
    if balk_cat:
        balk_result = await db.execute(
            select(Article)
            .where(Article.status == ArticleStatus.PUBLISHED.value, Article.category_id == balk_cat.id)
            .order_by(desc(Article.published_at))
            .limit(9)
        )
        ctx["balikesir_articles"] = balk_result.scalars().all()
    else:
        ctx["balikesir_articles"] = []

    # Kategori bölümleri (Spor, Ekonomi, Teknoloji, vb.)
    section_slugs = [
        ("Gündem", "gundem", "#c1121f"),
        ("Spor", "spor", "#023e8a"),
        ("Ekonomi", "ekonomi", "#2d6a4f"),
        ("Teknoloji", "teknoloji", "#4361ee"),
        ("Yaşam", "yasam", "#f4a261"),
        ("Kültür Sanat", "kultur-sanat", "#9b2226"),
    ]
    category_sections = []
    for name, slug, color in section_slugs:
        cat_r = await db.execute(select(Category).where(Category.slug == slug))
        cat = cat_r.scalar_one_or_none()
        if cat:
            art_r = await db.execute(
                select(Article)
                .where(Article.status == ArticleStatus.PUBLISHED.value, Article.category_id == cat.id)
                .order_by(desc(Article.published_at))
                .limit(4)
            )
            articles = art_r.scalars().all()
            if articles:
                category_sections.append({
                    "name": cat.name, "slug": cat.slug,
                    "color": cat.color or color, "articles": articles
                })
    ctx["category_sections"] = category_sections

    return templates.TemplateResponse("index.html", ctx)


# ─── HABER DETAY ─────────────────────────────────────────────────────────────

@router.get("/haber/{slug}", response_class=HTMLResponse)
async def article_detail(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Haber detay sayfası."""
    result = await db.execute(
        select(Article).where(Article.slug == slug, Article.status == ArticleStatus.PUBLISHED.value)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404)
        
    # Kategori 'reklam' ise /reklam/slug adresine yönlendir
    cat_r = await db.execute(select(Category).where(Category.id == article.category_id))
    category = cat_r.scalar_one_or_none()
    if category and category.slug == "reklam":
        return RedirectResponse(url=f"/reklam/{slug}", status_code=301)

    return await render_article_page(request, db, article, category)


@router.get("/reklam/{slug}", response_class=HTMLResponse)
async def reklam_detail(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Reklam/Sponsorlu içerik detay sayfası."""
    result = await db.execute(
        select(Article).where(Article.slug == slug, Article.status == ArticleStatus.PUBLISHED.value)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404)
        
    cat_r = await db.execute(select(Category).where(Category.id == article.category_id))
    category = cat_r.scalar_one_or_none()
    
    if not category or category.slug != "reklam":
        return RedirectResponse(url=f"/haber/{slug}", status_code=301)

    return await render_article_page(request, db, article, category)


async def render_article_page(request: Request, db: AsyncSession, article: Article, category: Category):
    """Ortak haber/reklam render mantığı."""

    # Görüntülenme artır
    article.view_count += 1
    await db.commit()
    await db.refresh(article)

    ctx = await get_base_context(db, request)
    ctx["article"] = article

    # Kategori
    if article.category_id:
        cat_r = await db.execute(select(Category).where(Category.id == article.category_id))
        ctx["category"] = cat_r.scalar_one_or_none()
    else:
        ctx["category"] = None

    # İlgili haberler (aynı kategoriden)
    if article.category_id:
        rel_r = await db.execute(
            select(Article)
            .where(
                Article.status == ArticleStatus.PUBLISHED.value,
                Article.category_id == article.category_id,
                Article.id != article.id
            )
            .order_by(desc(Article.published_at))
            .limit(3)
        )
        ctx["related_articles"] = rel_r.scalars().all()
    else:
        ctx["related_articles"] = []

    # Yorumları Getir
    comments_r = await db.execute(
        select(Comment)
        .options(joinedload(Comment.user))
        .where(Comment.article_id == article.id, Comment.status == "published")
        .order_by(desc(Comment.created_at))
    )
    ctx["comments"] = comments_r.scalars().all()

    return templates.TemplateResponse("article.html", ctx)


# ─── KATEGORİ ────────────────────────────────────────────────────────────────

@router.get("/kategori/{slug}", response_class=HTMLResponse)
async def category_page(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    sayfa: int = Query(1, alias="sayfa", ge=1),
):
    """Kategori haber listesi sayfası."""
    cat_r = await db.execute(
        select(Category)
        .options(joinedload(Category.parent))
        .where(Category.slug == slug, Category.is_active == True)
    )
    category = cat_r.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404)

    per_page = 12
    query = select(Article).where(
        Article.status == ArticleStatus.PUBLISHED.value,
        Article.category_id == category.id
    )

    total_r = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_r.scalar() or 0

    offset = (sayfa - 1) * per_page
    art_r = await db.execute(query.order_by(desc(Article.published_at)).offset(offset).limit(per_page))
    articles = art_r.scalars().all()

    # Alt kategoriler
    sub_r = await db.execute(
        select(Category).where(Category.parent_id == category.id, Category.is_active == True).order_by(Category.order)
    )
    sub_categories = sub_r.scalars().all()

    ctx = await get_base_context(db, request, active_category=slug)
    ctx.update({
        "category": category,
        "articles": articles,
        "sub_categories": sub_categories,
        "total": total,
        "page": sayfa,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    })

    return templates.TemplateResponse("category.html", ctx)


# ─── ARŞİV ───────────────────────────────────────────────────────────────────

@router.get("/arsiv", response_class=HTMLResponse)
async def archive_index(request: Request, db: AsyncSession = Depends(get_db)):
    """Arşiv ana sayfası (Yıllar)."""
    # SQLite'da yılları almak için strftime kullanıyoruz
    query = select(func.strftime('%Y', Article.published_at).label('year'), func.count(Article.id).label('count'))\
        .where(Article.status == ArticleStatus.PUBLISHED.value)\
        .group_by('year')\
        .order_by(desc('year'))
    
    result = await db.execute(query)
    years = [{"year": row.year, "count": row.count} for row in result.all() if row.year]
    
    ctx = await get_base_context(db, request)
    ctx.update({
        "archive_type": "index",
        "years": years,
        "title": "Haber Arşivi",
        "description": "Geçmişten günümüze tüm haberlerin arşivi."
    })
    return templates.TemplateResponse("arsiv.html", ctx)

@router.get("/arsiv/{year}", response_class=HTMLResponse)
async def archive_year(
    year: str, 
    request: Request, 
    db: AsyncSession = Depends(get_db),
    sayfa: int = Query(1, alias="sayfa", ge=1)
):
    """Yıl arşivi sayfası."""
    per_page = 12
    base_query = select(Article).where(
        Article.status == ArticleStatus.PUBLISHED.value,
        func.strftime('%Y', Article.published_at) == year
    )
    
    total_r = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = total_r.scalar() or 0
    
    offset = (sayfa - 1) * per_page
    art_r = await db.execute(base_query.order_by(desc(Article.published_at)).offset(offset).limit(per_page))
    articles = art_r.scalars().all()
    
    # Ayları getir
    month_query = select(func.strftime('%m', Article.published_at).label('month'), func.count(Article.id).label('count'))\
        .where(Article.status == ArticleStatus.PUBLISHED.value, func.strftime('%Y', Article.published_at) == year)\
        .group_by('month')\
        .order_by('month')
    
    m_result = await db.execute(month_query)
    months = [{"month": row.month, "count": row.count} for row in m_result.all() if row.month]
    
    ctx = await get_base_context(db, request)
    ctx.update({
        "archive_type": "year",
        "year": year,
        "months": months,
        "articles": articles,
        "total": total,
        "page": sayfa,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "title": f"{year} Yılı Haber Arşivi",
        "description": f"{year} yılında yayınlanan tüm haberler."
    })
    return templates.TemplateResponse("arsiv.html", ctx)

@router.get("/arsiv/{year}/{month}", response_class=HTMLResponse)
async def archive_month(
    year: str, 
    month: str, 
    request: Request, 
    db: AsyncSession = Depends(get_db),
    sayfa: int = Query(1, alias="sayfa", ge=1)
):
    """Ay arşivi sayfası."""
    month = month.zfill(2)
    per_page = 12
    base_query = select(Article).where(
        Article.status == ArticleStatus.PUBLISHED.value,
        func.strftime('%Y', Article.published_at) == year,
        func.strftime('%m', Article.published_at) == month
    )
    
    total_r = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = total_r.scalar() or 0
    
    offset = (sayfa - 1) * per_page
    art_r = await db.execute(base_query.order_by(desc(Article.published_at)).offset(offset).limit(per_page))
    articles = art_r.scalars().all()
    
    ctx = await get_base_context(db, request)
    ctx.update({
        "archive_type": "month",
        "year": year,
        "month": month,
        "articles": articles,
        "total": total,
        "page": sayfa,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "title": f"{month}. Ay {year} Haber Arşivi",
        "description": f"{year} yılı {month}. ayında yayınlanan tüm haberler."
    })
    return templates.TemplateResponse("arsiv.html", ctx)

@router.get("/arsiv/{year}/{month}/{day}", response_class=HTMLResponse)
async def archive_day(
    year: str, 
    month: str, 
    day: str,
    request: Request, 
    db: AsyncSession = Depends(get_db),
    sayfa: int = Query(1, alias="sayfa", ge=1)
):
    """Gün arşivi sayfası."""
    month = month.zfill(2)
    day = day.zfill(2)
    per_page = 12
    base_query = select(Article).where(
        Article.status == ArticleStatus.PUBLISHED.value,
        func.strftime('%Y', Article.published_at) == year,
        func.strftime('%m', Article.published_at) == month,
        func.strftime('%d', Article.published_at) == day
    )
    
    total_r = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = total_r.scalar() or 0
    
    offset = (sayfa - 1) * per_page
    art_r = await db.execute(base_query.order_by(desc(Article.published_at)).offset(offset).limit(per_page))
    articles = art_r.scalars().all()
    
    ctx = await get_base_context(db, request)
    ctx.update({
        "archive_type": "day",
        "year": year,
        "month": month,
        "day": day,
        "articles": articles,
        "total": total,
        "page": sayfa,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "title": f"{day}.{month}.{year} Haberleri",
        "description": f"{day}.{month}.{year} tarihinde yayınlanan tüm haberler."
    })
    return templates.TemplateResponse("arsiv.html", ctx)

# ─── ARAMA ───────────────────────────────────────────────────────────────────

@router.get("/arama", response_class=HTMLResponse)
async def search_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    q: str = Query("", alias="q"),
    start_date: str = Query(None, alias="start_date"),
    end_date: str = Query(None, alias="end_date"),
    category_id: int = Query(None, alias="category_id"),
    sayfa: int = Query(1, alias="sayfa", ge=1),
):
    """Arama sonuçları sayfası."""
    ctx = await get_base_context(db, request)
    ctx["query"] = q
    ctx["start_date"] = start_date
    ctx["end_date"] = end_date
    ctx["category_id"] = category_id
    ctx["articles"] = []
    ctx["total"] = 0
    ctx["page"] = sayfa
    ctx["pages"] = 1
    
    # Tüm kategorileri filtre dropdown'u için getir
    cat_r = await db.execute(select(Category).where(Category.is_active == True).order_by(Category.name))
    ctx["all_categories"] = cat_r.scalars().all()

    if q and len(q.strip()) >= 2:
        per_page = 12
        search = f"%{q.strip()}%"
        
        # Filtreleri ekleyerek query oluştur
        conditions = [
            Article.status == ArticleStatus.PUBLISHED.value,
            or_(
                Article.title.ilike(search),
                Article.excerpt.ilike(search),
                Article.content.ilike(search),
            )
        ]
        
        if category_id:
            conditions.append(Article.category_id == category_id)
            
        if start_date:
            try:
                # Beklenen format: YYYY-MM-DD
                dt_start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                conditions.append(Article.published_at >= dt_start)
            except ValueError:
                pass
                
        if end_date:
            try:
                # Günü tam kapsamak için saati 23:59:59 yapıyoruz
                dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
                conditions.append(Article.published_at <= dt_end)
            except ValueError:
                pass

        query = select(Article).where(and_(*conditions))
        
        total_r = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_r.scalar() or 0

        offset = (sayfa - 1) * per_page
        art_r = await db.execute(query.order_by(desc(Article.published_at)).offset(offset).limit(per_page))

        ctx["articles"] = art_r.scalars().all()
        ctx["total"] = total
        ctx["per_page"] = per_page
        ctx["pages"] = max(1, (total + per_page - 1) // per_page)

    return templates.TemplateResponse("search.html", ctx)


# ─── KURUMSAL SAYFALAR ───────────────────────────────────────────────────────

@router.get("/hakkimizda", response_class=HTMLResponse)
async def about_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Hakkımızda sayfası."""
    ctx = await get_base_context(db, request)
    return templates.TemplateResponse("hakkimizda.html", ctx)


@router.get("/iletisim", response_class=HTMLResponse)
async def contact_page(request: Request, db: AsyncSession = Depends(get_db)):
    """İletişim sayfası."""
    ctx = await get_base_context(db, request)
    return templates.TemplateResponse("iletisim.html", ctx)



@router.get("/gizlilik", response_class=HTMLResponse)
async def privacy_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Gizlilik Politikası sayfası."""
    ctx = await get_base_context(db, request)
    return templates.TemplateResponse("gizlilik.html", ctx)

@router.get("/kullanim-sartlari", response_class=HTMLResponse)
async def terms_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Kullanım Şartları sayfası."""
    ctx = await get_base_context(db, request)
    return templates.TemplateResponse("kullanim-sartlari.html", ctx)


# ─── SEO: ROBOTS.TXT ─────────────────────────────────────────────────────────

@router.get("/robots.txt", response_class=Response)
async def robots_txt():
    """robots.txt dosyası."""
    site_url = settings.SITE_URL
    content = f"""User-agent: *
Allow: /
Disallow: /admin
Disallow: /api/
Disallow: /arama

Sitemap: {site_url}/sitemap.xml
Sitemap: {site_url}/sitemap-news.xml
"""
    return Response(content=content, media_type="text/plain")


# ─── SEO: SITEMAP ────────────────────────────────────────────────────────────

@router.get("/sitemap.xml", response_class=Response)
async def sitemap_xml(db: AsyncSession = Depends(get_db)):
    """Ana sitemap.xml — kategoriler ve haberler."""
    site_url = settings.SITE_URL

    urls = [
        f"""  <url>
    <loc>{site_url}/</loc>
    <changefreq>hourly</changefreq>
    <priority>1.0</priority>
  </url>"""
    ]

    # Kategoriler
    cat_r = await db.execute(select(Category).where(Category.is_active == True))
    for cat in cat_r.scalars().all():
        urls.append(f"""  <url>
    <loc>{site_url}/kategori/{cat.slug}</loc>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>""")

    # Haberler
    art_r = await db.execute(
        select(Article, Category.slug.label("cat_slug"))
        .outerjoin(Category, Article.category_id == Category.id)
        .where(Article.status == ArticleStatus.PUBLISHED.value)
        .order_by(desc(Article.published_at))
        .limit(1000)
    )
    
    for row in art_r.all():
        art = row[0]
        cat_slug = row.cat_slug
        dt = art.published_at.strftime("%Y-%m-%d") if art.published_at else ""
        
        prefix = "reklam" if cat_slug == "reklam" else "haber"
        urls.append(f"""  <url>
    <loc>{site_url}/{prefix}/{art.slug}</loc>
    <lastmod>{dt}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""
    return Response(content=xml, media_type="application/xml")


@router.get("/rss", response_class=Response)
async def rss_feed(db: AsyncSession = Depends(get_db)):
    """RSS 2.0 Feed."""
    site_url = settings.SITE_URL
    site_name = settings.SITE_NAME
    site_desc = settings.SITE_DESCRIPTION

    art_r = await db.execute(
        select(Article)
        .where(Article.status == ArticleStatus.PUBLISHED.value)
        .order_by(desc(Article.published_at))
        .limit(50)
    )
    articles = art_r.scalars().all()

    items = []
    for art in articles:
        pub = art.published_at.strftime("%a, %d %b %Y %H:%M:%S +0300") if art.published_at else ""
        items.append(f"""    <item>
      <title><![CDATA[{art.title}]]></title>
      <link>{site_url}/haber/{art.slug}</link>
      <description><![CDATA[{art.excerpt or ''}]]></description>
      <pubDate>{pub}</pubDate>
      <guid isPermaLink="true">{site_url}/haber/{art.slug}</guid>
    </item>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>{site_name}</title>
    <link>{site_url}</link>
    <description>{site_desc}</description>
{chr(10).join(items)}
  </channel>
</rss>"""
    return Response(content=xml, media_type="application/xml")


@router.get("/sitemap-news.xml", response_class=Response)
async def sitemap_news_xml(db: AsyncSession = Depends(get_db)):
    """Google News sitemap — son 48 saatteki haberler."""
    from datetime import timedelta
    site_url = settings.SITE_URL
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    art_r = await db.execute(
        select(Article)
        .where(
            Article.status == ArticleStatus.PUBLISHED.value,
            Article.published_at >= cutoff
        )
        .order_by(desc(Article.published_at))
        .limit(1000)
    )

    items = []
    for art in art_r.scalars().all():
        pub = art.published_at.strftime("%Y-%m-%dT%H:%M:%S+03:00") if art.published_at else ""
        items.append(f"""  <url>
    <loc>{site_url}/haber/{art.slug}</loc>
    <news:news>
      <news:publication>
        <news:name>{settings.SITE_NAME}</news:name>
        <news:language>tr</news:language>
      </news:publication>
      <news:publication_date>{pub}</news:publication_date>
      <news:title><![CDATA[{art.title}]]></news:title>
    </news:news>
  </url>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
{chr(10).join(items) if items else '  <!-- Henüz haber yok -->'}
</urlset>"""
    return Response(content=xml, media_type="application/xml")


# ─── ADMIN FRONTEND ──────────────────────────────────────────────────────────

@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin giriş sayfası."""
    return templates.TemplateResponse("admin/login.html", {
        "request": request,
        "site_name": settings.SITE_NAME,
        "error": None,
    })


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Admin dashboard."""
    if not current_user or not current_user.is_admin:
        return RedirectResponse("/admin/login", status_code=302)

    # İstatistikler
    total_articles = (await db.execute(select(func.count(Article.id)))).scalar() or 0
    published_articles = (await db.execute(
        select(func.count(Article.id)).where(Article.status == ArticleStatus.PUBLISHED.value)
    )).scalar() or 0
    pending_articles = (await db.execute(
        select(func.count(Article.id)).where(Article.status == ArticleStatus.PENDING_REVIEW.value)
    )).scalar() or 0
    total_categories = (await db.execute(select(func.count(Category.id)))).scalar() or 0

    # Son haberler
    recent_r = await db.execute(
        select(Article).order_by(desc(Article.created_at)).limit(15)
    )
    recent_articles = recent_r.scalars().all()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "site_name": settings.SITE_NAME,
        "active_page": "dashboard",
        "current_user": current_user,
        "stats": {
            "total_articles": total_articles,
            "published_articles": published_articles,
            "pending_articles": pending_articles,
            "total_categories": total_categories,
        },
        "recent_articles": recent_articles,
    })


@router.get("/admin/articles", response_class=HTMLResponse)
async def admin_articles_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    status: Optional[str] = None,
    sayfa: int = Query(1, alias="sayfa", ge=1),
    q: Optional[str] = None,
):
    """Admin haber listesi."""
    if not current_user or not current_user.is_admin:
        return RedirectResponse("/admin/login", status_code=302)

    per_page = 30
    query = select(Article)
    if status:
        query = query.where(Article.status == status)
    if q:
        search = f"%{q}%"
        query = query.where(or_(Article.title.ilike(search), Article.excerpt.ilike(search)))

    total_r = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_r.scalar() or 0

    offset = (sayfa - 1) * per_page
    art_r = await db.execute(query.order_by(desc(Article.created_at)).offset(offset).limit(per_page))
    articles = art_r.scalars().all()

    return templates.TemplateResponse("admin/articles.html", {
        "request": request,
        "site_name": settings.SITE_NAME,
        "active_page": "articles",
        "current_user": current_user,
        "articles": articles,
        "total": total,
        "page": sayfa,
        "pages": max(1, (total + per_page - 1) // per_page),
        "filter_status": status,
        "search_q": q,
    })


@router.get("/admin/articles/new", response_class=HTMLResponse)
async def admin_article_new(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Yeni haber oluşturma formu."""
    if not current_user or not current_user.is_admin:
        return RedirectResponse("/admin/login", status_code=302)

    cat_r = await db.execute(select(Category).where(Category.is_active == True).order_by(Category.parent_id, Category.order))
    categories = cat_r.scalars().all()

    return templates.TemplateResponse("admin/article_form.html", {
        "request": request,
        "site_name": settings.SITE_NAME,
        "active_page": "article-new",
        "current_user": current_user,
        "article": None,
        "categories": categories,
    })


@router.get("/admin/articles/{article_id}/edit", response_class=HTMLResponse)
async def admin_article_edit(
    article_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Haber düzenleme formu."""
    if not current_user or not current_user.is_admin:
        return RedirectResponse("/admin/login", status_code=302)

    art_r = await db.execute(select(Article).where(Article.id == article_id))
    article = art_r.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404)

    cat_r = await db.execute(select(Category).where(Category.is_active == True).order_by(Category.parent_id, Category.order))
    categories = cat_r.scalars().all()

    return templates.TemplateResponse("admin/article_form.html", {
        "request": request,
        "site_name": settings.SITE_NAME,
        "active_page": "articles",
        "current_user": current_user,
        "article": article,
        "categories": categories,
    })


@router.get("/admin/sources", response_class=HTMLResponse)
async def admin_sources(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """RSS kaynakları sayfası."""
    if not current_user or not current_user.is_admin:
        return RedirectResponse("/admin/login", status_code=302)

    src_r = await db.execute(select(Source).order_by(Source.name))
    sources = src_r.scalars().all()

    return templates.TemplateResponse("admin/sources.html", {
        "request": request,
        "site_name": settings.SITE_NAME,
        "active_page": "sources",
        "current_user": current_user,
        "sources": sources,
    })


@router.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Kategoriler sayfası."""
    if not current_user or not current_user.is_admin:
        return RedirectResponse("/admin/login", status_code=302)

    cat_r = await db.execute(select(Category).order_by(Category.parent_id, Category.order))
    categories = cat_r.scalars().all()

    return templates.TemplateResponse("admin/categories.html", {
        "request": request,
        "site_name": settings.SITE_NAME,
        "active_page": "categories",
        "current_user": current_user,
        "categories": categories,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# OKUR (USER) KİMLİK DOĞRULAMA & YORUM İŞLEMLERİ
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/kayit-ol", response_class=HTMLResponse)
async def register_page(request: Request, db: AsyncSession = Depends(get_db)):
    context = await get_base_context(db, request)
    context["active_category"] = "kayit"
    return templates.TemplateResponse("register.html", context)

@router.post("/kayit-ol", response_class=HTMLResponse)
async def register_post(
    request: Request,
    full_name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    context = await get_base_context(db, request)
    context["active_category"] = "kayit"

    # Kontrol
    existing = await db.execute(select(User).where(or_(User.username == username, User.email == email)))
    if existing.scalars().first():
        context["error"] = "Bu kullanıcı adı veya e-posta zaten kullanımda."
        return templates.TemplateResponse("register.html", context)

    new_user = User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        is_admin=False
    )
    db.add(new_user)
    await db.commit()

    return RedirectResponse(url="/giris-yap?success=kayit", status_code=302)

@router.get("/giris-yap", response_class=HTMLResponse)
async def login_page(request: Request, db: AsyncSession = Depends(get_db), success: str = None):
    context = await get_base_context(db, request)
    context["active_category"] = "giris"
    if success == "kayit":
        context["success"] = "Kayıt başarılı! Lütfen giriş yapın."
    return templates.TemplateResponse("login.html", context)

@router.post("/giris-yap", response_class=HTMLResponse)
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(db, username, password)
    if not user:
        context = await get_base_context(db, request)
        context["active_category"] = "giris"
        context["error"] = "Hatalı kullanıcı adı veya şifre."
        return templates.TemplateResponse("login.html", context)

    # Token oluştur
    access_token = create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response

@router.get("/cikis-yap")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response

@router.post("/api/comments")
async def add_comment(
    request: Request,
    article_id: int = Form(...),
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/giris-yap", status_code=302)
    
    new_comment = Comment(
        content=content,
        article_id=article_id,
        user_id=current_user.id,
        status="published"
    )
    db.add(new_comment)
    await db.commit()
    
    article_res = await db.execute(select(Article).where(Article.id == article_id))
    article = article_res.scalars().first()
    if article:
        return RedirectResponse(url=f"/haber/{article.slug}", status_code=302)
    return RedirectResponse(url="/", status_code=302)


@router.get("/api/stream/notifications")
async def stream_notifications(request: Request):
    """Kullanıcıya yeni haberleri SSE üzerinden bildir."""
    async def notification_generator():
        last_checked = datetime.now(timezone.utc)
        while True:
            # Kullanıcı bağlantıyı kapatmışsa döngüden çık
            if await request.is_disconnected():
                break
            
            await asyncio.sleep(30) # Her 30 saniyede bir kontrol et
            
            try:
                async with AsyncSessionLocal() as db:
                    new_articles = await db.execute(
                        select(Article)
                        .where(Article.status == "published", Article.published_at > last_checked)
                        .order_by(desc(Article.published_at))
                    )
                    articles = new_articles.scalars().all()
                    if articles:
                        for article in articles:
                            data = json.dumps({"title": article.title, "url": f"/haber/{article.slug}"})
                            yield f"data: {data}\n\n"
                        last_checked = datetime.now(timezone.utc)
                    else:
                        # Bağlantıyı canlı tutmak için ping gönder
                        yield ": ping\n\n"
            except Exception as e:
                logger.error(f"SSE Error: {e}")
                break

    return StreamingResponse(notification_generator(), media_type="text/event-stream")
