import os
import json
import time
import logging
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from app.modules.agent.schemas import DiseaseAssessment
from app.config import settings

logger = logging.getLogger("agrimind.disease")

DEFAULT_DISCLAIMER = (
    "AI-generated crop health assessment. Severe or uncertain cases "
    "should be confirmed by a qualified agricultural expert."
)

# In-memory cache for live connectivity probe (TTL 60s)
_gemini_status_cache: Dict[str, Any] = {
    "result": None,
    "timestamp": 0.0,
    "key_len": 0,
    "model": ""
}

def check_gemini_status(force_probe: bool = False, test_connectivity: bool = True) -> Dict[str, Any]:
    """
    Evaluates the live operational status of Google Gemini Vision API.
    Performs real backend API verification test using the official Google GenAI SDK.
    Differentiates:
      - DEMO: Explicit DEMO mode active
      - NOT_CONFIGURED: Key is absent or placeholder
      - CONFIGURED_NOT_TESTED: Key present but probe deferred
      - CONNECTED: Real API authentication and test generation succeeded
      - INVALID_KEY: API explicitly rejects credentials (400/403 API_KEY_INVALID)
      - MODEL_ERROR: Key authenticated, but model access failed (404/Quota)
      - CONNECTION_ERROR: Network timeout or transport failure
    """
    mode_env = settings.get_gemini_mode()
    api_key = settings.get_gemini_api_key()
    model = settings.get_gemini_model()

    if mode_env == "DEMO":
        return {
            "mode": "DEMO",
            "model": model,
            "configured": bool(api_key),
            "authenticated": False,
            "gemini_configured": bool(api_key),
            "status_detail": "Explicit DEMO mode enabled via GEMINI_MODE=DEMO environment setting."
        }

    if not api_key:
        return {
            "mode": "NOT_CONFIGURED",
            "model": model,
            "configured": False,
            "authenticated": False,
            "gemini_configured": False,
            "status_detail": "GEMINI_API_KEY is not configured in environment or .env. System operates in transparent agronomic DEMO mock mode."
        }

    if not test_connectivity:
        return {
            "mode": "CONFIGURED_NOT_TESTED",
            "model": model,
            "configured": True,
            "authenticated": False,
            "gemini_configured": True,
            "status_detail": f"GEMINI_API_KEY detected for model {model}. Connectivity test pending."
        }

    # Check cached verification (valid for 60 seconds unless forced)
    now = time.time()
    if (
        not force_probe and 
        _gemini_status_cache["result"] is not None and 
        (now - _gemini_status_cache["timestamp"]) < 60.0 and
        _gemini_status_cache["key_len"] == len(api_key) and
        _gemini_status_cache["model"] == model
    ):
        return _gemini_status_cache["result"]

    # Perform safe live backend connectivity test using official google-genai SDK
    try:
        import google.genai as genai
        from google.genai import errors as genai_errors

        client = genai.Client(api_key=api_key)
        # Lightweight probe test
        probe_res = client.models.generate_content(
            model=model,
            contents="Ping"
        )
        if probe_res and probe_res.text:
            result = {
                "mode": "CONNECTED",
                "model": model,
                "configured": True,
                "authenticated": True,
                "gemini_configured": True,
                "status_detail": f"Google Gemini Vision active and verified connected using official model {model}."
            }
        else:
            result = {
                "mode": "CONNECTED",
                "model": model,
                "configured": True,
                "authenticated": True,
                "gemini_configured": True,
                "status_detail": f"Google Gemini Vision connected using official model {model}."
            }
    except Exception as exc:
        err_str = str(exc)
        logger.warning(f"Gemini API connectivity probe error: {err_str[:200]}")
        
        # Categorize exact error state
        if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
            result = {
                "mode": "INVALID_KEY",
                "model": model,
                "configured": True,
                "authenticated": False,
                "gemini_configured": False,
                "status_detail": "Google Gemini API rejected credentials: API_KEY_INVALID. Please verify your GEMINI_API_KEY."
            }
        elif any(t in err_str.lower() for t in ["503", "unavailable", "high demand", "spikes in demand"]):
            result = {
                "mode": "CONNECTION_ERROR",
                "model": model,
                "configured": True,
                "authenticated": True,
                "gemini_configured": True,
                "status_detail": f"Google Gemini API temporarily unavailable due to upstream demand spike (503): {err_str[:120]}"
            }
        elif "404" in err_str or "not found" in err_str.lower():
            result = {
                "mode": "MODEL_ERROR",
                "model": model,
                "configured": True,
                "authenticated": True,
                "gemini_configured": True,
                "status_detail": f"Gemini API authentication succeeded, but model '{model}' was not found: {err_str[:120]}"
            }
        elif any(t in err_str.lower() for t in ["timeout", "connection", "protocol", "getaddrinfo", "resource_exhausted"]):
            result = {
                "mode": "CONNECTION_ERROR",
                "model": model,
                "configured": True,
                "authenticated": False,
                "gemini_configured": False,
                "status_detail": f"Network, timeout, or rate error connecting to Google Gemini API: {err_str[:120]}"
            }
        else:
            result = {
                "mode": "MODEL_ERROR",
                "model": model,
                "configured": True,
                "authenticated": False,
                "gemini_configured": False,
                "status_detail": f"Gemini API error during connectivity test: {err_str[:120]}"
            }

    _gemini_status_cache["result"] = result
    _gemini_status_cache["timestamp"] = now
    _gemini_status_cache["key_len"] = len(api_key)
    _gemini_status_cache["model"] = model
    return result

def get_mock_disease_assessment(crop_name: Optional[str] = "Crop") -> DiseaseAssessment:
    """Returns a clearly marked demo/mock disease assessment when GEMINI_API_KEY is not configured or in DEMO mode."""
    crop_str = crop_name if crop_name and "crop" not in crop_name.lower() else "Tomato"
    return DiseaseAssessment(
        identified_crop=crop_str,
        possible_condition="Tomato Early Blight (Alternaria solani)",
        assessment_level="Likely",
        severity="Moderate",
        image_quality="Adequate",
        observations=[
            "Dark brown concentric rings on lower leaves (target-board appearance)",
            "Yellow chlorotic halo surrounding necrotic lesions",
            "Slight stem collar discoloration near lower plant node"
        ],
        symptoms=[
            "Premature defoliation of lower canopy leaves",
            "Target-spot pattern foliar necrosis",
            "Reduced photosynthetic leaf area"
        ],
        cause="Fungal pathogen Alternaria solani thriving under warm temperatures (24–29°C) and extended leaf wetness.",
        organic_treatment=[
            "Prune and safely destroy heavily infected lower foliage to reduce spore load",
            "Apply bio-fungicide Bacillus subtilis or Trichoderma harzianum (5g/liter) as preventative foliar spray",
            "Spray 0.5% neem oil emulsion on foliage to suppress fungal sporulation"
        ],
        chemical_treatment=[
            "Apply approved copper oxychloride (50% WP) adhering strictly to state university dosage guidelines",
            "In severe outbreaks, rotate with an approved Mancozeb or Azoxystrobin fungicide"
        ],
        treatment=[
            "Prune and safely destroy heavily infected lower leaves",
            "Ensure proper field drainage and air circulation",
            "Apply approved organic copper fungicide adhering strictly to local agricultural guidelines"
        ],
        prevention=[
            "Practice 3-year crop rotation with non-solanaceous crops",
            "Use drip irrigation instead of overhead sprinklers to keep leaves dry",
            "Apply organic straw mulch around base of plants to prevent soil-splash spore transmission"
        ],
        requires_expert_confirmation=True,
        disclaimer=DEFAULT_DISCLAIMER,
        is_mock=True
    )

def diagnose_crop_disease_with_gemini(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    crop_context: str = "",
    observed_symptoms: str = ""
) -> DiseaseAssessment:
    """
    Calls Gemini 2.5 Flash Vision model to analyze crop leaf images and produce structured assessment.
    """
    mode_env = settings.get_gemini_mode()
    api_key = settings.get_gemini_api_key()
    model_name = settings.get_gemini_model()

    # 1. Check for Explicit DEMO Mode or Missing API Key
    if mode_env == "DEMO" or not api_key:
        logger.info("Operating in explicit DEMO/MOCK mode for crop disease diagnosis.")
        return get_mock_disease_assessment(crop_context)

    # 2. Valid API Key -> Perform Live Gemini Vision Call with network retry
    try:
        import google.genai as genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        
        prompt = (
            "You are an expert plant pathologist and agronomist. Analyze this crop leaf photo thoroughly.\n"
            f"Context provided by farmer: {crop_context or 'Unspecified crop'}\n"
            f"Observed farmer symptoms: {observed_symptoms or 'None reported'}\n\n"
            "Provide your diagnostic findings in raw JSON format (no markdown formatting, no ```json blocks) matching this exact schema:\n"
            "{\n"
            '  "identified_crop": "Identified crop name (e.g. Tomato, Rice, Cotton, or Unknown)",\n'
            '  "possible_condition": "Suspected disease or physiological condition name",\n'
            '  "assessment_level": "Likely" or "Possible" or "Uncertain",\n'
            '  "severity": "Mild" or "Moderate" or "Severe" or "Uncertain",\n'
            '  "image_quality": "Clear" or "Adequate" or "Blurry" or "Unidentifiable",\n'
            '  "observations": ["visual feature observed on leaf 1", "feature 2"],\n'
            '  "symptoms": ["agronomic symptom 1", "symptom 2"],\n'
            '  "cause": "Underlying pathogen or environmental cause description",\n'
            '  "organic_treatment": ["organic/biological control step 1", "step 2"],\n'
            '  "chemical_treatment": ["chemical control measure 1", "measure 2"],\n'
            '  "prevention": ["preventive agronomic practice 1", "practice 2"],\n'
            '  "requires_expert_confirmation": true,\n'
            f'  "disclaimer": "{DEFAULT_DISCLAIMER}"\n'
            "}\n\n"
            "Strict rules:\n"
            "- If the image does not clearly depict a plant leaf/crop or is too blurry to diagnose, set image_quality to 'Unidentifiable' or 'Blurry', assessment_level to 'Uncertain', and ask the farmer to provide a clearer photo in observations.\n"
            "- Do NOT invent numerical chemical dosages. Keep recommendations general and ICAR-aligned.\n"
            "- Never present an uncertain diagnosis as confirmed fact."
        )

        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[image_part, prompt]
                )
                break
            except Exception as net_err:
                if attempt < max_attempts:
                    logger.warning(f"Gemini Vision call attempt {attempt} failed, retrying: {net_err}")
                    time.sleep(1.0)
                    continue
                raise net_err

        raw_text = response.text.strip()
        # Clean potential markdown wrapping if returned
        if raw_text.startswith("```json"):
            raw_text = raw_text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text.split("```", 1)[1].rsplit("```", 1)[0].strip()

        data = json.loads(raw_text)

        # Enforce assessment_level safety values
        level = data.get("assessment_level", "Likely")
        if level not in ["Likely", "Possible", "Uncertain"]:
            level = "Likely"

        severity = data.get("severity", "Moderate")
        if severity not in ["Mild", "Moderate", "Severe", "Uncertain"]:
            severity = "Moderate"

        img_qual = data.get("image_quality", "Adequate")

        organic = data.get("organic_treatment", [])
        chemical = data.get("chemical_treatment", [])
        combined_treatment = organic + chemical if (organic or chemical) else data.get("treatment", [])

        return DiseaseAssessment(
            identified_crop=data.get("identified_crop", crop_context or "Crop"),
            possible_condition=data.get("possible_condition", "Unspecified Plant Condition"),
            assessment_level=level,
            severity=severity,
            image_quality=img_qual,
            observations=data.get("observations", []),
            symptoms=data.get("symptoms", []),
            cause=data.get("cause", "Environmental or pathological factors"),
            organic_treatment=organic,
            chemical_treatment=chemical,
            treatment=combined_treatment,
            prevention=data.get("prevention", []),
            requires_expert_confirmation=data.get("requires_expert_confirmation", True),
            disclaimer=data.get("disclaimer", DEFAULT_DISCLAIMER),
            is_mock=False
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini Vision response JSON: {str(e)}")
        raise RuntimeError("Failed to decode disease diagnosis output format.") from e
    except Exception as e:
        err_msg = str(e)
        logger.error(f"Gemini API request failed: {err_msg}")
        if "401" in err_msg or "403" in err_msg or "API_KEY_INVALID" in err_msg or "PERMISSION_DENIED" in err_msg:
            raise RuntimeError(f"Gemini Vision API authentication failed: Invalid API key ({err_msg})") from e
        elif "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            raise RuntimeError(f"Gemini Vision API quota exceeded: Rate limit reached ({err_msg})") from e
        else:
            raise RuntimeError(f"Gemini Vision API service error: {err_msg}") from e

@tool
def crop_disease_tool(crop_context: str = "") -> str:
    """
    LangChain tool wrapper metadata for disease diagnosis intent matching.
    """
    return "Crop disease diagnosis tool available for visual leaf photo inspection using Gemini Vision."
