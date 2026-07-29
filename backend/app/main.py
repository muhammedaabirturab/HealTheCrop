import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.admin_seed import seed_admin_account
from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.core.storage import storage_service

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_admin_account(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered smart agriculture platform: IoT soil monitoring, "
                 "crop recommendation, and pest/disease detection for farmers.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    # Vite picks the next free port (5174, 5175, ...) whenever 5173 is already in use,
    # which would otherwise silently fail CORS preflight and look like a "backend error"
    # with no useful message. This regex only ever matches loopback addresses, so it's
    # safe to leave on in production too — real deployments still require the exact
    # origin to be listed in CORS_ORIGINS.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


app.include_router(api_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "storage_backend": storage_service.status,
    }


@app.get("/")
def root():
    return {"message": "HealTheCrop API — see /docs for interactive API documentation."}
