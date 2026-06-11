"""
Grayn AEO — FastAPI Main Application Entrypoint

Configures FastAPI app settings, CORS middleware, global exception handlers,
and registers both /v1 public and /internal admin API routers.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.config import get_settings
from app.routers import v1, internal
from app.mcp_server import router as mcp_router
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def scheduled_tracking():
    """Weekly automated tracking run for all active workspaces."""
    try:
        from app.database import get_supabase
        from app.services.tracking import trigger_batch_run
        from app.models.schemas import EngineType
        
        logger.info("Starting scheduled weekly AEO tracking batch.")
        db = get_supabase()
        workspaces = db.table("workspaces").select("*").execute().data
        
        for ws in workspaces:
            prompts = db.table("aeo_prompts").select("id").eq("workspace_id", ws["id"]).eq("is_active", True).execute().data
            prompt_ids = [p["id"] for p in prompts]
            if not prompt_ids:
                continue
                
            engines = [EngineType.OPENAI, EngineType.GOOGLE_AI, EngineType.PERPLEXITY]
            for eng in engines:
                await trigger_batch_run(db, ws, eng, prompt_ids)
                
    except Exception as e:
        logger.error(f"Scheduled tracking failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(scheduled_tracking, 'cron', day_of_week='mon', hour=2, minute=0)
    scheduler.start()
    yield
    scheduler.shutdown()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app.main")

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Register CORS Middleware (CORS-01)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handlers ─────────────────────────────────────


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors elegantly."""
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle any uncaught backend exceptions gracefully."""
    logger.exception("Uncaught exception on %s: %s", request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error occurred. Please try again later."},
    )


# ── Register Routers ──────────────────────────────────────────────

app.include_router(v1.router)
app.include_router(internal.router)
app.include_router(mcp_router)


@app.get("/")
def read_root():
    """Root endpoint for pinging and basic system details."""
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.API_VERSION,
        "status": "online",
        "documentation": "/docs" if settings.DEBUG else "disabled in production",
    }
