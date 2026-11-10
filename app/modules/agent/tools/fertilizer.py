from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from app.modules.agent.schemas import FertilizerResult

# -----------------------------------------------------------------------------
# ICAR / State Agricultural Universities (SAU) Recommended Dose of Fertilizers (RDF)
# Benchmark N-P-K (kg/acre) and phenological stage splits
# -----------------------------------------------------------------------------
ICAR_CROP_RDF: Dict[str, Dict[str, Any]] = {
    "tomato": {
        "name": "Tomato",
        "total_npk_kg_per_acre": {"N": 50, "P": 25, "K": 25},
        "splits": {
            "basal": {
                "fraction": {"N": 0.30, "P": 1.00, "K": 0.40},
                "focus": "Phosphorus for Root Establishment & Basal Energy",
                "organic": "5 tons/acre well-decomposed Farmyard Manure (FYM) or 2 tons/acre Vermicompost + 50 kg Neem Cake at land preparation.",
                "timing": "Incorporate during final land ploughing / prior to transplanting."
            },
            "vegetative": {
                "fraction": {"N": 0.40, "P": 0.00, "K": 0.20},
                "focus": "Nitrogen for Foliage Vigour & Vegetative Canopy",
                "organic": "Neem cake top-up (40 kg/acre) & Azotobacter/Azospirillum bio-slurry root application.",
                "timing": "25–30 days after transplanting (top dressing)."
            },
            "flowering": {
                "fraction": {"N": 0.30, "P": 0.00, "K": 0.40},
                "focus": "Potassium & Boron for Flower Retention, Fruit Setting & Disease Resistance",
                "organic": "Foliar spray of 3% Panchagavya or Liquid Seaweed Extract at 15-day intervals.",
                "timing": "50–60 days after transplanting (peak blooming / early fruit initiation)."
            }
        }
    },
    "rice": {
        "name": "Rice (Paddy)",
        "total_npk_kg_per_acre": {"N": 48, "P": 24, "K": 24},
        "splits": {
            "basal": {
                "fraction": {"N": 0.25, "P": 1.00, "K": 0.50},
                "focus": "Phosphorus Soil Incorporation & Zinc Micronutrient",
                "organic": "4 tons/acre FYM or in-situ Green Manuring with Sesbania (Dhaincha) ploughed 15 days before transplanting.",
                "timing": "Broadcast at last puddling before seedling transplanting."
            },
            "vegetative": {
                "fraction": {"N": 0.50, "P": 0.00, "K": 0.00},
                "focus": "Nitrogen for Maximum Tillering",
                "organic": "Azospirillum & Phosphobacteria soil application (2 kg/acre).",
                "timing": "20–25 days after transplanting (active tillering stage)."
            },
            "flowering": {
                "fraction": {"N": 0.25, "P": 0.00, "K": 0.50},
                "focus": "Potassium for Panicle Emergence & Grain Filling",
                "organic": "Foliar Potash mobilizing bio-fertilizer or Vermiwash spray.",
                "timing": "45–50 days after transplanting (panicle initiation stage)."
            }
        }
    },
    "paddy": {
        "name": "Rice (Paddy)",
        "total_npk_kg_per_acre": {"N": 48, "P": 24, "K": 24},
        "splits": {
            "basal": {
                "fraction": {"N": 0.25, "P": 1.00, "K": 0.50},
                "focus": "Phosphorus Soil Incorporation & Zinc Micronutrient",
                "organic": "4 tons/acre FYM or Green Manuring with Dhaincha.",
                "timing": "At final puddling."
            },
            "vegetative": {
                "fraction": {"N": 0.50, "P": 0.00, "K": 0.00},
                "focus": "Nitrogen for Tillering Vigour",
                "organic": "Biofertilizer slurry application.",
                "timing": "Active tillering stage."
            },
            "flowering": {
                "fraction": {"N": 0.25, "P": 0.00, "K": 0.50},
                "focus": "Potassium for Panicle Filling",
                "organic": "Vermiwash foliar spray.",
                "timing": "Panicle initiation."
            }
        }
    },
    "wheat": {
        "name": "Wheat",
        "total_npk_kg_per_acre": {"N": 48, "P": 24, "K": 16},
        "splits": {
            "basal": {
                "fraction": {"N": 0.33, "P": 1.00, "K": 1.00},
                "focus": "Basal Phosphorus & Seedling Rooting",
                "organic": "3 tons/acre well-rotted cattle manure or compost.",
                "timing": "Drill into seedbed along with seed sowing."
            },
            "vegetative": {
                "fraction": {"N": 0.34, "P": 0.00, "K": 0.00},
                "focus": "Nitrogen for Crown Root Initiation (CRI)",
                "organic": "Neem coated organic bio-enricher.",
                "timing": "21 days after sowing (first CRI irrigation)."
            },
            "flowering": {
                "fraction": {"N": 0.33, "P": 0.00, "K": 0.00},
                "focus": "Nitrogen for Booting & Spikelet Formation",
                "organic": "Foliar seaweed extract.",
                "timing": "Booting / heading stage (45–50 days after sowing)."
            }
        }
    },
    "cotton": {
        "name": "Cotton",
        "total_npk_kg_per_acre": {"N": 60, "P": 30, "K": 30},
        "splits": {
            "basal": {
                "fraction": {"N": 0.20, "P": 1.00, "K": 0.33},
                "focus": "Basal P & Early Root Establishment",
                "organic": "4 tons/acre FYM + 100 kg Neem cake.",
                "timing": "Basal application at sowing / ridge opening."
            },
            "vegetative": {
                "fraction": {"N": 0.40, "P": 0.00, "K": 0.33},
                "focus": "Nitrogen for Vegetative Branching (Monopodial/Sympodial)",
                "organic": "Biofertilizer liquid drip injection.",
                "timing": "30–35 days after sowing (square formation)."
            },
            "flowering": {
                "fraction": {"N": 0.40, "P": 0.00, "K": 0.34},
                "focus": "Potassium & Magnesium for Boll Development & Anti-wilting",
                "organic": "Foliar 1% MgSO4 + 1% KNO3 equivalent organic formulation.",
                "timing": "60–70 days after sowing (peak boll development)."
            }
        }
    },
    "maize": {
        "name": "Maize",
        "total_npk_kg_per_acre": {"N": 48, "P": 24, "K": 16},
        "splits": {
            "basal": {
                "fraction": {"N": 0.33, "P": 1.00, "K": 1.00},
                "focus": "Basal NPK Soil Incorporation",
                "organic": "3 tons/acre FYM.",
                "timing": "At sowing."
            },
            "vegetative": {
                "fraction": {"N": 0.34, "P": 0.00, "K": 0.00},
                "focus": "Nitrogen at Knee-High Stage",
                "organic": "Vermicompost top dressing.",
                "timing": "25–30 days after sowing."
            },
            "flowering": {
                "fraction": {"N": 0.33, "P": 0.00, "K": 0.00},
                "focus": "Nitrogen at Tasseling / Silking",
                "organic": "Panchagavya foliar application.",
                "timing": "Tasseling stage (45–55 days)."
            }
        }
    },
    "chilli": {
        "name": "Chilli",
        "total_npk_kg_per_acre": {"N": 40, "P": 20, "K": 20},
        "splits": {
            "basal": {
                "fraction": {"N": 0.33, "P": 1.00, "K": 0.50},
                "focus": "Basal Phosphorus & Secondary Nutrients",
                "organic": "4 tons/acre FYM + 50 kg Neem cake.",
                "timing": "At transplanting."
            },
            "vegetative": {
                "fraction": {"N": 0.34, "P": 0.00, "K": 0.00},
                "focus": "Nitrogen for Bushy Canopy",
                "organic": "Vermicompost ring application.",
                "timing": "30 days after transplanting."
            },
            "flowering": {
                "fraction": {"N": 0.33, "P": 0.00, "K": 0.50},
                "focus": "Potassium for Pod Size & Pungency",
                "organic": "Foliar amino acid & micronutrient spray.",
                "timing": "Fruit setting / first picking stage."
            }
        }
    }
}

# Soil Test Crop Response (STCR) adjustment multipliers
STCR_ADJUSTMENT = {
    "low": 1.25,     # Add 25% nutrient if soil test is deficient
    "medium": 1.00,  # Standard RDF
    "high": 0.75     # Reduce 25% nutrient if soil test is abundant
}

def get_fertilizer_recommendation(
    crop_name: str,
    soil_type: str = "Loam",
    growth_stage: str = "basal",
    soil_ph: Optional[float] = None,
    soil_n_status: Optional[str] = None, # "low", "medium", "high"
    soil_p_status: Optional[str] = None,
    soil_k_status: Optional[str] = None,
    field_area_acres: float = 1.0
) -> FertilizerResult:
    """
    Computes scientific, rule-based agronomic fertilizer prescriptions calibrated with ICAR
    recommendations, Soil Test Crop Response (STCR) adjustments, commercial fertilizer conversion,
    and field area scaling.
    """
    crop_key = crop_name.lower().strip() if crop_name else ""
    if not crop_key or crop_key == "unspecified":
        return FertilizerResult(
            crop="Unspecified",
            growth_stage=growth_stage.capitalize(),
            nutrient_focus="Requires Crop Selection",
            recommendation=["Please select or specify your crop to generate an accurate fertilizer recommendation."],
            organic_option="Apply 3–5 tons/acre well-decomposed FYM as general soil conditioner.",
            application_stage="Pre-sowing",
            soil_considerations="Conduct a laboratory soil test to measure exact N-P-K and pH levels.",
            reasoning="Missing crop parameter. Cannot determine Recommended Dose of Fertilizers (RDF).",
            data_source="AgriMind ICAR Agronomy Engine",
            disclaimer="Select a crop to receive scientific fertilizer dosage schedules."
        )

    # 1. Retrieve Crop RDF
    crop_info = ICAR_CROP_RDF.get(crop_key)
    if not crop_info:
        # Generic vegetable baseline
        crop_info = {
            "name": crop_name.capitalize(),
            "total_npk_kg_per_acre": {"N": 40, "P": 20, "K": 20},
            "splits": ICAR_CROP_RDF["tomato"]["splits"]
        }

    # Normalize Growth Stage
    stage_input = growth_stage.lower()
    if "flower" in stage_input or "fruit" in stage_input or "boll" in stage_input or "panicle" in stage_input:
        stage_key = "flowering"
    elif "veg" in stage_input or "till" in stage_input or "grow" in stage_input:
        stage_key = "vegetative"
    else:
        stage_key = "basal"

    stage_data = crop_info["splits"].get(stage_key, crop_info["splits"]["basal"])
    base_npk = crop_info["total_npk_kg_per_acre"]
    fractions = stage_data["fraction"]

    # 2. STCR Soil Test Adjustments
    n_factor = STCR_ADJUSTMENT.get((soil_n_status or "medium").lower(), 1.0)
    p_factor = STCR_ADJUSTMENT.get((soil_p_status or "medium").lower(), 1.0)
    k_factor = STCR_ADJUSTMENT.get((soil_k_status or "medium").lower(), 1.0)

    # Calculate Elemental Nutrient Targets for This Specific Stage (kg/acre)
    target_n = round(base_npk["N"] * fractions["N"] * n_factor, 1)
    target_p = round(base_npk["P"] * fractions["P"] * p_factor, 1)
    target_k = round(base_npk["K"] * fractions["K"] * k_factor, 1)

    # 3. Commercial Fertilizer Conversions
    # Option A: DAP (18% N, 46% P2O5) + Urea (46% N) + MOP (60% K2O)
    recommendations: List[str] = []
    area = max(field_area_acres, 0.1)

    if stage_key == "basal":
        # DAP delivers P2O5 and some N
        dap_kg_acre = round(target_p / 0.46, 1) if target_p > 0 else 0.0
        n_from_dap = dap_kg_acre * 0.18
        remaining_n = max(0.0, target_n - n_from_dap)
        urea_kg_acre = round(remaining_n / 0.46, 1) if remaining_n > 0 else 0.0
        mop_kg_acre = round(target_k / 0.60, 1) if target_k > 0 else 0.0

        if dap_kg_acre > 0:
            recommendations.append(f"DAP (Di-ammonium Phosphate 18:46:0): {dap_kg_acre} kg/acre (Total for {area} ac: {round(dap_kg_acre*area, 1)} kg)")
        if urea_kg_acre > 0:
            recommendations.append(f"Urea (46% N): {urea_kg_acre} kg/acre (Total for {area} ac: {round(urea_kg_acre*area, 1)} kg)")
        if mop_kg_acre > 0:
            recommendations.append(f"MOP (Muriate of Potash 60% K2O): {mop_kg_acre} kg/acre (Total for {area} ac: {round(mop_kg_acre*area, 1)} kg)")
        if not recommendations:
            recommendations.append("No inorganic chemical application required at this stage.")
    else:
        # Top-dressing stages (primarily Urea and MOP)
        urea_kg_acre = round(target_n / 0.46, 1) if target_n > 0 else 0.0
        mop_kg_acre = round(target_k / 0.60, 1) if target_k > 0 else 0.0

        if urea_kg_acre > 0:
            recommendations.append(f"Urea (Top Dressing): {urea_kg_acre} kg/acre (Total for {area} ac: {round(urea_kg_acre*area, 1)} kg)")
        if mop_kg_acre > 0:
            recommendations.append(f"MOP (Potassium Top Dressing): {mop_kg_acre} kg/acre (Total for {area} ac: {round(mop_kg_acre*area, 1)} kg)")
        if not recommendations:
            recommendations.append("Balanced vegetative stage: Maintain moisture; no heavy chemical top-dressing required.")

    # 4. Soil pH Considerations & Soil Health Amendments
    soil_ph_notes = []
    if soil_ph is not None:
        if soil_ph < 6.0:
            soil_ph_notes.append(f"Acidic soil detected (pH {soil_ph}). Apply 150–200 kg/acre Agricultural Lime (CaCO3) 2 weeks prior to sowing to correct phosphorus fixation.")
        elif soil_ph > 8.0:
            soil_ph_notes.append(f"Alkaline/Sodic soil detected (pH {soil_ph}). Apply 200 kg/acre Agricultural Gypsum (CaSO4) and organic sulfur to prevent micronutrient lockout.")
        else:
            soil_ph_notes.append(f"Soil pH is optimal ({soil_ph}), providing ideal nutrient availability.")
    else:
        soil_ph_notes.append("Soil pH not specified. Recommendations assume neutral soil (pH 6.5–7.5).")

    # Soil texture considerations
    soil_lower = soil_type.lower()
    if "sand" in soil_lower:
        soil_ph_notes.append("Sandy soil: Apply Nitrogen in multiple small split doses to prevent leaching into groundwater.")
    elif "clay" in soil_lower:
        soil_ph_notes.append("Clay soil: High nutrient retention; avoid over-fertilizing to prevent root burn.")

    soil_considerations_str = " ".join(soil_ph_notes)

    # 5. Missing Input Transparency
    stcr_note = ""
    if soil_n_status or soil_p_status or soil_k_status:
        stcr_note = f"Adjusted via Soil Test Crop Response (STCR): N={soil_n_status or 'med'}, P={soil_p_status or 'med'}, K={soil_k_status or 'med'}."
    else:
        stcr_note = "Preliminary baseline recommendation. Actual soil laboratory test values were not provided."

    reasoning = (
        f"Calculated for {crop_info['name']} at {stage_key.upper()} stage. "
        f"Elemental Nutrient Target: N={target_n} kg/ac, P={target_p} kg/ac, K={target_k} kg/ac. "
        f"{stcr_note} Timing: {stage_data['timing']}"
    )

    disclaimer = (
        "Preliminary agronomic guidance based on State Agricultural University / ICAR package of practices. "
        "A certified soil testing laboratory report should be consulted for exact field-level prescriptions."
    )

    crop_display_name = "Rice" if crop_key in ["rice", "paddy"] else crop_info["name"]

    return FertilizerResult(
        crop=crop_display_name,
        growth_stage=stage_key.capitalize(),
        nutrient_focus=stage_data["focus"],
        recommendation=recommendations,
        organic_option=stage_data["organic"],
        application_stage=stage_data["timing"],
        soil_considerations=soil_considerations_str,
        reasoning=reasoning,
        data_source="AgriMind Agronomy Rule Engine",
        disclaimer=disclaimer
    )

@tool
def fertilizer_tool(crop_name: str, soil_type: str = "Loam", growth_stage: str = "basal", field_area: float = 1.0) -> str:
    """
    Calculates scientific N-P-K fertilizer and organic nutrient recommendations for crops.
    """
    res = get_fertilizer_recommendation(crop_name=crop_name, soil_type=soil_type, growth_stage=growth_stage, field_area_acres=field_area)
    rec_text = "; ".join(res.recommendation)
    return f"Fertilizer plan for {res.crop} ({res.growth_stage} stage): Focus: {res.nutrient_focus}. Dose: {rec_text}. Organic: {res.organic_option}"
