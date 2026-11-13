import io
import json
import base64
import logging
import requests
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, DiseaseReport
from app.modules.auth.router import get_current_user
from app.modules.farm import service as farm_service
from app.modules.agent import schemas, nlu
from app.modules.agent.image_validator import validate_and_decode_image
from app.modules.agent.engine import agent_engine
from app.modules.agent.voice_service import GnaniVoiceService
from app.modules.agent.tools.weather import get_weather_forecast
from app.modules.agent.tools.irrigation import calculate_irrigation_schedule
from app.modules.agent.tools.fertilizer import get_fertilizer_recommendation
from app.modules.agent.tools.market import get_market_prices
from app.modules.agent.tools.knowledge import search_crop_knowledge

logger = logging.getLogger("agrimind.agent.router")

router = APIRouter(prefix="/api/v1/agent", tags=["Agent, Diagnosis & Voice"])

# -----------------------------------------------------------------------------
# 1. Voice Interaction Endpoints (Gnani AI Prisma & Timbre)
# -----------------------------------------------------------------------------

@router.post("/voice/transcribe", response_model=schemas.VoiceTranscribeResponse)
async def transcribe_voice_audio(
    file: UploadFile = File(...),
    language: str = Form("te")
):
    """
    Transcribes farmer speech audio using official Gnani Prisma STT (v3.0).
    Preprocesses and standardizes audio to 16kHz mono 16-bit PCM WAV.
    Supports Telugu ('te'), Hindi ('hi'), English ('en'), and auto-detection ('auto').
    Provides transparent development mock mode when GNANI_API_KEY is not configured.
    """
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

        result = GnaniVoiceService.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=file.filename or "speech.webm",
            content_type=file.content_type or "audio/webm",
            language=language
        )
        return schemas.VoiceTranscribeResponse(**result)
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Voice audio validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.error(f"Voice transcription authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except (TimeoutError, requests.exceptions.Timeout) as e:
        logger.error(f"Voice transcription timeout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Gnani Speech-to-Text timeout: {str(e)}"
        )
    except (ConnectionError, requests.exceptions.ConnectionError) as e:
        logger.error(f"Voice transcription connection error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gnani Speech-to-Text connection error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Voice transcription error: {str(e)}", exc_info=True)
        err_msg = str(e)
        err_lower = err_msg.lower()
        if "authentication failed" in err_lower or "invalid_api_key" in err_lower:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Gnani Speech-to-Text authentication error: {err_msg}"
            )
        elif "rate limit" in err_lower or "rate_limited" in err_lower or "429" in err_lower:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Gnani Speech-to-Text rate limited: {err_msg}"
            )
        elif "timed out" in err_lower or "timeout" in err_lower:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Gnani Speech-to-Text timeout: {err_msg}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gnani Speech-to-Text service error: {err_msg}"
            )

@router.post("/voice/synthesize")
def synthesize_voice_speech(
    request: schemas.VoiceSynthesizeRequest
):
    """
    Synthesizes speech audio from text using official Gnani Timbre TTS (v3.0).
    Returns audio stream (.wav or .mp3).
    """
    try:
        audio_bytes, content_type, is_mock, provider = GnaniVoiceService.synthesize_speech(
            text=request.text,
            language=request.language,
            speed=request.speed,
            voice=request.voice,
            container=request.container
        )
        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "X-Audio-Provider": provider,
                "X-Audio-Mock": str(is_mock)
            }
        )
    except ValueError as e:
        logger.warning(f"Voice synthesis validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Voice synthesis error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gnani Text-to-Speech service error: {str(e)}"
        )

# -----------------------------------------------------------------------------
# 2. Main Agent Orchestrator Chat Endpoint
# -----------------------------------------------------------------------------

@router.post("/chat", response_model=schemas.ChatResponse)
def agent_chat(
    request: schemas.ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    JWT Protected AI Agronomist chat endpoint.
    Routes queries dynamically across Disease Diagnosis, Irrigation, Fertilizer, Weather, Market, and Knowledge RAG.
    Supports regional response languages (Telugu, Hindi, English).
    """
    crop_context_str = ""
    farm_location_str = "Mandya, India"
    soil_type_str = "Loam"
    field_area_acres = 1.0

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
        field_area_acres = farm.area_acres or 1.0

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

    # 3. Pull farm context for farm_management_tool
    user_farms = farm_service.get_farms_by_owner(db, owner_id=current_user.id)
    farm_data = {
        "farms": [{"name": f.name, "location": f.location, "acres": f.area_acres, "soil": f.soil_type} for f in user_farms]
    }

    # 4. Process Request with Agent Engine
    try:
        reply, tool_used, assessment, irrigation, fertilizer, weather, market, knowledge = agent_engine.process_request(
            request=request,
            image_bytes=image_bytes,
            mime_type="image/jpeg",
            crop_context=crop_context_str,
            farm_location=farm_location_str,
            soil_type=soil_type_str,
            field_area=field_area_acres,
            farm_data=farm_data
        )
    except RuntimeError as re:
        logger.error(f"Agent engine service error: {str(re)}")
        err_detail = (
            "Crop disease diagnosis service is temporarily unavailable. Please try again later."
            if image_bytes
            else "Agricultural AI service encountered a temporary error. Please try again shortly."
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=err_detail
        )
    except Exception as e:
        logger.error(f"Unexpected error during chat processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while processing your request."
        )

    # 5. Database Persistence of Disease Report if disease diagnosis ran
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

    _, detected_lang = nlu.detect_language_and_style(request.message, request.language)

    return schemas.ChatResponse(
        reply=reply,
        tool_used=tool_used,
        detected_language=detected_lang,
        assessment=assessment,
        irrigation=irrigation,
        fertilizer=fertilizer,
        weather=weather,
        market=market,
        knowledge=knowledge,
        report_id=report_id
    )

# -----------------------------------------------------------------------------
# 3. Direct Tool REST Endpoints for Dedicated Dashboard Views
# -----------------------------------------------------------------------------

@router.get("/weather", response_model=schemas.WeatherResult)
def get_weather_endpoint(
    location: str = Query("Mandya, India", description="City or district location")
):
    """Direct live weather forecast and spraying advisory endpoint."""
    return get_weather_forecast(location=location)

@router.post("/irrigation/calculate", response_model=schemas.IrrigationResult)
def calculate_irrigation_endpoint(
    crop: str = Form(...),
    soil_type: str = Form("Loam"),
    growth_stage: str = Form("vegetative"),
    location: str = Form("Mandya, India"),
    irrigation_method: str = Form("drip"),
    field_area_acres: float = Form(1.0),
    soil_moisture_percent: Optional[float] = Form(None)
):
    """Direct FAO-56 Penman-Monteith smart irrigation calculation endpoint."""
    weather = get_weather_forecast(location=location)
    return calculate_irrigation_schedule(
        crop_name=crop,
        soil_type=soil_type,
        growth_stage=growth_stage,
        temp_c=weather.temperature_c,
        rainfall_mm=weather.rainfall_mm,
        soil_moisture_percent=soil_moisture_percent,
        irrigation_method=irrigation_method,
        field_area_acres=field_area_acres
    )

@router.post("/fertilizer/calculate", response_model=schemas.FertilizerResult)
def calculate_fertilizer_endpoint(
    crop: str = Form(...),
    soil_type: str = Form("Loam"),
    growth_stage: str = Form("basal"),
    soil_ph: Optional[float] = Form(None),
    soil_n_status: Optional[str] = Form("medium"),
    soil_p_status: Optional[str] = Form("medium"),
    soil_k_status: Optional[str] = Form("medium"),
    field_area_acres: float = Form(1.0)
):
    """Direct ICAR STCR rule-based fertilizer dose calculation endpoint."""
    return get_fertilizer_recommendation(
        crop_name=crop,
        soil_type=soil_type,
        growth_stage=growth_stage,
        soil_ph=soil_ph,
        soil_n_status=soil_n_status,
        soil_p_status=soil_p_status,
        soil_k_status=soil_k_status,
        field_area_acres=field_area_acres
    )

@router.get("/market/prices", response_model=schemas.MarketResult)
def get_market_prices_endpoint(
    commodity: str = Query("Tomato", description="Crop or commodity name"),
    location: str = Query("", description="State or Mandi location")
):
    """Direct APMC Mandi commodity market price lookup endpoint."""
    return get_market_prices(commodity=commodity, state_or_mandi=location)

@router.get("/knowledge/search", response_model=schemas.KnowledgeResult)
def search_knowledge_endpoint(
    query: str = Query(..., description="Crop management query")
):
    """Direct agronomy RAG knowledge base search endpoint."""
    return search_crop_knowledge(query=query)

@router.get("/reports", response_model=List[schemas.DiseaseReportResponse])
def get_user_disease_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns historical disease reports for the authenticated user."""
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
