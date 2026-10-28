from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

# --- Disease Assessment ---
class DiseaseAssessment(BaseModel):
    possible_condition: str = Field(..., description="Name of detected or suspected crop disease/health condition.")
    assessment_level: str = Field(..., description="Qualitative level: Likely, Possible, or Uncertain.")
    observations: List[str] = Field(default_factory=list, description="Visual features observed on leaf/stem.")
    symptoms: List[str] = Field(default_factory=list, description="Agronomic symptoms detected.")
    cause: Optional[str] = Field(None, description="Pathogen or environmental root cause.")
    treatment: List[str] = Field(default_factory=list, description="Controlled management practices.")
    prevention: List[str] = Field(default_factory=list, description="Preventive recommendations.")
    disclaimer: str = Field(
        default="AI-generated crop health assessment. Severe or uncertain cases should be confirmed by a qualified agricultural expert.",
        description="Medical/agronomic disclaimer."
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
    data_source: str = "AgriMind Rule-Based Engine"
    is_mock: bool = False

# --- Fertilizer Result ---
class FertilizerResult(BaseModel):
    crop: str
    growth_stage: str
    nutrient_focus: str # e.g. "Nitrogen & Phosphorus Emphasis"
    recommendation: List[str] # N-P-K dosages
    organic_option: str
    application_stage: str
    soil_considerations: str
    reasoning: str
    data_source: str = "AgriMind Agronomy Rule Engine"
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
    source: str # "OpenWeatherMap" or "DEMO / MOCK"
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
    trend: str # e.g. "Stable", "Upward (+3%)"
    data_date: str
    source: str = "Curated Demo APMC Dataset"
    is_demo_data: bool = True
    advisory: str

# --- Knowledge RAG Result ---
class KnowledgeResult(BaseModel):
    query: str
    answer: str
    source_document: str
    relevant_section: str
    source_metadata: dict = Field(default_factory=dict)

# --- Chat Request & Response ---
class ChatRequest(BaseModel):
    message: str = Field(..., description="Farmer text prompt or query.")
    image_b64: Optional[str] = Field(None, description="Optional Base64 encoded JPEG/PNG crop photo.")
    farm_id: Optional[str] = Field(None, description="Optional associated farm ID.")
    crop_id: Optional[str] = Field(None, description="Optional associated crop ID.")

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
