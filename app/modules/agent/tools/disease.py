import os
import json
import logging
from typing import Optional
from langchain_core.tools import tool
from app.modules.agent.schemas import DiseaseAssessment

logger = logging.getLogger("agrimind.disease")

DEFAULT_DISCLAIMER = (
    "AI-generated crop health assessment. Severe or uncertain cases "
    "should be confirmed by a qualified agricultural expert."
)

def get_mock_disease_assessment(crop_name: Optional[str] = "Crop") -> DiseaseAssessment:
    """Returns a clearly marked demo/mock disease assessment when GEMINI_API_KEY is not configured."""
    return DiseaseAssessment(
        possible_condition="Tomato Early Blight (Alternaria solani)",
        assessment_level="Likely",
        observations=[
            "Dark brown concentric rings on lower leaves",
            "Yellow halo surrounding leaf lesions",
            "Slight stem necrosis near lower node"
        ],
        symptoms=[
            "Premature defoliation of lower leaves",
            "Target-spot pattern lesions",
            "Reduced photosynthetic foliage"
        ],
        cause="Fungal pathogen Alternaria solani thriving under warm, high-humidity conditions.",
        treatment=[
            "Prune and safely destroy heavily infected lower leaves",
            "Ensure proper field drainage and air circulation",
            "Apply approved organic copper fungicide adhering strictly to local agricultural guidelines"
        ],
        prevention=[
            "Practice 3-year crop rotation with non-solanaceous crops",
            "Use drip irrigation instead of overhead sprinklers to keep leaves dry",
            "Apply mulch around base of plants to prevent soil-splash spore transmission"
        ],
        disclaimer=DEFAULT_DISCLAIMER,
        is_mock=True
    )

def diagnose_crop_disease_with_gemini(image_bytes: bytes, mime_type: str = "image/jpeg", crop_context: str = "") -> DiseaseAssessment:
    """
    Calls Gemini 2.5 Flash Vision model to analyze crop leaf images and produce structured assessment.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    # 1. Missing or Placeholder API Key -> Explicit Mock Mode
    if not api_key or api_key.startswith("your_"):
        logger.info("GEMINI_API_KEY not found or placeholder in environment. Activating explicit DEMO/MOCK mode.")
        return get_mock_disease_assessment(crop_context)

    # 2. Valid API Key -> Perform Gemini Vision Call
    try:
        import google.genai as genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        
        prompt = (
            "You are an expert plant pathologist and agronomist. Analyze this crop image carefully.\n"
            f"Crop context: {crop_context or 'Unspecified crop'}\n\n"
            "Provide your diagnostic findings in raw JSON format (no markdown formatting, no ```json blocks) matching this exact schema:\n"
            "{\n"
            '  "possible_condition": "Short disease or condition name",\n'
            '  "assessment_level": "Likely" or "Possible" or "Uncertain",\n'
            '  "observations": ["observed visual leaf feature 1", "feature 2"],\n'
            '  "symptoms": ["symptom 1", "symptom 2"],\n'
            '  "cause": "Underlying pathogen or environmental cause description",\n'
            '  "treatment": ["controlled agronomic treatment 1", "treatment 2"],\n'
            '  "prevention": ["preventive practice 1", "practice 2"],\n'
            f'  "disclaimer": "{DEFAULT_DISCLAIMER}"\n'
            "}\n\n"
            "Important guidelines:\n"
            "- Do NOT invent exact numerical pesticide/fertilizer dosages (e.g. do not say '2.5ml per liter'). Keep recommendations focused on general agronomic practices.\n"
            "- Do NOT use numeric probability scores. Use assessment_level as 'Likely', 'Possible', or 'Uncertain'."
        )

        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[image_part, prompt]
        )

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

        return DiseaseAssessment(
            possible_condition=data.get("possible_condition", "Unspecified Plant Condition"),
            assessment_level=level,
            observations=data.get("observations", []),
            symptoms=data.get("symptoms", []),
            cause=data.get("cause", "Environmental or pathological factors"),
            treatment=data.get("treatment", []),
            prevention=data.get("prevention", []),
            disclaimer=data.get("disclaimer", DEFAULT_DISCLAIMER),
            is_mock=False
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini Vision response JSON: {str(e)}")
        raise RuntimeError("Failed to decode disease diagnosis output format.") from e
    except Exception as e:
        logger.error(f"Gemini API request failed: {str(e)}")
        # Real Gemini API failure: raise exception so router returns controlled error
        raise RuntimeError(f"Gemini Vision API service error: {str(e)}") from e

@tool
def diagnose_crop_disease_tool(crop_context: str = "") -> str:
    """
    LangChain tool wrapper metadata for disease diagnosis intent matching.
    """
    return "Crop disease diagnosis tool available for visual leaf photo inspection."
