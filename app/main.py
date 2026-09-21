# ===================================
# BALIKESİR SON DAKİKA HABER
# app/main.py — FastAPI Ana Uygulama
# ===================================

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from app.config.settings import settings
from app.database.database import init_db
import socket

# ─── Scheduler Lock (Single Instance) ──────────
_scheduler_lock_socket = None

def acquire_scheduler_lock() -> bool:
    """Socket port binding ile process-level singleton kilit oluşturur."""
    global _scheduler_lock_socket
    try:
        _scheduler_lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _scheduler_lock_socket.bind(("127.0.0.1", 49152)) # Rastgele yüksek port
        return True
    except OSError:
        return False

# ─── Logger ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Dizin Kontrolleri ──────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent


def ensure_directories():
    for d in [BASE_DIR / "data", BASE_DIR / "data" / "media", BASE_DIR / "logs"]:
        d.mkdir(parents=True, exist_ok=True)


# ─── Lifespan ───────────────────────────────────────────────────────────────────

from app.services.scheduler_service import start_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"  {settings.SITE_NAME} baslatiliyor...")
    logger.info(f"  Ortam : {settings.APP_ENV}")
    logger.info(f"  URL   : {settings.SITE_URL}")
    logger.info("=" * 60)
    ensure_directories()
    await init_db()
    
    # Scheduler'ı başlat (Yalnızca tek process kilit alabildiyse)
    is_scheduler_running = False
    if acquire_scheduler_lock():
        start_scheduler()
        is_scheduler_running = True
    else:
        logger.info("[SCHEDULER] Baska bir process tarafindan calistiriliyor (Reload/Multi-worker korumasi).")
    
    logger.info("Uygulama hazir.")
    yield
    
    # Scheduler'ı durdur
    if is_scheduler_running:
        shutdown_scheduler()
        if _scheduler_lock_socket:
            _scheduler_lock_socket.close()
            
    logger.info("Uygulama kapatiliyor...")


# ─── FastAPI App ────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.SITE_NAME,
    description="Balıkesir ve ilçelerinden son dakika haberleri",
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ─── CORS ───────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# ─── Static Files ───────────────────────────────────────────────────────────────

static_dir = BASE_DIR / "app" / "static"
media_dir = BASE_DIR / "data" / "media"
static_dir.mkdir(parents=True, exist_ok=True)
media_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

# ─── Templates ──────────────────────────────────────────────────────────────────

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

# ─── API Router'ları ────────────────────────────────────────────────────────────

from app.api import auth, articles, categories, sources, market  # noqa: E402

app.include_router(auth.router,       prefix="/api/auth",       tags=["auth"])
app.include_router(articles.router,   prefix="/api/articles",   tags=["articles"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(sources.router,    prefix="/api/sources",    tags=["sources"])
app.include_router(market.router,     prefix="/api/market",     tags=["market"])

# ─── Frontend Router ─────────────────────────────────────────────────────────────

from app.frontend import router as frontend_router  # noqa: E402
app.include_router(frontend_router)

# ─── System Endpoints ────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health_check():
    """GET /health → {"status": "ok", "scheduler": "running"}"""
    from app.services.scheduler_service import scheduler
    sch_status = "running" if scheduler.running else "stopped"
    return {"status": "ok", "app": settings.SITE_NAME, "version": settings.APP_VERSION, "scheduler": sch_status}


# ─── Hata Yöneticileri ──────────────────────────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"error": "Bulunamadı"})
    try:
        return templates.TemplateResponse(
            "404.html", {"request": request, "site_name": settings.SITE_NAME}, status_code=404
        )
    except Exception:
        return JSONResponse(status_code=404, content={"error": "Sayfa bulunamadı"})


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error(f"Sunucu hatası: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Sunucu hatası", "detail": str(exc)})
