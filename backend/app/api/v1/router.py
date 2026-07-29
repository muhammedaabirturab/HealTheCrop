from fastapi import APIRouter

from app.api.v1 import admin, auth, localization, pest, predictions, reports, sensors

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(sensors.router)
api_router.include_router(predictions.router)
api_router.include_router(pest.router)
api_router.include_router(reports.router)
api_router.include_router(localization.router)
