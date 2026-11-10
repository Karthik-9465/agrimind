from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Disease Assessment ---
class DiseaseAssessment(BaseModel):
    identified_crop: Optional[str] = Field(None, description="Crop identified visually or from user context.")
    possible_condition: str = Field(..., description="Name of detected or suspected crop disease/health condition.")
    assessment_level: str = Field(..., description="Qualitative level: Likely, Possible, or Uncertain.")
    severity: str = Field(default="Moderate", description="Severity grade: Mild, Moderate, Severe, or Uncertain.")
    image_quality: str = Field(default="Adequate", description="Image clarity feedback: Clear, Adequate, Blurry, or Unidentifiable.")
    observations: List[str] = Field(default_factory=list, description="Visual features observed on leaf/stem.")
    symptoms: List[str] = Field(default_factory=list, description="Agronomic symptoms detected.")
    cause: Optional[str] = Field(None, description="Pathogen or environmental root cause.")
    organic_treatment: List[str] = Field(default_factory=list, description="Organic biological management practices.")
    chemical_treatment: List[str] = Field(default_factory=list, description="Approved chemical management practices.")
    treatment: List[str] = Field(default_factory=list, description="Consolidated recommended management practices.")
    prevention: List[str] = Field(default_factory=list, description="Preventive recommendations.")
    requires_expert_confirmation: bool = Field(default=True, description="Whether confirmation by agricultural extension officer is advised.")
    disclaimer: str = Field(
        default="AI-generated crop health assessment. Severe or uncertain cases should be confirmed by a qualified agricultural expert.",
        description="Agronomic and legal disclaimer."
    )
    is_mock: bool = Field(default=False, description="Flag indicating whether response is from mock/demo mode.")

# --- Irrigation Result ---
class IrrigationResult(BaseModel):
    crop: str
    soil_type: str
    growth_stage: str
    soil_moisture_status: str
    water_requirement: str # e.g. "4.5 mm/day (approx. 18,000 liters/acre)"
    irrigation_interval: str # e.g. "Every 3 days"
    recommended_action: str
    reasoning: str
    data_source: str = "AgriMind FAO-56 Penman-Monteith Scientific Engine"
    is_mock: bool = False

# --- Fertilizer Result ---
class FertilizerResult(BaseModel):
    crop: str
    growth_stage: str
    nutrient_focus: str # e.g. "Phosphorus for Root Establishment"
    recommendation: List[str] # N-P-K dosages
    organic_option: str
    application_stage: str
    soil_considerations: str
    reasoning: str
    data_source: str = "AgriMind ICAR STCR Agronomy Engine"
    disclaimer: str = "General agronomic guidance. Conduct a laboratory soil test for field-specific prescriptions."

# --- Weather Result ---
class WeatherResult(BaseModel):
    location: str
    temperature_c: float
    humidity_percent: int
    rainfall_mm: float
    rainfall_prob_percent: int
    wind_speed_kmh: float
    forecast: str
    agricultural_advisory: str
    source: str # "Open-Meteo Live Meteorology", "OpenWeatherMap (Live)" or "DEMO / MOCK"
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    is_mock: bool = False

# --- Market Result ---
class MarketResult(BaseModel):
    commodity: str
    mandi: str
    state: str
    minimum_price: float # ₹ / quintal
    maximum_price: float
    modal_price: float
    unit: str = "₹ / quintal"
    trend: str # e.g. "Upward (+4.2%)", "Stable"
    data_date: str
    source: str = "Official Agmarknet APMC Mandi Benchmark"
    is_demo_data: bool = True
    advisory: str

# --- Knowledge RAG Result ---
class KnowledgeResult(BaseModel):
    query: str
    answer: str
    source_document: str
    relevant_section: str
    source_metadata: Dict[str, Any] = Field(default_factory=dict)

# --- Voice Interaction Schemas ---
class VoiceTranscribeResponse(BaseModel):
    text: str
    language_detected: str
    confidence: float
    duration_seconds: Optional[float] = None
    is_mock: bool
    provider: str
    note: Optional[str] = None

class VoiceSynthesizeRequest(BaseModel):
    text: str
    language: str = "te" # "te", "hi", "en"
    speed: float = 1.0
    voice: Optional[str] = None
    container: Optional[str] = None # "wav", "mp3"

# --- Chat Request & Response ---
class ChatRequest(BaseModel):
    message: str = Field(..., description="Farmer text prompt or transcribed voice query.")
    image_b64: Optional[str] = Field(None, description="Optional Base64 encoded JPEG/PNG/WEBP crop photo.")
    farm_id: Optional[str] = Field(None, description="Optional associated farm ID.")
    crop_id: Optional[str] = Field(None, description="Optional associated crop ID.")
    language: Optional[str] = Field("en", description="Preferred response language: en, te, hi.")

class ChatResponse(BaseModel):
    reply: str
    tool_used: Optional[str] = None
    assessment: Optional[DiseaseAssessment] = None
    irrigation: Optional[IrrigationResult] = None
    fertilizer: Optional[FertilizerResult] = None
    weather: Optional[WeatherResult] = None
    market: Optional[MarketResult] = None
    knowledge: Optional[KnowledgeResult] = None
    report_id: Optional[str] = None
    audio_base64: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class DiseaseReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    farm_id: Optional[str] = None
    crop_id: Optional[str] = None
    image_reference: Optional[str] = None
    possible_condition: str
    assessment_level: str
    observations: List[str] = []
    symptoms: List[str] = []
    cause: Optional[str] = None
    treatment: List[str] = []
    prevention: List[str] = []
    disclaimer: str
    is_mock: bool
    created_at: datetime
