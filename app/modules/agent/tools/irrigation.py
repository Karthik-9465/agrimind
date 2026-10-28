from typing import Optional
from langchain_core.tools import tool
from app.modules.agent.schemas import IrrigationResult

CROP_WATER_BASE = {
    "tomato": {"base_mm_day": 4.5, "unit_liters": 18000},
    "rice": {"base_mm_day": 7.0, "unit_liters": 28000},
    "paddy": {"base_mm_day": 7.0, "unit_liters": 28000},
    "wheat": {"base_mm_day": 3.5, "unit_liters": 14000},
    "maize": {"base_mm_day": 5.0, "unit_liters": 20000},
    "corn": {"base_mm_day": 5.0, "unit_liters": 20000},
    "cotton": {"base_mm_day": 5.5, "unit_liters": 22000},
    "potato": {"base_mm_day": 4.0, "unit_liters": 16000},
}

SOIL_INTERVAL_MAP = {
    "sandy": {"interval_days": 2, "retention": "Low soil moisture retention", "factor": 1.1},
    "clay": {"interval_days": 4, "retention": "High soil moisture retention", "factor": 0.9},
    "black clay": {"interval_days": 5, "retention": "High moisture retention clay", "factor": 0.85},
    "loam": {"interval_days": 3, "retention": "Optimal moisture retention", "factor": 1.0},
    "silt": {"interval_days": 3, "retention": "Moderate retention", "factor": 1.0},
}

def calculate_irrigation_schedule(
    crop_name: str,
    soil_type: str = "Loam",
    growth_stage: str = "vegetative",
    temp_c: Optional[float] = None,
    rainfall_mm: Optional[float] = None
) -> IrrigationResult:
    """
    Calculates deterministic crop irrigation schedule and water requirements.
    """
    crop_key = crop_name.lower().strip() if crop_name else ""
    soil_key = soil_type.lower().strip() if soil_type else "loam"

    if not crop_key:
        return IrrigationResult(
            crop="Unspecified",
            soil_type=soil_type,
            growth_stage=growth_stage,
            soil_moisture_status="Unknown",
            water_requirement="Insufficient Information",
            irrigation_interval="Requires crop name",
            recommended_action="Please specify a crop name to calculate an accurate irrigation schedule.",
            reasoning="Missing crop parameter.",
            data_source="AgriMind Rule-Based Engine",
            is_mock=False
        )

    # Base crop requirements
    crop_data = CROP_WATER_BASE.get(crop_key, {"base_mm_day": 4.0, "unit_liters": 16000})
    base_mm = crop_data["base_mm_day"]
    
    # Soil factors
    soil_info = SOIL_INTERVAL_MAP.get(soil_key, SOIL_INTERVAL_MAP["loam"])
    interval_days = soil_info["interval_days"]
    retention_desc = soil_info["retention"]
    soil_factor = soil_info["factor"]

    # Stage factor
    stage_key = growth_stage.lower()
    stage_factor = 1.0
    if "flower" in stage_key or "fruit" in stage_key or "grain" in stage_key:
        stage_factor = 1.25 # Peak water demand
    elif "initial" in stage_key or "seedling" in stage_key:
        stage_factor = 0.7

    # Climate adjustments
    temp_factor = 1.15 if temp_c and temp_c > 32 else 1.0
    
    calculated_mm = round(base_mm * soil_factor * stage_factor * temp_factor, 1)
    liters_per_acre = int(calculated_mm * 4000)

    # Recommendation & Rainfall adjustment
    if rainfall_mm and rainfall_mm >= 15.0:
        recommended_action = f"Hold irrigation for 2-3 days. Recent rainfall of {rainfall_mm} mm has satisfied soil moisture needs."
        soil_status = "Saturated / Adequate"
    elif rainfall_mm and rainfall_mm >= 5.0:
        recommended_action = f"Reduce irrigation by 50%. Light rainfall of {rainfall_mm} mm observed."
        soil_status = "Moist"
    else:
        recommended_action = f"Apply {calculated_mm} mm of water every {interval_days} days using drip or furrow irrigation."
        soil_status = "Standard moisture maintenance required"

    reasoning = (
        f"Calculated for {crop_name.capitalize()} during {growth_stage} stage in {soil_type} soil. "
        f"{retention_desc}. Adjusted for stage demand factor ({stage_factor}x)."
    )

    return IrrigationResult(
        crop=crop_name.capitalize(),
        soil_type=soil_type,
        growth_stage=growth_stage.capitalize(),
        soil_moisture_status=soil_status,
        water_requirement=f"{calculated_mm} mm/day (approx. {liters_per_acre:,} liters/acre)",
        irrigation_interval=f"Every {interval_days} days",
        recommended_action=recommended_action,
        reasoning=reasoning,
        data_source="AgriMind Rule-Based Engine",
        is_mock=False
    )

@tool
def irrigation_tool(crop_name: str, soil_type: str = "Loam") -> str:
    """Calculates deterministic irrigation water requirements and scheduling."""
    res = calculate_irrigation_schedule(crop_name, soil_type)
    return f"Irrigation Schedule for {res.crop}: {res.water_requirement}, Interval: {res.irrigation_interval}. Action: {res.recommended_action}"
