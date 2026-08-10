from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.storage import storage_service
from app.cv.disease_service import SUPPORTED_LANGUAGES, get_disease_service
from app.models.pest_detection import PestDetection
from app.models.user import User
from app.schemas.pest import PestDetectionResponse

router = APIRouter(prefix="/pest", tags=["Pest & Disease Detection"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


@router.post("/scan", response_model=PestDetectionResponse)
async def scan_crop_image(
    file: UploadFile = File(...),
    lang: str = Query("en", description="UI language code — determines which language the diagnosis text is returned in"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Upload a JPEG, PNG, or WEBP image")
    lang = lang if lang in SUPPORTED_LANGUAGES else "en"

    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Image exceeds 10MB limit")

    service = get_disease_service()
    try:
        result = service.detect(image_bytes, lang=lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not result["image_quality"]["is_acceptable"]:
        return PestDetectionResponse(
            model_used=result["model_used"],
            detections=[],
            severity=result["severity"],
            image_quality=result["image_quality"],
            is_uncertain=result["is_uncertain"],
            uncertainty_note=result["uncertainty_note"],
        )

    filename = file.filename or ""
    extension = "." + filename.rsplit(".", 1)[-1] if "." in filename else ".jpg"
    image_key = storage_service.upload_bytes("healthecrop-images", image_bytes, extension)

    top_confidence = result["detections"][0]["confidence"] if result["detections"] else None
    record = PestDetection(
        user_id=user.id,
        image_key=image_key,
        detections=result["detections"],
        model_used=result["model_used"],
        top_confidence=top_confidence,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return PestDetectionResponse(
        id=record.id,
        model_used=result["model_used"],
        detections=result["detections"],
        severity=result["severity"],
        image_quality=result["image_quality"],
        is_uncertain=result["is_uncertain"],
        uncertainty_note=result["uncertainty_note"],
        created_at=record.created_at,
    )
