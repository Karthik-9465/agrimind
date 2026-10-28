import re
from typing import Optional, Tuple
from app.modules.agent.schemas import (
    ChatRequest, DiseaseAssessment, IrrigationResult,
    FertilizerResult, WeatherResult, MarketResult, KnowledgeResult
)
from app.modules.agent.tools.disease import diagnose_crop_disease_with_gemini
from app.modules.agent.tools.irrigation import calculate_irrigation_schedule
from app.modules.agent.tools.fertilizer import get_fertilizer_recommendation
from app.modules.agent.tools.weather import get_weather_forecast
from app.modules.agent.tools.market import get_market_prices
from app.modules.agent.tools.knowledge import search_crop_knowledge
from app.modules.agent.guardrails import AgriMindGuardrail

class AgentEngine:
    """
    Core LangChain / Gemini Agent Engine orchestrating intent routing across all 6 domain capabilities:
    1. Disease Diagnosis (Vision Tool)
    2. Irrigation Rules Engine
    3. Fertilizer Rules Engine
    4. Weather Service
    5. Mandi Market Price Lookup
    6. RAG Knowledge Tool
    + Input Safety & Domain Guardrails
    """

    def process_request(
        self,
        request: ChatRequest,
        image_bytes: Optional[bytes] = None,
        mime_type: str = "image/jpeg",
        crop_context: str = "",
        farm_location: str = "Mandya, India",
        soil_type: str = "Loam"
    ) -> Tuple[
        str,
        Optional[str],
        Optional[DiseaseAssessment],
        Optional[IrrigationResult],
        Optional[FertilizerResult],
        Optional[WeatherResult],
        Optional[MarketResult],
        Optional[KnowledgeResult]
    ]:
        """
        Processes incoming farmer query and image.
        Returns tuple of (reply_text, tool_used, disease_obj, irrigation_obj, fertilizer_obj, weather_obj, market_obj, knowledge_obj).
        """
        has_image = image_bytes is not None and len(image_bytes) > 0

        # ---------------------------------------------------------------------
        # PRIORITY 0: Input Safety & Domain Guardrails Check
        # ---------------------------------------------------------------------
        is_valid, category, refusal_msg = AgriMindGuardrail.validate_input(request.message, has_image=has_image)
        if not is_valid:
            tool_name = "input_guardrail_refusal" if category == "OFF_TOPIC" else "input_safety_refusal"
            return refusal_msg, tool_name, None, None, None, None, None, None

        message_lower = request.message.lower().strip()

        # Extract crop name from crop_context if available (e.g. "Crop: Tomato (HD). ")
        crop_name = "Tomato"
        if "crop:" in crop_context.lower():
            crop_match = re.search(r'crop:\s*([^\(\,]+)', crop_context, re.IGNORECASE)
            if crop_match:
                crop_name = crop_match.group(1).strip()

        # ---------------------------------------------------------------------
        # PRIORITY 1: Image Attached -> Strictly Route to Disease Diagnosis Tool
        # ---------------------------------------------------------------------
        if has_image:
            tool_used = "disease_diagnosis_tool"
            assessment = diagnose_crop_disease_with_gemini(
                image_bytes=image_bytes,
                mime_type=mime_type,
                crop_context=crop_context
            )
            reply = (
                f"I have analyzed your crop photo. The assessment indicates **{assessment.possible_condition}** "
                f"with a likelihood level of **{assessment.assessment_level}**. "
                f"Please review the detailed symptoms and recommended management practices below."
            )
            return reply, tool_used, assessment, None, None, None, None, None

        # ---------------------------------------------------------------------
        # PRIORITY 2: Text Intent Classification
        # ---------------------------------------------------------------------

        # Intent Regex Patterns
        disease_pattern = r'\b(disease|blight|fungus|fungal|rot|symptom|symptoms|infection|wilt|rust|diagnose|diagnosis|lesion|lesions|spot|spots)\b'
        irrigation_pattern = r'\b(water|irrigate|irrigation|moisture|watering|liters|drip|sprinkler|drainage)\b'
        fertilizer_pattern = r'\b(fertilizer|npk|urea|dap|mop|nitrogen|phosphorus|potash|manure|compost|nutrient|nutrients|dosage|dose)\b'
        weather_pattern = r'\b(weather|rain|rainfall|temperature|humidity|wind|cloud|forecast|sunny|climate)\b'
        market_pattern = r'\b(price|prices|mandi|market|rate|rates|cost|quintal|apmc|commodity|sell)\b'
        knowledge_pattern = r'\b(guide|cultivation|how to grow|planting depth|sowing|spacing|technique|handbook|practices)\b'

        is_disease = bool(re.search(disease_pattern, message_lower))
        is_irrigation = bool(re.search(irrigation_pattern, message_lower))
        is_fertilizer = bool(re.search(fertilizer_pattern, message_lower))
        is_weather = bool(re.search(weather_pattern, message_lower))
        is_market = bool(re.search(market_pattern, message_lower))
        is_knowledge = bool(re.search(knowledge_pattern, message_lower))

        # Count matched intents to detect ambiguity
        matched_count = sum([is_disease, is_irrigation, is_fertilizer, is_weather, is_market, is_knowledge])

        # 1. Disease Text Inquiry
        if is_disease and not is_irrigation and not is_fertilizer:
            reply = (
                "To provide an accurate disease diagnosis, please upload a clear photograph of the affected leaf or plant stem. "
                "In the meantime, feel free to describe the observed symptoms (such as spot patterns, leaf discoloration, or wilting)."
            )
            return reply, "disease_inquiry_guidance", None, None, None, None, None, None

        # 2. Irrigation Engine
        if is_irrigation and not is_fertilizer and not is_market:
            tool_used = "irrigation_rules_engine"
            res = calculate_irrigation_schedule(crop_name=crop_name, soil_type=soil_type, growth_stage="vegetative")
            reply = (
                f"Based on AgriMind deterministic rules for **{res.crop}** in **{res.soil_type}** soil, "
                f"the recommended water requirement is **{res.water_requirement}** with an interval of **{res.irrigation_interval}**. "
                f"Action: {res.recommended_action}"
            )
            return reply, tool_used, None, res, None, None, None, None

        # 3. Fertilizer Engine
        if is_fertilizer and not is_irrigation and not is_market:
            tool_used = "fertilizer_rules_engine"
            res = get_fertilizer_recommendation(crop_name=crop_name, soil_type=soil_type, growth_stage="basal")
            rec_str = ", ".join(res.recommendation)
            reply = (
                f"AgriMind rule-based nutrient plan for **{res.crop}** ({res.growth_stage} stage):\n"
                f"• **Focus**: {res.nutrient_focus}\n"
                f"• **Recommended Dose**: {rec_str}\n"
                f"• **Organic Alternative**: {res.organic_option}"
            )
            return reply, tool_used, None, None, res, None, None, None

        # 4. Weather Service
        if is_weather and not is_market:
            tool_used = "weather_service"
            res = get_weather_forecast(location=farm_location)
            reply = (
                f"Current weather forecast for **{res.location}**: {res.temperature_c}°C, Humidity: {res.humidity_percent}%, "
                f"Condition: {res.forecast}. **Agricultural Advisory**: {res.agricultural_advisory} (Source: {res.source})"
            )
            return reply, tool_used, None, None, None, res, None, None

        # 5. Market Price Lookup
        if is_market:
            tool_used = "mandi_market_lookup"
            res = get_market_prices(commodity=crop_name, state_or_mandi=farm_location)
            reply = (
                f"APMC Mandi Price for **{res.commodity}** at {res.mandi} ({res.state}):\n"
                f"• **Modal Price**: ₹{res.modal_price:,.0f} / quintal\n"
                f"• **Price Range**: ₹{res.minimum_price:,.0f} - ₹{res.maximum_price:,.0f} / quintal\n"
                f"• **Trend**: {res.trend}\n"
                f"• **Advisory**: {res.advisory} (Source: {res.source})"
            )
            return reply, tool_used, None, None, None, None, res, None

        # 6. RAG Knowledge Tool
        if is_knowledge:
            tool_used = "rag_knowledge_tool"
            res = search_crop_knowledge(message_lower)
            reply = (
                f"According to **{res.source_document}** ({res.relevant_section}):\n\n"
                f"{res.answer}"
            )
            return reply, tool_used, None, None, None, None, None, res

        # Ambiguous query handling
        if matched_count > 1:
            reply = (
                f"I noticed your request touches on multiple agricultural topics. "
                f"Could you clarify if you would like a **Fertilizer Plan**, an **Irrigation Schedule**, a **Weather Forecast**, or **Mandi Market Prices** for your {crop_name} crop?"
            )
            return reply, "ambiguous_intent_clarification", None, None, None, None, None, None

        # General Agronomist Fallback
        reply = (
            f"Hello! I am your AI Agronomist assistant. You asked: '{request.message}'. "
            "I can assist you with **Disease Diagnosis** (upload a photo), **Irrigation Scheduling**, **Fertilizer Guidance**, **Weather Forecasts**, **Mandi Market Prices**, and **Agronomy Knowledge Base** guides."
        )
        return reply, "agri_assistant_chat", None, None, None, None, None, None

agent_engine = AgentEngine()
