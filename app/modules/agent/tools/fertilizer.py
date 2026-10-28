from typing import Optional, List
from langchain_core.tools import tool
from app.modules.agent.schemas import FertilizerResult

FERTILIZER_RULES = {
    "tomato": {
        "basal": {
            "focus": "Phosphorus & Root Development",
            "npk": ["Urea: 45 kg/acre", "Single Super Phosphate (SSP): 150 kg/acre", "Muriate of Potash (MOP): 35 kg/acre"],
            "organic": "5 tons/acre well-decomposed Farmyard Manure (FYM) or Vermicompost",
            "stage": "At transplanting / land preparation"
        },
        "vegetative": {
            "focus": "Nitrogen for Foliage Growth",
            "npk": ["Urea: 55 kg/acre (Top dressing)", "Muriate of Potash (MOP): 25 kg/acre"],
            "organic": "Neem cake blend (50 kg/acre) for soil pest deterrence",
            "stage": "25-30 days after transplanting"
        },
        "flowering": {
            "focus": "Potassium & Boron for Fruit Setting",
            "npk": ["Urea: 30 kg/acre", "Muriate of Potash (MOP): 40 kg/acre", "Foliar Boron spray (0.2%)"],
            "organic": "Foliar Panchagavya / Seaweed extract (3 ml/liter)",
            "stage": "50-60 days after transplanting"
        }
    },
    "rice": {
        "basal": {
            "focus": "Phosphorus & Zinc Soil Incorporation",
            "npk": ["DAP (Di-ammonium Phosphate): 50 kg/acre", "MOP: 25 kg/acre", "Zinc Sulfate: 10 kg/acre"],
            "organic": "4 tons/acre FYM or Green Manuring with Dhaincha",
            "stage": "At final puddling before transplanting"
        },
        "vegetative": {
            "focus": "Nitrogen Top Dressing",
            "npk": ["Urea: 35 kg/acre (Split 1)"],
            "organic": "Azospirillum / Biofertilizer slurry root dip",
            "stage": "20-25 days after transplanting (Tillering)"
        },
        "flowering": {
            "focus": "Panicle Development & Grain Filling",
            "npk": ["Urea: 25 kg/acre", "MOP: 15 kg/acre"],
            "organic": "Foliar Liquid Bio-potash spray",
            "stage": "Panicle initiation stage (45-50 days)"
        }
    },
    "wheat": {
        "basal": {
            "focus": "Basal NPK Balance",
            "npk": ["Urea: 30 kg/acre", "SSP: 125 kg/acre", "MOP: 20 kg/acre"],
            "organic": "3 tons/acre FYM",
            "stage": "At sowing time"
        },
        "vegetative": {
            "focus": "Crown Root Initiation Nitrogen",
            "npk": ["Urea: 45 kg/acre (First irrigation top dressing)"],
            "organic": "Vermicompost top-up (200 kg/acre)",
            "stage": "21 days after sowing"
        }
    }
}

def get_fertilizer_recommendation(
    crop_name: str,
    soil_type: str = "Loam",
    growth_stage: str = "basal",
    soil_ph: Optional[float] = None
) -> FertilizerResult:
    """
    Calculates deterministic fertilizer & nutrient advisory recommendations.
    """
    crop_key = crop_name.lower().strip() if crop_name else "default"
    stage_key = "basal"
    
    stage_input = growth_stage.lower()
    if "flower" in stage_input or "fruit" in stage_input or "grain" in stage_input:
        stage_key = "flowering"
    elif "veg" in stage_input or "tiller" in stage_input or "growth" in stage_input:
        stage_key = "vegetative"

    crop_rules = FERTILIZER_RULES.get(crop_key, FERTILIZER_RULES["tomato"])
    stage_data = crop_rules.get(stage_key, crop_rules["basal"])

    # Soil pH consideration
    ph_advice = "Soil pH within standard range."
    if soil_ph:
        if soil_ph < 6.0:
            ph_advice = f"Acidic soil (pH {soil_ph}). Apply 150-200 kg/acre agricultural lime 2 weeks prior to basal fertilizers."
        elif soil_ph > 8.0:
            ph_advice = f"Alkaline soil (pH {soil_ph}). Incorporate gypsum (200 kg/acre) or organic sulfur to prevent micronutrient lockout."

    reasoning = (
        f"Recommendation tailored for {crop_name.capitalize()} during {stage_key} stage in {soil_type} soil. "
        f"Focuses on balanced nutrient availability."
    )

    return FertilizerResult(
        crop=crop_name.capitalize(),
        growth_stage=stage_key.capitalize(),
        nutrient_focus=stage_data["focus"],
        recommendation=stage_data["npk"],
        organic_option=stage_data["organic"],
        application_stage=stage_data["stage"],
        soil_considerations=f"{soil_type} soil. {ph_advice}",
        reasoning=reasoning,
        data_source="AgriMind Agronomy Rule Engine",
        disclaimer="General agronomic guidance. Conduct a laboratory soil test for field-specific prescriptions."
    )

@tool
def fertilizer_tool(crop_name: str, growth_stage: str = "basal") -> str:
    """Calculates deterministic N-P-K fertilizer recommendations."""
    res = get_fertilizer_recommendation(crop_name, growth_stage=growth_stage)
    rec_str = ", ".join(res.recommendation)
    return f"Fertilizer Plan for {res.crop} ({res.growth_stage} stage): Focus: {res.nutrient_focus}. Dose: {rec_str}. Organic: {res.organic_option}"
