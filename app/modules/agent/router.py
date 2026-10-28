import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, DiseaseReport
from app.modules.auth.router import get_current_user
from app.modules.farm import service as farm_service
from app.modules.agent import schemas
from app.modules.agent.image_validator import validate_and_decode_image
from app.modules.agent.engine import agent_engine

logger = logging.getLogger("agrimind.agent.router")

router = APIRouter(prefix="/api/v1/agent", tags=["Agent & Diagnosis"])

@router.post("/chat", response_model=schemas.ChatResponse)
def agent_chat(
    request: schemas.ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    JWT Protected AI Agronomist chat endpoint.
    Routes queries dynamically across Disease Diagnosis, Irrigation, Fertilizer, Weather, Market, and Knowledge RAG.
    """
    crop_context_str = ""
    farm_location_str = "Mandya, India"
    soil_type_str = "Loam"

    # 1. Validate Farm & Crop Ownership Authorization
    if request.farm_id:
        farm = farm_service.get_farm_by_id(db, farm_id=request.farm_id, owner_id=current_user.id)
        if not farm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: specified farm profile does not belong to user."
            )
        crop_context_str += f"Farm: {farm.name} ({farm.soil_type} soil). "
        farm_location_str = farm.location
        soil_type_str = farm.soil_type

    if request.crop_id:
        if not request.farm_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="farm_id must be provided when crop_id is specified."
            )
        crops = farm_service.get_crops_by_farm(db, farm_id=request.farm_id)
        crop_match = next((c for c in crops if c.id == request.crop_id), None)
        if not crop_match:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: specified crop record does not belong to specified farm."
            )
        crop_context_str += f"Crop: {crop_match.name} ({crop_match.variety or 'Standard'}). "

    # 2. Image Decoding & Pillow Validation
    image_bytes: Optional[bytes] = None
    if request.image_b64:
        try:
            image_bytes = validate_and_decode_image(request.image_b64)
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image validation failed: {str(ve)}"
            )

    # 3. Process Request with Agent Engine
    try:
        reply, tool_used, assessment, irrigation, fertilizer, weather, market, knowledge = agent_engine.process_request(
            request=request,
            image_bytes=image_bytes,
            mime_type="image/jpeg",
            crop_context=crop_context_str,
            farm_location=farm_location_str,
            soil_type=soil_type_str
        )
    except RuntimeError as re:
        logger.error(f"Agent engine service error: {str(re)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Crop disease diagnosis service is temporarily unavailable. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error during chat processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while processing your request."
        )

    # 4. Database Persistence of Disease Report if disease tool ran
    report_id: Optional[str] = None
    if assessment:
        db_report = DiseaseReport(
            user_id=current_user.id,
            farm_id=request.farm_id,
            crop_id=request.crop_id,
            image_reference=f"reports/img_{current_user.id[:8]}.jpg" if request.image_b64 else None,
            possible_condition=assessment.possible_condition,
            assessment_level=assessment.assessment_level,
            observations=json.dumps(assessment.observations),
            symptoms=json.dumps(assessment.symptoms),
            cause=assessment.cause,
            treatment=json.dumps(assessment.treatment),
            prevention=json.dumps(assessment.prevention),
            disclaimer=assessment.disclaimer,
            is_mock=assessment.is_mock
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        report_id = db_report.id

    return schemas.ChatResponse(
        reply=reply,
        tool_used=tool_used,
        assessment=assessment,
        irrigation=irrigation,
        fertilizer=fertilizer,
        weather=weather,
        market=market,
        knowledge=knowledge,
        report_id=report_id
    )

@router.get("/reports", response_model=List[schemas.DiseaseReportResponse])
def get_user_disease_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns historical disease reports for the authenticated user.
    """
    reports = db.query(DiseaseReport).filter(DiseaseReport.user_id == current_user.id).order_by(DiseaseReport.created_at.desc()).all()
    
    result = []
    for r in reports:
        result.append(schemas.DiseaseReportResponse(
            id=r.id,
            farm_id=r.farm_id,
            crop_id=r.crop_id,
            image_reference=r.image_reference,
            possible_condition=r.possible_condition,
            assessment_level=r.assessment_level,
            observations=json.loads(r.observations) if r.observations else [],
            symptoms=json.loads(r.symptoms) if r.symptoms else [],
            cause=r.cause,
            treatment=json.loads(r.treatment) if r.treatment else [],
            prevention=json.loads(r.prevention) if r.prevention else [],
            disclaimer=r.disclaimer,
            is_mock=r.is_mock,
            created_at=r.created_at
        ))
    return result
