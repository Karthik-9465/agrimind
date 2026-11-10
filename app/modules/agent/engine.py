import re
from typing import Optional, Tuple, Dict, Any, List
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

# Multilingual UI Response Templates
LANG_TRANSLATIONS = {
    "te": {
        "disease_intro": "మీ పంట ఆకు ఫోటోను విశ్లేషించాను. గుర్తించిన వ్యాధి/పరిస్థితి: **{condition}** (తీవ్రత: **{severity}**, ఖచ్చితత్వం: **{level}**). సిఫార్సు చేయబడిన సేంద్రీయ మరియు నివారణ చర్యలను క్రింద చూడండి.",
        "irrigation_intro": "**{crop}** పంటకు **{soil}** నేలలో రోజుకు నీటి అవసరం: **{water_req}**, నీటి విరామం: **{interval}**. కార్యాచరణ: {action}",
        "fertilizer_intro": "**{crop}** పంట ({stage} దశ) ఎరువుల ప్రణాళిక:\n• **ముఖ్య దృష్టి**: {focus}\n• **సిఫార్సు మోతాదు**: {rec}\n• **సేంద్రీయ ప్రత్యామ్నాయం**: {organic}",
        "weather_intro": "**{location}** ప్రస్తుత వాతావరణం: {temp}°C, తేమ: {humidity}%, వాతావరణం: {forecast}. వ్యవసాయ సలహా: {advisory}",
        "market_intro": "**{commodity}** మార్కెట్ ధర ({mandi}, {state}):\n• **సగటు ధర**: ₹{modal:,.0f} / క్వింటాల్\n• **ధరల శ్రేణి**: ₹{min:,.0f} - ₹{max:,.0f} / క్వింటాల్\n• **ధోరణి**: {trend}\n• **సలహా**: {advisory}",
        "knowledge_intro": "**{source}** ({section}) ఆధారంగా:\n\n{answer}",
        "upload_prompt": "ఖచ్చితమైన తెగుళ్ల నిర్ధారణ కోసం, దయచేసి వ్యాధి సోకిన ఆకు లేదా మొక్క భాగం స్పష్టమైన ఫోటోను అప్‌లోడ్ చేయండి. మీ పరిశీలించిన లక్షణాలను కూడా తెలపండి.",
        "greeting": "నమస్కారం! నేను మీ అగ్రిమైండ్ AI వ్యవసాయ సహాయకుడిని. పంట వ్యాధులు, నీటి పారుదల, ఎరువుల మోతాదు, వాతావరణ సమాచారం లేదా మార్కెట్ ధరల గురించి నన్ను అడగండి."
    },
    "hi": {
        "disease_intro": "मैंने आपकी फसल की पत्ती की तस्वीर का विश्लेषण किया है। संभावित स्थिति: **{condition}** (गंभीरता: **{severity}**, संभावना: **{level}**)। अनुशंसित जैविक और प्रबंधन उपाय नीचे देखें।",
        "irrigation_intro": "**{crop}** फसल हेतु **{soil}** मिट्टी में दैनिक जल आवश्यकता: **{water_req}**, अंतराल: **{interval}**। सुझाव: {action}",
        "fertilizer_intro": "**{crop}** फसल ({stage} अवस्था) हेतु पोषक तत्व योजना:\n• **मुख्य फोकस**: {focus}\n• **अनुशंसित खुराक**: {rec}\n• **जैविक विकल्प**: {organic}",
        "weather_intro": "**{location}** का मौसम पूर्वानुमान: {temp}°C, आर्द्रता: {humidity}%, स्थिति: {forecast}। कृषि सलाह: {advisory}",
        "market_intro": "**{commodity}** मंडी भाव ({mandi}, {state}):\n• **मॉडल भाव**: ₹{modal:,.0f} / क्विंटल\n• **मूल्य सीमा**: ₹{min:,.0f} - ₹{max:,.0f} / क्विंटल\n• **रुझान**: {trend}\n• **सलाह**: {advisory}",
        "knowledge_intro": "**{source}** ({section}) के अनुसार:\n\n{answer}",
        "upload_prompt": "सटीक फसल रोग पहचान के लिए, कृपया प्रभावित पत्ती की स्पष्ट फोटो अपलोड करें। आप दिखाई देने वाले लक्षण भी बता सकते हैं।",
        "greeting": "नमस्ते! मैं आपका एग्रीमाइंड एआई कृषि सहायक हूं। आप मुझसे फसल रोग निदान, सिंचाई, उर्वरक, मौसम पूर्वानुमान और मंडी भाव के बारे में पूछ सकते हैं।"
    },
    "en": {
        "disease_intro": "I have analyzed your crop photo. The assessment indicates **{condition}** (Severity: **{severity}**, Likelihood: **{level}**). Please review the recommended organic management practices below.",
        "irrigation_intro": "Based on FAO-56 Penman-Monteith calculation for **{crop}** in **{soil}** soil, the water requirement is **{water_req}** with an interval of **{interval}**. Action: {action}",
        "fertilizer_intro": "AgriMind ICAR STCR nutrient plan for **{crop}** ({stage} stage):\n• **Focus**: {focus}\n• **Recommended Dose**: {rec}\n• **Organic Alternative**: {organic}",
        "weather_intro": "Current weather for **{location}**: {temp}°C, Humidity: {humidity}%, Condition: {forecast}. **Agricultural Advisory**: {advisory} (Source: {source})",
        "market_intro": "APMC Mandi Price for **{commodity}** at {mandi} ({state}):\n• **Modal Price**: ₹{modal:,.0f} / quintal\n• **Price Range**: ₹{min:,.0f} - ₹{max:,.0f} / quintal\n• **Trend**: {trend}\n• **Advisory**: {advisory} (Source: {source})",
        "knowledge_intro": "According to **{source}** ({section}):\n\n{answer}",
        "upload_prompt": "To provide an accurate disease diagnosis, please upload a clear photograph of the affected leaf or plant stem. In the meantime, describe observed symptoms.",
        "greeting": "Hello! I am your AgriMind AI Agronomist assistant. I can assist with Disease Diagnosis, Smart Irrigation, Fertilizer Plans, Weather Advisories, and Mandi Prices."
    }
}

class AgentEngine:
    """
    Central Agentic AI Orchestration Engine supporting:
    1. crop_disease_tool (Gemini Vision)
    2. irrigation_tool (FAO-56 Penman-Monteith)
    3. fertilizer_tool (ICAR STCR rules)
    4. weather_tool (Open-Meteo & OpenWeatherMap)
    5. market_price_tool (APMC Mandi Hub)
    6. agricultural_knowledge_tool (Local RAG)
    7. farm_management_tool (Cadastral farm & crop records)
    + Multi-language Regional Translation (Telugu, Hindi, English)
    + AI Input Safety & Domain Guardrails
    """

    def extract_crop_name(self, text: str, crop_context: str = "") -> str:
        """Extracts crop name from query or context."""
        text_lower = text.lower()
        crops = [
            "tomato", "rice", "paddy", "wheat", "cotton", "maize", "corn",
            "potato", "chilli", "onion", "sugarcane", "soybean", "groundnut", "mustard"
        ]
        for c in crops:
            if c in text_lower:
                return "Rice" if c == "paddy" else ("Maize" if c == "corn" else c.capitalize())
        
        if crop_context and "crop:" in crop_context.lower():
            match = re.search(r'crop:\s*([^\(\,]+)', crop_context, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "Tomato"

    def extract_growth_stage(self, text: str) -> str:
        """Extracts crop growth stage from text."""
        tl = text.lower()
        if any(w in tl for w in ["flower", "bloom", "fruit", "panicle", "heading", "boll"]):
            return "flowering"
        if any(w in tl for w in ["seed", "sow", "initial", "nursery", "transplant", "basal"]):
            return "basal"
        return "vegetative"

    def extract_location(self, text: str, default_loc: str = "Mandya, India") -> str:
        """Extracts city or district location from query if mentioned."""
        tl = text.lower()
        districts = [
            "mandya", "hyderabad", "rangareddy", "guntur", "karnal", "khanna",
            "rajkot", "indore", "nagpur", "nashik", "pune", "varanasi", "delhi", "bengaluru"
        ]
        for d in districts:
            if d in tl:
                return f"{d.capitalize()}, India"
        return default_loc

    def process_request(
        self,
        request: ChatRequest,
        image_bytes: Optional[bytes] = None,
        mime_type: str = "image/jpeg",
        crop_context: str = "",
        farm_location: str = "Mandya, India",
        soil_type: str = "Loam",
        field_area: float = 1.0,
        farm_data: Optional[Dict[str, Any]] = None
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
        Orchestrates intent classification, tool invocation, and regional-language response formatting.
        """
        has_image = image_bytes is not None and len(image_bytes) > 0
        lang = (request.language or "en").lower()
        if lang not in LANG_TRANSLATIONS:
            lang = "en"
        t = LANG_TRANSLATIONS[lang]

        # ---------------------------------------------------------------------
        # STEP 0: Safety & Domain Guardrails
        # ---------------------------------------------------------------------
        is_valid, category, refusal_msg = AgriMindGuardrail.validate_input(request.message, has_image=has_image)
        if not is_valid:
            tool_name = "input_guardrail_refusal" if category == "OFF_TOPIC" else "input_safety_refusal"
            return refusal_msg, tool_name, None, None, None, None, None, None

        message_lower = request.message.lower().strip()
        crop_name = self.extract_crop_name(request.message, crop_context)
        growth_stage = self.extract_growth_stage(request.message)
        location = self.extract_location(request.message, farm_location)

        # ---------------------------------------------------------------------
        # TOOL 1: Crop Disease Tool (Gemini Vision Image Upload)
        # ---------------------------------------------------------------------
        if has_image:
            tool_used = "disease_diagnosis_tool"
            assessment = diagnose_crop_disease_with_gemini(
                image_bytes=image_bytes,
                mime_type=mime_type,
                crop_context=crop_context,
                observed_symptoms=request.message
            )
            reply = t["disease_intro"].format(
                condition=assessment.possible_condition,
                severity=assessment.severity,
                level=assessment.assessment_level
            )
            return reply, tool_used, assessment, None, None, None, None, None

        # ---------------------------------------------------------------------
        # Intent Pattern Matching (English, Telugu & Hindi)
        # ---------------------------------------------------------------------
        disease_pattern = r'\b(disease|blight|fungus|fungal|rot|symptom|symptoms|infection|wilt|rust|diagnose|diagnosis|lesion|lesions|spot|spots|yellow leaves|curl|curling)\b|(తెగులు|వ్యాధి|మచ్చ|తెగుళ్లు|పురుగు)|(रोग|बीमारी|धब्बा|कीट)'
        irrigation_pattern = r'\b(water|irrigate|irrigation|moisture|watering|liters|drip|sprinkler|drainage|eto|etc)\b|(నీరు|నీటి|తడి|డ్రిప్|సాగునీరు)|(सिंचाई|पानी|नमी|ड्रिप)'
        fertilizer_pattern = r'\b(fertilizer|npk|urea|dap|mop|nitrogen|phosphorus|potash|potassium|manure|compost|nutrient|nutrients|dosage|dose|feed|zinc)\b|(ఎరువు|ఎరువులు|యూరియా|డిఎపి|పోటాష్|నత్రజని|భాస్వరం)|(खाद|उर्वरक|यूरिया|डीएपी|पोटाश)'
        weather_pattern = r'\b(weather|rain|rainfall|temperature|humidity|wind|cloud|forecast|sunny|climate|spray window)\b|(వాతావరణం|వర్షం|ఎండ|ఉష్ణోగ్రత)|(मौसम|बारिश|वर्षा|तापमान)'
        market_pattern = r'\b(price|prices|mandi|market|rate|rates|cost|quintal|apmc|commodity|sell|bhav)\b|(ధర|ధరలు|మార్కెట్|మండి|రేటు)|(मंडी|भाव|दाम|मूल्य|दर)'
        knowledge_pattern = r'\b(guide|cultivation|how to grow|planting depth|sowing|spacing|technique|handbook|practices|faw|bollworm)\b'
        farm_mgmt_pattern = r'\b(my farm|my crops|farm profile|registered farm|acreage|holding|field area)\b'

        is_disease = bool(re.search(disease_pattern, message_lower))
        is_irrigation = bool(re.search(irrigation_pattern, message_lower))
        is_fertilizer = bool(re.search(fertilizer_pattern, message_lower))
        is_weather = bool(re.search(weather_pattern, message_lower))
        is_market = bool(re.search(market_pattern, message_lower))
        is_knowledge = bool(re.search(knowledge_pattern, message_lower))
        is_farm_mgmt = bool(re.search(farm_mgmt_pattern, message_lower))

        # 1. Disease Text Inquiry (Prompt to upload image)
        if is_disease and not is_irrigation and not is_fertilizer:
            return t["upload_prompt"], "crop_disease_tool_guidance", None, None, None, None, None, None

        # 2. Smart Irrigation Engine (FAO-56 Penman-Monteith)
        if is_irrigation and not is_fertilizer and not is_market:
            tool_used = "irrigation_rules_engine"
            # Attempt to pull current weather for dynamic rainfall/temp deduction
            weather_data = get_weather_forecast(location=location)
            res = calculate_irrigation_schedule(
                crop_name=crop_name,
                soil_type=soil_type,
                growth_stage=growth_stage,
                temp_c=weather_data.temperature_c,
                rainfall_mm=weather_data.rainfall_mm,
                field_area_acres=field_area
            )
            reply = t["irrigation_intro"].format(
                crop=res.crop,
                soil=res.soil_type,
                water_req=res.water_requirement,
                interval=res.irrigation_interval,
                action=res.recommended_action
            )
            return reply, tool_used, None, res, None, None, None, None

        # 3. Fertilizer Recommendation Engine (ICAR STCR)
        if is_fertilizer and not is_irrigation and not is_market:
            tool_used = "fertilizer_rules_engine"
            res = get_fertilizer_recommendation(
                crop_name=crop_name,
                soil_type=soil_type,
                growth_stage=growth_stage,
                field_area_acres=field_area
            )
            rec_str = ", ".join(res.recommendation)
            reply = t["fertilizer_intro"].format(
                crop=res.crop,
                stage=res.growth_stage,
                focus=res.nutrient_focus,
                rec=rec_str,
                organic=res.organic_option
            )
            return reply, tool_used, None, None, res, None, None, None

        # 4. Weather Service (Open-Meteo & OpenWeatherMap)
        if is_weather and not is_market:
            tool_used = "weather_service"
            res = get_weather_forecast(location=location)
            reply = t["weather_intro"].format(
                location=res.location,
                temp=res.temperature_c,
                humidity=res.humidity_percent,
                forecast=res.forecast,
                advisory=res.agricultural_advisory,
                source=res.source
            )
            return reply, tool_used, None, None, None, res, None, None

        # 5. Market Price Tool (APMC Mandi Hub)
        if is_market:
            tool_used = "mandi_market_lookup"
            res = get_market_prices(commodity=crop_name, state_or_mandi=location)
            reply = t["market_intro"].format(
                commodity=res.commodity,
                mandi=res.mandi,
                state=res.state,
                modal=res.modal_price,
                min=res.minimum_price,
                max=res.maximum_price,
                trend=res.trend,
                advisory=res.advisory,
                source=res.source
            )
            return reply, tool_used, None, None, None, None, res, None

        # 6. Farm Management Tool
        if is_farm_mgmt and farm_data:
            tool_used = "farm_management_tool"
            farms_list = farm_data.get("farms", [])
            farm_names = ", ".join([f.get("name", "Farm") for f in farms_list]) if farms_list else "None registered"
            reply = (
                f"🌾 **Farm Profile Summary**:\n"
                f"• Registered Holdings: {len(farms_list)} ({farm_names})\n"
                f"• Active Selected Context: {crop_context or 'General Farm'}\n"
                f"• Soil Type: {soil_type} | Location: {location}\n"
                f"You can add or update your fields anytime under the Farm Management tab."
            )
            return reply, tool_used, None, None, None, None, None, None

        # 7. Knowledge RAG Tool
        if is_knowledge:
            tool_used = "rag_knowledge_tool"
            res = search_crop_knowledge(message_lower)
            reply = t["knowledge_intro"].format(
                source=res.source_document,
                section=res.relevant_section,
                answer=res.answer
            )
            return reply, tool_used, None, None, None, None, None, res

        # Default Agronomist Guidance
        return t["greeting"], "agri_assistant_chat", None, None, None, None, None, None

agent_engine = AgentEngine()
