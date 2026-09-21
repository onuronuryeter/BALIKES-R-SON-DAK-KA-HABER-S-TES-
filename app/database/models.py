# ===================================
# BALIKESİR SON DAKİKA HABER
# app/database/models.py
# SQLAlchemy ORM Modelleri
# ===================================

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Enum, Index, Float, BigInteger
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from datetime import datetime, timezone

from app.database.database import Base


# ─── Enum Tanımları ─────────────────────────────────────────────────────────────

class ArticleStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PENDING_IMAGE = "pending_image"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SourceType(str, enum.Enum):
    RSS = "rss"
    MANUAL = "manual"
    API = "api"
    SCRAPER = "scraper"


class AIProvider(str, enum.Enum):
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    NONE = "none"


# ─── Yardımcı Fonksiyon ─────────────────────────────────────────────────────────

def utc_now():
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# KULLANICI MODELİ
# ═══════════════════════════════════════════════════════════════════════════════

class User(Base):
    """
    Admin ve editör kullanıcı hesapları.
    Şifreler bcrypt ile hash'lenir, asla düz metin saklanmaz.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_superadmin = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # İlişkiler
    articles = relationship("Article", back_populates="author_user", foreign_keys="Article.author_id")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username!r})>"


# ═══════════════════════════════════════════════════════════════════════════════
# YAZAR MODELİ
# ═══════════════════════════════════════════════════════════════════════════════

class Author(Base):
    """
    Haber yazarları. Hem sistem kullanıcıları hem de dış kaynakların
    yazarları bu tabloda tutulur.
    """
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    bio = Column(Text, nullable=True)
    email = Column(String(255), nullable=True)
    avatar = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # İlişkiler
    user = relationship("User", foreign_keys=[user_id])
    articles = relationship("Article", back_populates="article_author", foreign_keys="Article.article_author_id")

    def __repr__(self):
        return f"<Author(id={self.id}, name={self.name!r})>"


# ═══════════════════════════════════════════════════════════════════════════════
# KATEGORİ MODELİ
# ═══════════════════════════════════════════════════════════════════════════════

class Category(Base):
    """
    Haber kategorileri. Hiyerarşik yapı desteklenir (parent_id).
    Veritabanından yönetilebilir.
    """
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    color = Column(String(7), default="#e63946", nullable=True)  # Hex renk kodu
    icon = Column(String(50), nullable=True)  # Icon class adı
    order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    show_in_nav = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # SEO
    seo_title = Column(String(70), nullable=True)
    seo_description = Column(String(160), nullable=True)

    # İlişkiler
    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent")
    articles = relationship("Article", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name!r})>"


# ═══════════════════════════════════════════════════════════════════════════════
# ETİKET MODELİ
# ═══════════════════════════════════════════════════════════════════════════════

class Tag(Base):
    """Haber etiketleri."""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # İlişkiler
    articles = relationship("ArticleTag", back_populates="tag")

    def __repr__(self):
        return f"<Tag(id={self.id}, name={self.name!r})>"


# ═══════════════════════════════════════════════════════════════════════════════
# KAYNAK MODELİ (RSS / Haber Kaynakları)
# ═══════════════════════════════════════════════════════════════════════════════

class Source(Base):
    """
    Haber kaynakları. RSS feed'ler ve diğer kaynaklar.
    Admin panelinden yönetilebilir.
    """
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(2048), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(20), default=SourceType.RSS.value, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    last_article_count = Column(Integer, default=0, nullable=False)
    total_fetched = Column(Integer, default=0, nullable=False)
    total_imported = Column(Integer, default=0, nullable=False)
    fetch_interval_minutes = Column(Integer, default=15, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # İlişkiler
    category = relationship("Category", foreign_keys=[category_id])
    articles = relationship("Article", back_populates="source")

    def __repr__(self):
        return f"<Source(id={self.id}, name={self.name!r})>"


# ═══════════════════════════════════════════════════════════════════════════════
# MEDYA MODELİ
# ═══════════════════════════════════════════════════════════════════════════════

class Media(Base):
    """
    Yüklenen görseller ve medya dosyaları.
    İleride S3 veya başka object storage'a geçilebilecek şekilde tasarlandı.
    """
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=True)
    file_path = Column(String(1000), nullable=False)
    url = Column(String(2048), nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(BigInteger, default=0, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    alt_text = Column(String(500), nullable=True)
    caption = Column(Text, nullable=True)
    storage_provider = Column(String(20), default="local", nullable=False)  # local, s3, gcs
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="SET NULL"), nullable=True)
    is_cover = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # İlişkiler
    uploader = relationship("User", foreign_keys=[uploaded_by])
    article = relationship("Article", foreign_keys=[article_id])

    def __repr__(self):
        return f"<Media(id={self.id}, filename={self.filename!r}, article_id={self.article_id})>"


# ═══════════════════════════════════════════════════════════════════════════════
# HABER MODELİ
# ═══════════════════════════════════════════════════════════════════════════════

class Article(Base):
    """
    Ana haber modeli. Tüm haber içerikleri burada saklanır.
    """
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)

    # ─── Temel Bilgiler ─────────────────────────────────────────────────────────
    title = Column(String(500), nullable=False)
    original_title = Column(String(500), nullable=True)
    slug = Column(String(600), unique=True, nullable=False, index=True)
    excerpt = Column(Text, nullable=True)            # Spot / özet / summary
    content = Column(Text, nullable=True)            # Tam içerik

    # ─── İlişkiler ─────────────────────────────────────────────────────────────
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    article_author_id = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"), nullable=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)

    # ─── Kaynak Bilgisi ─────────────────────────────────────────────────────────
    source_url = Column(String(2048), nullable=True)  # Kaynak site URL'i
    source_name = Column(String(200), nullable=True)  # Kaynak adı (cache)
    original_url = Column(String(2048), nullable=True, index=True)  # Haber orijinal URL'i

    # ─── Görseller ─────────────────────────────────────────────────────────────
    featured_image = Column(String(2048), nullable=True)  # URL veya dosya yolu
    featured_image_alt = Column(String(500), nullable=True)
    featured_image_caption = Column(Text, nullable=True)
    image_source_url = Column(String(2048), nullable=True)  # Görsel kaynak url'i
    image_license = Column(String(100), default='unknown', nullable=True)  # Görsel lisans/telif bilgisi
    image_source = Column(String(20), default='rss', nullable=True)  # rss, og_image, placeholder
    image_status = Column(String(20), default='available', nullable=True)  # available, blocked, missing, invalid

    # ─── Durum & Özellikler ─────────────────────────────────────────────────────
    status = Column(
        String(20),
        default=ArticleStatus.DRAFT.value,
        nullable=False,
        index=True
    )
    is_published = Column(Boolean, default=False, nullable=False, index=True)
    is_breaking = Column(Boolean, default=False, nullable=False, index=True)
    is_featured = Column(Boolean, default=False, nullable=False, index=True)
    is_ai_generated = Column(Boolean, default=False, nullable=False)
    is_duplicate_suspect = Column(Boolean, default=False, nullable=False, index=True)

    # ─── AI (Yapay Zeka) ────────────────────────────────────────────────────────
    ai_processed = Column(Boolean, default=False, nullable=False)
    ai_model = Column(String(100), nullable=True)
    ai_processed_at = Column(DateTime(timezone=True), nullable=True)
    ai_error = Column(Text, nullable=True)
    ai_source_count = Column(Integer, default=1, nullable=False)
    ai_enrichment_status = Column(String(50), default='not_needed', nullable=True)

    # ─── Tarihler ───────────────────────────────────────────────────────────────
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    imported_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # ─── SEO ────────────────────────────────────────────────────────────────────
    meta_title = Column(String(70), nullable=True)
    meta_description = Column(String(160), nullable=True)
    canonical_url = Column(String(2048), nullable=True)
    keywords = Column(String(200), nullable=True)

    # ─── İstatistikler ──────────────────────────────────────────────────────────
    view_count = Column(Integer, default=0, nullable=False)
    share_count = Column(Integer, default=0, nullable=False)

    # ─── Duplicate Detection ────────────────────────────────────────────────────
    content_hash = Column(String(64), nullable=True, index=True)  # SHA256
    title_normalized = Column(String(600), nullable=True, index=True)  # Normalize başlık

    # ─── SQLAlchemy İlişkileri ──────────────────────────────────────────────────
    category = relationship("Category", back_populates="articles")
    author_user = relationship("User", back_populates="articles", foreign_keys=[author_id])
    article_author = relationship("Author", back_populates="articles", foreign_keys=[article_author_id])
    source = relationship("Source", back_populates="articles")
    tags = relationship("ArticleTag", back_populates="article", cascade="all, delete-orphan")
    revisions = relationship("ArticleRevision", back_populates="article", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="article", cascade="all, delete-orphan")

    # ─── İndeksler ──────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_articles_status_published", "status", "published_at"),
        Index("ix_articles_category_status", "category_id", "status"),
        Index("ix_articles_breaking", "is_breaking", "status"),
        Index("ix_articles_featured", "is_featured", "status"),
    )

    def __repr__(self):
        return f"<Article(id={self.id}, title={self.title[:50]!r}, status={self.status!r})>"


# ═══════════════════════════════════════════════════════════════════════════════
# HABER-ETİKET İLİŞKİ TABLOSU
# ═══════════════════════════════════════════════════════════════════════════════

class ArticleTag(Base):
    """Haber-Etiket çoka-çok ilişki tablosu."""
    __tablename__ = "article_tags"

    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # İlişkiler
    article = relationship("Article", back_populates="tags")
    tag = relationship("Tag", back_populates="articles")


# ═══════════════════════════════════════════════════════════════════════════════
# HABER REVİZYON MODELİ
# ═══════════════════════════════════════════════════════════════════════════════

class ArticleRevision(Base):
    """
    Haber revizyon geçmişi. Her düzenleme burada saklanır.
    Eski sürümlere geri dönme imkânı sağlar.
    """
    __tablename__ = "article_revisions"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    excerpt = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    revised_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    revision_note = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # İlişkiler
    article = relationship("Article", back_populates="revisions")
    reviser = relationship("User", foreign_keys=[revised_by])

    def __repr__(self):
        return f"<ArticleRevision(id={self.id}, article_id={self.article_id})>"


# ═══════════════════════════════════════════════════════════════════════════════
# SİTE AYARLARI MODELİ
# ═══════════════════════════════════════════════════════════════════════════════

class SiteSetting(Base):
    """
    Site ayarları key-value mağazası.
    Admin panelinden değiştirilebilir.
    """
    __tablename__ = "site_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    label = Column(String(200), nullable=True)       # Kullanıcı dostu etiket
    description = Column(Text, nullable=True)        # Ayarın açıklaması
    setting_type = Column(String(20), default="text", nullable=False)  # text, bool, json, image
    is_public = Column(Boolean, default=False, nullable=False)  # Frontend'de görünür mü?
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    def __repr__(self):
        return f"<SiteSetting(key={self.key!r}, value={str(self.value)[:30]!r})>"


# ═══════════════════════════════════════════════════════════════════════════════
# YORUM MODELİ
# ═══════════════════════════════════════════════════════════════════════════════

class Comment(Base):
    """
    Haber yorumları.
    """
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="published", nullable=False, index=True) # published, pending, spam
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # İlişkiler
    article = relationship("Article", back_populates="comments")
    user = relationship("User", back_populates="comments")

    def __repr__(self):
        return f"<Comment(id={self.id}, article_id={self.article_id}, user_id={self.user_id})>"
