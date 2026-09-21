import sys, asyncio
sys.path.insert(0, '.')
from app.database.database import AsyncSessionLocal
from sqlalchemy import select, func, text
from app.database.models import Article, ArticleStatus

async def main():
    async with AsyncSessionLocal() as db:
        print("=== ARTICLES WITH MISSING FEATURED_IMAGE (Published) ===")
        r = await db.execute(select(Article.id, Article.title, Article.featured_image, Article.image_source, Article.image_status).where(
            Article.status == ArticleStatus.PUBLISHED.value,
            (Article.featured_image == None) | (Article.featured_image == '') | (Article.featured_image == 'None')
        ))
        for row in r.all():
            print(f"  [{row.id}] img={row.featured_image!r} src={row.image_source} status={row.image_status} | {row.title[:60]}")

        print("\n=== EXCERPT HTML TAG STATS ===")
        r2 = await db.execute(select(func.count(Article.id)).where(
            Article.status == ArticleStatus.PUBLISHED.value,
            Article.excerpt.like('%<%')
        ))
        print(f"  Excerpts with raw HTML: {r2.scalar()}")

        print("\n=== ARTICLE SLUG SAMPLE (to find actual articles) ===")
        r3 = await db.execute(select(Article.id, Article.slug, Article.title).where(
            Article.status == ArticleStatus.PUBLISHED.value
        ).order_by(Article.id.desc()).limit(5))
        for row in r3.all():
            print(f"  [{row.id}] /haber/{row.slug}")

asyncio.run(main())
