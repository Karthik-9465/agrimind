import logging
import re
from typing import Optional, Tuple, Dict, Any

from app.modules.agent.schemas import (
    ChatRequest, DiseaseAssessment, IrrigationResult,
    FertilizerResult, WeatherResult, MarketResult, KnowledgeResult
)
from app.modules.agent.tools.disease import diagnose_crop_disease_with_gemini
from app.modules.agent.tools.irrigation import calculate_irrigation_schedule
from app.modules.agent.tools.fertilizer import (
    get_fertilizer_recommendation,
    get_stage_nutrient_overview,
    has_verified_crop_rdf,
)
from app.modules.agent.tools.weather import get_weather_forecast
from app.modules.agent.tools.market import get_market_prices
from app.modules.agent.tools.knowledge import search_crop_knowledge
from app.modules.agent.guardrails import AgriMindGuardrail
from app.modules.agent import nlu
from app.modules.agent import reasoning

logger = logging.getLogger("agrimind.engine")

# Multilingual Structured & Localized Templates (used in DEMO/offline mode and image greetings)
LANG_TRANSLATIONS = {
    "te": {
        "disease_intro": "మీ పంట ఆకు ఫోటోను విశ్లేషించాను. గుర్తించిన వ్యాధి/పరిస్థితి: **{condition}** (తీవ్రత: **{severity}**, ఖచ్చితత్వం: **{level}**). సిఫార్సు చేయబడిన సేంద్రీయ మరియు నివారణ చర్యలను క్రింద చూడండి.",
        "irrigation_intro": "**{crop}** పంటకు **{soil}** నేలలో రోజుకు నీటి అవసరం: **{water_req}**, నీటి విరామం: **{interval}**. కార్యాచరణ: {action}",
        "fertilizer_intro": "**{crop}** పంట ({stage} దశ) ఎరువుల ప్రణాళిక:\n• **ముఖ్య దృష్టి**: {focus}\n• **సిఫార్సు మోతాదు**: {rec}\n• **సేంద్రీయ ప్రత్యామ్నాయం**: {organic}",
        "weather_intro": "**{location}** ప్రస్తుత వాతావరణం: {temp}°C, తేమ: {humidity}%, వాతావరణం: {forecast}. వ్యవసాయ సలహా: {advisory}",
        "market_intro": "**{commodity}** మార్కెట్ ధర ({mandi}, {state}):\n• **సగటు ధర**: ₹{modal:,.0f} / క్వింటాల్\n• **ధరల శ్రేణి**: ₹{min:,.0f} - ₹{max:,.0f} / క్వింటాల్\n• **ధోరణి**: {trend}\n• **సలహా**: {advisory}",
        "knowledge_intro": "**{source}** ({section}) ఆధారంగా:\n\n{answer}",
        "greeting": "నమస్కారం! నేను మీ అగ్రిమైండ్ AI వ్యవసాయ సహాయకుడిని. పంట సాగు, నేల సారం, ఎరువులు, నీటి పారుదల, పురుగులు/వ్యాధులు, వాతావరణం, మార్కెట్ ధరలు, పాడి/పశుపోషణ లేదా ప్రభుత్వ పథకాల గురించి ఏ ప్రశ్నైనా అడగండి.",
    },
    "hi": {
        "disease_intro": "मैंने आपकी फसल की पत्ती की तस्वीर का विश्लेषण किया है। संभावित स्थिति: **{condition}** (गंभीरता: **{severity}**, संभावना: **{level}**)। अनुशंसित जैविक और प्रबंधन उपाय नीचे देखें।",
        "irrigation_intro": "**{crop}** फसल हेतु **{soil}** मिट्टी में दैनिक जल आवश्यकता: **{water_req}**, अंतराल: **{interval}**। सुझाव: {action}",
        "fertilizer_intro": "**{crop}** फसल ({stage} अवस्था) हेतु पोषक तत्व योजना:\n• **मुख्य फोकस**: {focus}\n• **अनुशंसित खुराक**: {rec}\n• **जैविक विकल्प**: {organic}",
        "weather_intro": "**{location}** का मौसम पूर्वानुमान: {temp}°C, आर्द्रता: {humidity}%, स्थिति: {forecast}। कृषि सलाह: {advisory}",
        "market_intro": "**{commodity}** मंडी भाव ({mandi}, {state}):\n• **मॉडल भाव**: ₹{modal:,.0f} / क्विंटल\n• **मूल्य सीमा**: ₹{min:,.0f} - ₹{max:,.0f} / क्विंटल\n• **रुझान**: {trend}\n• **सलाह**: {advisory}",
        "knowledge_intro": "**{source}** ({section}) के अनुसार:\n\n{answer}",
        "greeting": "नमस्ते! मैं आपका एग्रीमाइंड AI कृषि सहायक हूं। आप मुझसे खेती, मिट्टी सुधार, खाद, सिंचाई, कीट-रोग, मौसम, मंडी भाव, पशुपालन या सरकारी योजनाओं से जुड़ा कोई भी प्रश्न पूछ सकते हैं।",
    },
    "en": {
        "disease_intro": "I have analyzed your crop photo. The assessment indicates **{condition}** (Severity: **{severity}**, Likelihood: **{level}**). Please review the recommended organic management practices below.",
        "irrigation_intro": "Based on FAO-56 Penman-Monteith calculation for **{crop}** in **{soil}** soil, the water requirement is **{water_req}** with an interval of **{interval}**. Action: {action}",
        "fertilizer_intro": "AgriMind ICAR STCR nutrient plan for **{crop}** ({stage} stage):\n• **Focus**: {focus}\n• **Recommended Dose**: {rec}\n• **Organic Alternative**: {organic}",
        "weather_intro": "Current weather for **{location}**: {temp}°C, Humidity: {humidity}%, Condition: {forecast}. **Agricultural Advisory**: {advisory} (Source: {source})",
        "market_intro": "APMC Mandi Price for **{commodity}** at {mandi} ({state}):\n• **Modal Price**: ₹{modal:,.0f} / quintal\n• **Price Range**: ₹{min:,.0f} - ₹{max:,.0f} / quintal\n• **Trend**: {trend}\n• **Advisory**: {advisory} (Source: {source})",
        "knowledge_intro": "According to **{source}** ({section}):\n\n{answer}",
        "greeting": "Hello! I am your AgriMind AI Agricultural Assistant. Feel free to ask any agriculture-related question — crops, soil health, fertilizers, irrigation, pests, weather, market prices, dairy/livestock, aquaculture, beekeeping, machinery, or government schemes.",
    },
}

AgentReturnTuple = Tuple[
    str,
    Optional[str],
    Optional[DiseaseAssessment],
    Optional[IrrigationResult],
    Optional[FertilizerResult],
    Optional[WeatherResult],
    Optional[MarketResult],
    Optional[KnowledgeResult],
]


class AgentEngine:
    """
    Hybrid Open-Domain Agricultural Reasoning & Deterministic Tool Orchestration Engine:
      1. Multilingual NLU & Context Resolution (Current Query > Recent History > Farm Background)
      2. Gemini Semantic Planning & Open-Domain Agricultural Q&A (any agricultural subject)
      3. Specialized Deterministic Tools (Disease Vision, FAO-56 Irrigation, ICAR STCR Fertilizer, Weather, Mandi Market, RAG)
      4. Honest Fallback & Missing-Information Clarification (no generic greetings on real questions)
    """

    def extract_crop_name(self, text: str, crop_context: str = "") -> Optional[str]:
        """Word-boundary & multilingual crop extraction (returns None when absent)."""
        return nlu.extract_crop(text, crop_context=crop_context, allow_farm_context=False)

    def extract_growth_stage(self, text: str) -> Optional[str]:
        """Multilingual growth-stage extraction (returns None when unknown)."""
        return nlu.extract_growth_stage(text)

    def extract_location(self, text: str, default_loc: str = "Mandya, India") -> str:
        """Extracts location cleanly without overwriting unless specified."""
        return nlu.extract_location(text, default_location=default_loc) or default_loc

    def _template_lang(self, lang: str) -> str:
        if lang in LANG_TRANSLATIONS:
            return lang
        if lang == "romanized_te":
            return "en"
        if lang == "hinglish":
            return "en"
        return "en"

    def _localize_crop_and_stage(
        self,
        crop: str,
        stage: Optional[str],
        t_lang: str,
    ) -> Tuple[str, str]:
        """Localizes common crop & growth-stage names for deterministic Telugu/Hindi templates."""
        if t_lang == "te":
            crop_map = {
                "Tomato": "టమాటా",
                "Cotton": "పత్తి",
                "Rice": "వరి",
                "Paddy": "వరి",
                "Wheat": "గోధుమ",
                "Maize": "మొక్కజొన్న",
                "Chilli": "మిరప",
                "Groundnut": "వేరుశనగ",
                "Brinjal": "వంగ",
                "Onion": "ఉల్లి",
            }
            stage_map = {
                "Basal": "ప్రాథమిక",
                "Vegetative": "శాఖీయ పెరుగుదల",
                "Flowering": "పూత",
                "Fruiting": "కాయ",
            }
            return crop_map.get(crop, crop), stage_map.get(stage or "", stage or "")
        if t_lang == "hi":
            crop_map = {
                "Tomato": "टमाटर",
                "Cotton": "कपास",
                "Rice": "धान",
                "Paddy": "धान",
                "Wheat": "गेहूं",
                "Maize": "मक्का",
                "Chilli": "मिर्च",
                "Groundnut": "मूंगफली",
                "Brinjal": "बैंगन",
                "Onion": "प्याज",
            }
            stage_map = {
                "Basal": "बुवाई",
                "Vegetative": "वानस्पतिक",
                "Flowering": "फूल",
                "Fruiting": "फल",
            }
            return crop_map.get(crop, crop), stage_map.get(stage or "", stage or "")
        return crop, (stage or "")

    def _deterministic_select_tool(self, context: Dict[str, Any]) -> str:
        """Offline/heuristic fallback router aligned with open-domain agricultural QA."""
        raw = context["original_query"]
        low = raw.lower().strip()
        norm_low = context["normalized_query"].lower()

        if nlu.is_pure_greeting(raw):
            return "agri_assistant_chat"

        weather_pat = r'\b(weather|rain|rainfall|temperature|humidity|wind|cloud|forecast|sunny|climate|spray window)\b|(వాతావరణం|వర్షం|ఎండ|ఉష్ణోగ్రత)|(मौसम|बारिश|वर्षा|तापमान)'
        market_pat = r'\b(price|prices|mandi|market|rate|rates|cost|quintal|apmc|commodity|bhav)\b|(ధర|ధరలు|మార్కెట్|మండి|రేటు)|(मंडी|भाव|दाम|मूल्य|दर)'
        irrigation_pat = r'\b(water|irrigate|irrigation|moisture|watering|liters|drip|sprinkler|drainage|eto|etc)\b|(నీరు|నీటి|తడి|పారుదల|డ్రిప్|సాగునీరు)|(सिंचाई|पानी|नमी|ड्रिप)'
        fertilizer_pat = r'\b(fertilizer|fertilizers|npk|urea|dap|mop|nitrogen|phosphorus|potash|potassium|nutrients?|dosage|dose)\b|(ఎరువు|ఎరువులు|యూరియా|డిఎపి|పోటాష్|నత్రజని|భాస్వరం|పోషకాలు)|(खाद|उर्वरक|यूरिया|डीएपी|पोटाश|पोषक)'
        knowledge_pat = r'\b(search knowledge|knowledge guide|handbook|planting depth|spacing|technique|cultivation guide|faw|fall armyworm|bollworm)\b'
        farm_pat = r'\b(my farm|my crops|farm profile|registered farm|registered holdings|acreage)\b'

        is_weather = bool(re.search(weather_pat, low)) or bool(re.search(weather_pat, raw))
        is_market = bool(re.search(market_pat, low)) or bool(re.search(market_pat, raw))
        is_irrigation = bool(re.search(irrigation_pat, low)) or bool(re.search(irrigation_pat, raw))
        is_fertilizer = bool(re.search(fertilizer_pat, low)) or bool(re.search(fertilizer_pat, raw))
        is_knowledge = bool(re.search(knowledge_pat, low))
        is_farm = bool(re.search(farm_pat, low))

        # Avoid hijacking soil-management / dairy / open-domain queries into fertilizer/irrigation calculators
        if context.get("non_crop_topic") and not is_weather and not is_market and not is_farm:
            return "agri_assistant_chat"

        if is_weather and not is_market:
            return "weather_service"
        if is_market:
            return "mandi_market_lookup"
        if is_irrigation and not is_fertilizer:
            return "irrigation_rules_engine"
        if is_fertilizer and not is_irrigation:
            crop = context.get("resolved_crop")
            # If user asks about nutrients with explicitly unknown/current stage (e.g., "at this stage" / "ప్రస్తుతం"),
            # answer stage-wise via open-domain agent and ask for the stage instead of guessing "vegetative".
            if crop and has_verified_crop_rdf(crop) and not context.get("uncertain_stage"):
                return "fertilizer_rules_engine"
            return "agri_assistant_chat"
        if is_farm:
            return "farm_management_tool"
        if is_knowledge:
            # Verify RAG store actually finds a chunk; otherwise open-domain Gemini answers cleanly
            rag_probe = search_crop_knowledge(norm_low)
            if rag_probe.source_metadata.get("status") != "not_found":
                return "rag_knowledge_tool"
        return "agri_assistant_chat"

    def _merge_planner_and_context(
        self,
        context: Dict[str, Any],
        plan: Optional[Dict[str, Any]],
    ) -> Tuple[str, Dict[str, Any], Optional[Dict[str, Any]]]:
        """Reconciles Gemini semantic planner output with strict current-message entity safeguards."""
        if not plan:
            return self._deterministic_select_tool(context), context, None

        # Check explicit non-agricultural classification from Gemini
        if plan.get("is_agricultural") is False and not AgriMindGuardrail.has_agricultural_signal(context["original_query"]):
            return "input_guardrail_refusal", context, plan

        # Keep explicit UI language if set to te/hi, or adopt Gemini language match when UI is default 'en'
        plan_lang = (plan.get("response_language") or "").strip().lower()
        if context["reply_language"] == "en" and plan_lang in ("te", "hi", "romanized_te", "hinglish", "en"):
            context["reply_language"] = plan_lang

        # Strict entity precedence: explicit crop/stage in current query ALWAYS takes priority
        merged_crop = context.get("explicit_crop") or plan.get("crop") or context.get("resolved_crop")
        if merged_crop and isinstance(merged_crop, str) and merged_crop.lower() in ("null", "none", "unspecified"):
            merged_crop = None
        context["resolved_crop"] = merged_crop

        explicit_stage = context.get("explicit_stage")
        plan_stage = plan.get("growth_stage")
        if isinstance(plan_stage, str) and plan_stage.lower() in ("null", "none", "unknown", ""):
            plan_stage = None
        if explicit_stage:
            context["resolved_stage"] = explicit_stage
        elif context.get("uncertain_stage") and not context.get("is_follow_up"):
            # Do not let planner guess a stage if the user literally said "at this stage" with no stage given
            context["resolved_stage"] = None
        elif plan_stage:
            context["resolved_stage"] = plan_stage

        if not context.get("explicit_soil") and plan.get("soil_type"):
            p_soil = str(plan["soil_type"]).strip()
            if p_soil.lower() not in ("null", "none"):
                context["resolved_soil"] = p_soil
        if not context.get("explicit_location") and plan.get("location"):
            p_loc = str(plan["location"]).strip()
            if p_loc.lower() not in ("null", "none"):
                context["resolved_location"] = p_loc

        selected_tool = plan.get("selected_tool") or "agri_assistant_chat"

        # Deterministic safety guard on tool choice:
        # Never force fertilizer calculator on uncalibrated crops or uncertain growth stage
        if selected_tool == "fertilizer_rules_engine":
            if not context.get("resolved_crop") or not has_verified_crop_rdf(context["resolved_crop"]) or context.get("uncertain_stage"):
                selected_tool = "agri_assistant_chat"

        # Respect explicit knowledge guide searches cleanly
        if re.search(r"\b(search knowledge|knowledge guide|planting depth|handbook)\b", context["original_query"].lower()):
            rag_probe = search_crop_knowledge(context["normalized_query"].lower())
            if rag_probe.source_metadata.get("status") != "not_found":
                selected_tool = "rag_knowledge_tool"

        return selected_tool, context, plan

    def _offline_open_domain_fallback(
        self,
        context: Dict[str, Any],
        stage_overview: Optional[Dict[str, Any]],
        rag_doc: Optional[KnowledgeResult],
    ) -> str:
        """
        Deterministic fallback when Gemini API key is absent / DEMO mode.
        Never returns a generic greeting on a real agricultural question.
        """
        raw = context["original_query"]
        low = context["normalized_query"].lower()
        t_lang = self._template_lang(context["reply_language"])
        t = LANG_TRANSLATIONS[t_lang]

        if nlu.is_pure_greeting(raw):
            return t["greeting"]

        combined_q = f"{raw.lower()} {low}"
        is_pest_or_disease = bool(
            re.search(
                r"\b(curl|curling|thrips|mite|mites|aphid|whitefly|borer|worm|pest|disease|blight|wilt|fungus|virus|spot|spots|yellowing|rot|aaku|aakulu|muduthunnayi|mudatha|tegulu|purugu|keet|keeda|rog)\b",
                combined_q,
            )
            or any(
                tok in raw
                for tok in ("ముడుత", "ముడుచు", "ఆకులు", "ఆకు", "తెగులు", "పురుగు", "తామరపురుగు", "నల్లి", "रोग", "कीट", "पत्ते मुड़")
            )
        )

        # 1. Specific agronomy / livestock / pest / scheme guidance takes priority over crop nutrient fallback
        if "black soil" in low or "regadi" in low:
            return (
                "Black soil (Vertisol) improvement principles:\n"
                "• Incorporate 3–5 tons/acre well-decomposed FYM/compost or green manure (Dhaincha/Sunhemp) to improve structure and aeration.\n"
                "• Provide raised beds or surface drainage channels to avoid waterlogging during heavy rains.\n"
                "• Use shallow mulching to minimize moisture cracks, and get a soil test (pH, EC) before applying Gypsum if sodic/alkaline (pH > 8.5)."
            )
        if any(w in low for w in ("dairy", "cow", "buffalo", "livestock")):
            return (
                "Practical steps to start dairy farming:\n"
                "• Choose climate-adapted breeds (e.g., Murrah buffalo or local crossbred/indigenous cows) and start small (2–5 animals).\n"
                "• Construct a clean, well-ventilated shed with sloped drainage and continuous clean drinking water.\n"
                "• Plan balanced feeding (green fodder + dry roughage + concentrate mineral mixture) and establish preventive vaccination/deworming with a local veterinarian."
            )
        if "rotation" in low:
            return (
                "Proper crop rotation principles:\n"
                "• Alternate heavy nutrient feeders (Tomato, Maize, Rice, Cotton) with nitrogen-fixing legumes (Red Gram, Green Gram, Chickpea).\n"
                "• Avoid planting closely related crops (e.g., Tomato/Chilli/Brinjal/Potato) back-to-back in the same plot to break soil-borne wilt and nematode cycles."
            )
        if any(w in low for w in ("pm-kisan", "pm kisan", "scheme", "subsidy", "eligibility", "installment", "auction")):
            return (
                "For government farmer schemes (such as PM-KISAN, PMFBY crop insurance, or KCC) and live local auction updates, "
                "AgriMind cannot verify real-time beneficiary status or unindexed local dealer/mandi auctions directly. "
                "Please verify current status on official portals (pmkisan.gov.in, pmfby.gov.in, enam.gov.in) or with your local Krishi Vigyan Kendra / Mandal Agriculture Officer."
            )
        if is_pest_or_disease:
            crop_label = context.get("resolved_crop") or "crop"
            if t_lang == "te":
                crop_disp, _ = self._localize_crop_and_stage(crop_label, None, "te")
                return (
                    f"**{crop_disp}** పంటలో ఆకులు ముడుచుకుపోవడం సాధారణంగా రసం పీల్చే పురుగులు (తామరపురుగులు/థ్రిప్స్, తెల్లదోమ లేదా ఎర్రనల్లి) లేదా వైరస్ సమస్య వల్ల వస్తుంది:\n"
                    "• లేత ఆకుల అడుగు భాగాన్ని పరిశీలించండి (ఆకులు పైకి దోనెలా ముడుచుకుంటే తామరపురుగులు/థ్రిప్స్; కిందికి ముడుచుకుంటే నల్లి/మైట్స్ అయ్యే అవకాశం ఎక్కువ).\n"
                    "• ఎకరానికి 10–15 నీలి మరియు పసుపు రంగు జిగురు అట్టలు (sticky traps) పెట్టండి; తీవ్రంగా వైరస్ సోకిన మొక్కలను త్వరగా పీకి నాశనం చేయండి.\n"
                    "• ప్రారంభ నివారణకు వేప నూనె (Neem oil 1500 ppm @ 3–5 ml/లీటర్) లేదా NSKE పిచికారీ చేయండి; అధిక నత్రజని (యూరియా) వాడకాన్ని తగ్గించండి. స్పష్టమైన ఆకు ఫోటో అప్‌లోడ్ చేస్తే Gemini Vision ద్వారా తనిఖీ చేయవచ్చు."
                )
            return (
                f"Leaf curling / pest symptoms in **{crop_label}** are commonly linked to sucking pests (thrips/mites/whiteflies) or viral complex:\n"
                "• Inspect the underside of young leaves carefully (upward cup-shaped curling often indicates thrips; downward curling suggests yellow/broad mites).\n"
                "• Install blue/yellow sticky traps (10–15/acre), remove severely mosaic/stunted plants early, and consider botanical spray such as neem oil (1500 ppm) or NSKE.\n"
                "• Avoid excess nitrogen and overhead stress irrigation; you can also upload a close-up leaf photo in AgriMind for Gemini Vision screening."
            )

        # 2. Crop nutrient overview when crop is known & stage is unknown
        if stage_overview:
            crop_disp, _ = self._localize_crop_and_stage(stage_overview["crop"], None, t_lang)
            stages = stage_overview["stages"]
            lines = []
            for st_key in ("basal", "vegetative", "flowering"):
                st_info = stages.get(st_key)
                if st_info:
                    _, st_disp = self._localize_crop_and_stage(stage_overview["crop"], st_key.capitalize(), t_lang)
                    lines.append(f"• {st_disp} ({st_info['timing']}): {st_info['focus']}")
            stage_bullets = "\n".join(lines)
            if t_lang == "te":
                return (
                    f"**{crop_disp}** పంటకు అవసరమైన పోషకాలు పెరుగుదల దశను బట్టి మారుతాయి (సాధారణ ICAR మార్గదర్శకాలు):\n"
                    f"{stage_bullets}\n\n"
                    f"ఖచ్చితమైన ఎరువుల మోతాదు సూచించడానికి దయచేసి మీ **{crop_disp}** పంట ప్రస్తుతం **ఏ దశలో** ఉంది "
                    f"(మొలక/నాటు, శాఖీయ పెరుగుదల, లేదా పూత/కాయ దశ), నేల రకం మరియు నేల పరీక్ష వివరాలు తెలుపండి."
                )
            if t_lang == "hi":
                return (
                    f"**{crop_disp}** की पोषक तत्व आवश्यकता वृद्धि अवस्था पर निर्भर करती है:\n"
                    f"{stage_bullets}\n\n"
                    f"सटीक मात्रा के लिए कृपया बताएं कि आपकी **{crop_disp}** फसल अभी किस अवस्था में है (बुवाई, वानस्पतिक या फूल/फल) और मिट्टी की जांच रिपोर्ट साझा करें।"
                )
            return (
                f"Nutrient requirements for **{crop_disp}** depend on its current growth stage (general ICAR guidance):\n"
                f"{stage_bullets}\n\n"
                f"To give stage-specific recommendations, please tell me **which growth stage your {crop_disp} crop is currently in** "
                f"(basal/seedling, vegetative, or flowering/fruiting), along with your soil type or soil-test values."
            )

        # 3. Local RAG document hit (skip shallow banner-only matches)
        if (
            rag_doc
            and rag_doc.source_metadata.get("status") != "not_found"
            and rag_doc.relevant_section.strip("= \t\n")
        ):
            return t["knowledge_intro"].format(
                source=rag_doc.source_document,
                section=rag_doc.relevant_section,
                answer=rag_doc.answer,
            )
        if context.get("resolved_crop") and context.get("resolved_stage"):
            return (
                f"Noted that your **{context['resolved_crop']}** crop is in the **{context['resolved_stage']}** stage. "
                f"Would you like stage-specific fertilizer scheduling, FAO-56 irrigation planning, or pest/disease prevention tips for {context['resolved_crop']}?"
            )

        if t_lang == "te":
            return (
                f"మీ వ్యవసాయ ప్రశ్న (\"{raw}\") గురించి మరింత ఖచ్చితమైన సలహా ఇవ్వడానికి దయచేసి పంట రకం, ప్రస్తుత పెరుగుదల దశ లేదా నేల వివరాలను తెలపండి. "
                f"(గమనిక: ప్రస్తుత ఆఫ్‌లైన్ మోడ్‌లో ఉన్నాము; పూర్తి AI సమాధానాల కోసం ఇంటర్నెట్ మరియు LIVE Gemini కనెక్షన్ అవసరం.)"
            )
        if t_lang == "hi":
            return (
                f"आपके कृषि प्रश्न (\"{raw}\") के लिए सटीक मार्गदर्शन देने हेतु कृपया फसल का नाम, वर्तमान अवस्था या मिट्टी का विवरण बताएं। "
                f"(नोट: अभी ऑफ़लाइन मोड सक्रिय है; पूर्ण AI उत्तर के लिए इंटरनेट और LIVE Gemini कनेक्शन आवश्यक है।)"
            )
        return (
            f"Regarding your agricultural question (\"{raw}\"): please share a few more field specifics "
            f"(crop/enterprise, growth stage, soil type, or local conditions) so I can tailor guidance. "
            f"(Note: Currently operating in offline fallback mode; live Gemini connectivity is required for full open-domain AI reasoning.)"
        )

    def _run_selected_tool(
        self,
        selected_tool: str,
        context: Dict[str, Any],
        crop_context: str,
        farm_data: Optional[Dict[str, Any]],
    ) -> Tuple[str, Dict[str, Any], Optional[str], Optional[IrrigationResult], Optional[FertilizerResult], Optional[WeatherResult], Optional[MarketResult], Optional[KnowledgeResult]]:
        """Executes deterministic domain tools with isolated error handling so failures are never masked."""
        crop_name = context.get("resolved_crop") or "Unspecified"
        soil_type = context.get("resolved_soil") or "Loam"
        location = context.get("resolved_location") or "Mandya, India"
        field_area = context.get("field_area") or 1.0
        growth_stage = context.get("resolved_stage") or "basal"

        irrigation_res = None
        fertilizer_res = None
        weather_res = None
        market_res = None
        knowledge_res = None
        payload: Dict[str, Any] = {}
        tool_error: Optional[str] = None

        if selected_tool == "irrigation_rules_engine":
            target_crop = context.get("resolved_crop") or context.get("farm_crop") or "Tomato"
            stage_for_irr = context.get("resolved_stage") or "vegetative"
            try:
                weather_data = get_weather_forecast(location=location)
                temp_c = weather_data.temperature_c
                rain_mm = weather_data.rainfall_mm
            except Exception as w_err:
                logger.warning(f"Weather lookup during irrigation failed cleanly: {w_err}")
                temp_c = None
                rain_mm = None

            try:
                irrigation_res = calculate_irrigation_schedule(
                    crop_name=target_crop,
                    soil_type=soil_type,
                    growth_stage=stage_for_irr,
                    temp_c=temp_c,
                    rainfall_mm=rain_mm,
                    field_area_acres=field_area,
                )
                payload = irrigation_res.model_dump()
            except Exception as exc:
                tool_error = f"Irrigation calculation failed: {exc}"

        elif selected_tool == "fertilizer_rules_engine":
            target_crop = context.get("resolved_crop") or context.get("farm_crop") or "Tomato"
            stage_used = context.get("resolved_stage") or "basal"
            stage_assumed = context.get("resolved_stage") is None
            try:
                fertilizer_res = get_fertilizer_recommendation(
                    crop_name=target_crop,
                    soil_type=soil_type,
                    growth_stage=stage_used,
                    field_area_acres=field_area,
                )
                payload = fertilizer_res.model_dump()
                payload["stage_was_assumed_baseline"] = stage_assumed
            except Exception as exc:
                tool_error = f"Fertilizer calculation failed: {exc}"

        elif selected_tool == "weather_service":
            try:
                weather_res = get_weather_forecast(location=location)
                payload = weather_res.model_dump()
            except Exception as exc:
                tool_error = f"Live weather service unavailable: {exc}"

        elif selected_tool == "mandi_market_lookup":
            target_crop = context.get("resolved_crop") or context.get("farm_crop") or "Tomato"
            try:
                market_res = get_market_prices(commodity=target_crop, state_or_mandi=location)
                payload = market_res.model_dump()
            except Exception as exc:
                tool_error = f"Market price lookup failed: {exc}"

        elif selected_tool == "rag_knowledge_tool":
            try:
                knowledge_res = search_crop_knowledge(context["normalized_query"].lower())
                payload = knowledge_res.model_dump()
            except Exception as exc:
                tool_error = f"Knowledge repository search failed: {exc}"

        elif selected_tool == "farm_management_tool":
            farms_list = (farm_data or {}).get("farms", [])
            payload = {
                "registered_farms_count": len(farms_list),
                "farms": farms_list,
                "active_selected_context": crop_context or "General Farm",
                "soil_type": soil_type,
                "location": location,
            }

        return (
            selected_tool,
            payload,
            tool_error,
            irrigation_res,
            fertilizer_res,
            weather_res,
            market_res,
            knowledge_res,
        )

    def _format_deterministic_tool_reply(
        self,
        selected_tool: str,
        context: Dict[str, Any],
        tool_error: Optional[str],
        irrigation_res: Optional[IrrigationResult],
        fertilizer_res: Optional[FertilizerResult],
        weather_res: Optional[WeatherResult],
        market_res: Optional[MarketResult],
        knowledge_res: Optional[KnowledgeResult],
        payload: Dict[str, Any],
    ) -> str:
        """Deterministic formatting fallback for specialized tools when Gemini synthesis is offline."""
        t_lang = self._template_lang(context["reply_language"])
        t = LANG_TRANSLATIONS[t_lang]

        if tool_error:
            return (
                f"Sorry, the requested tool ({selected_tool}) could not complete right now: {tool_error}. "
                "No estimated numbers were fabricated; please try again shortly or consult your local agricultural office."
            )

        if irrigation_res:
            crop_disp, _ = self._localize_crop_and_stage(irrigation_res.crop, None, t_lang)
            return t["irrigation_intro"].format(
                crop=crop_disp,
                soil=irrigation_res.soil_type,
                water_req=irrigation_res.water_requirement,
                interval=irrigation_res.irrigation_interval,
                action=irrigation_res.recommended_action,
            )
        if fertilizer_res:
            crop_disp, stage_disp = self._localize_crop_and_stage(fertilizer_res.crop, fertilizer_res.growth_stage, t_lang)
            rec_str = ", ".join(fertilizer_res.recommendation)
            base_reply = t["fertilizer_intro"].format(
                crop=crop_disp,
                stage=stage_disp,
                focus=fertilizer_res.nutrient_focus,
                rec=rec_str,
                organic=fertilizer_res.organic_option,
            )
            if payload.get("stage_was_assumed_baseline"):
                note = (
                    "\n\n(గమనిక: పెరుగుదల దశ పేర్కొనకపోవడంతో ప్రాథమిక దశ ఆధారంగా వివరాలు ఇచ్చాము. దయచేసి ప్రస్తుత దశ మరియు మట్టి పరీక్ష వివరాలు తెలిపితే ఖచ్చితమైన సిఫార్సు ఇవ్వగలను.)"
                    if t_lang == "te"
                    else "\n\n(Note: Since no specific growth stage was mentioned, preliminary baseline stage values are shown. Please share your crop's current growth stage and soil test report for tailored guidance.)"
                )
                return base_reply + note
            return base_reply
        if weather_res:
            return t["weather_intro"].format(
                location=weather_res.location,
                temp=weather_res.temperature_c,
                humidity=weather_res.humidity_percent,
                forecast=weather_res.forecast,
                advisory=weather_res.agricultural_advisory,
                source=weather_res.source,
            )
        if market_res:
            return t["market_intro"].format(
                commodity=market_res.commodity,
                mandi=market_res.mandi,
                state=market_res.state,
                modal=market_res.modal_price,
                min=market_res.minimum_price,
                max=market_res.maximum_price,
                trend=market_res.trend,
                advisory=market_res.advisory,
                source=market_res.source,
            )
        if knowledge_res:
            return t["knowledge_intro"].format(
                source=knowledge_res.source_document,
                section=knowledge_res.relevant_section,
                answer=knowledge_res.answer,
            )
        if selected_tool == "farm_management_tool":
            farms_list = payload.get("farms", [])
            farm_names = ", ".join([f.get("name", "Farm") for f in farms_list]) if farms_list else "None registered"
            return (
                f"🌾 **Farm Profile Summary**:\n"
                f"• Registered Holdings: {len(farms_list)} ({farm_names})\n"
                f"• Active Selected Context: {payload.get('active_selected_context')}\n"
                f"• Soil Type: {payload.get('soil_type')} | Location: {payload.get('location')}\n"
                f"You can add or update your fields anytime under the Farm Holdings tab."
            )
        return t["greeting"]

    def process_request(
        self,
        request: ChatRequest,
        image_bytes: Optional[bytes] = None,
        mime_type: str = "image/jpeg",
        crop_context: str = "",
        farm_location: str = "Mandya, India",
        soil_type: str = "Loam",
        field_area: float = 1.0,
        farm_data: Optional[Dict[str, Any]] = None,
    ) -> AgentReturnTuple:
        """
        Orchestrates open-domain multilingual question understanding, hybrid tool routing,
        context management, and accurate answer generation.
        """
        has_image = image_bytes is not None and len(image_bytes) > 0

        # ---------------------------------------------------------------------
        # STEP 0: Input Safety & Pre-Filter Guardrails (keeps open-domain open)
        # ---------------------------------------------------------------------
        is_valid, category, refusal_msg = AgriMindGuardrail.validate_input(request.message, has_image=has_image)
        if not is_valid:
            tool_name = "input_guardrail_refusal" if category == "OFF_TOPIC" else "input_safety_refusal"
            return refusal_msg, tool_name, None, None, None, None, None, None

        # ---------------------------------------------------------------------
        # STEP 1: Resolve Language, Normalization & Conversation Context
        # ---------------------------------------------------------------------
        context = nlu.resolve_context(
            current_message=request.message,
            history=getattr(request, "history", None),
            requested_language=request.language,
            crop_context=crop_context,
            farm_location=farm_location,
            soil_type=soil_type,
            field_area=field_area,
        )
        t_lang = self._template_lang(context["reply_language"])
        t = LANG_TRANSLATIONS[t_lang]

        # ---------------------------------------------------------------------
        # STEP 2: Crop Disease Vision Tool (Image Upload Priority)
        # ---------------------------------------------------------------------
        if has_image:
            assessment = diagnose_crop_disease_with_gemini(
                image_bytes=image_bytes,
                mime_type=mime_type,
                crop_context=crop_context,
                observed_symptoms=request.message,
            )
            reply = t["disease_intro"].format(
                condition=assessment.possible_condition,
                severity=assessment.severity,
                level=assessment.assessment_level,
            )
            return reply, "disease_diagnosis_tool", assessment, None, None, None, None, None

        # ---------------------------------------------------------------------
        # STEP 3: Hybrid Question Understanding & Tool Selection
        # ---------------------------------------------------------------------
        plan = reasoning.plan_agricultural_turn(context)
        selected_tool, context, plan = self._merge_planner_and_context(context, plan)

        if selected_tool == "input_guardrail_refusal":
            refusal = (plan or {}).get("refusal_message") or AgriMindGuardrail.OFF_TOPIC_MESSAGE
            return refusal, "input_guardrail_refusal", None, None, None, None, None, None

        # ---------------------------------------------------------------------
        # STEP 4: Specialized Deterministic Tool Path OR Open-Domain Gemini QA
        # ---------------------------------------------------------------------
        specialized_tools = {
            "irrigation_rules_engine",
            "fertilizer_rules_engine",
            "weather_service",
            "mandi_market_lookup",
            "rag_knowledge_tool",
            "farm_management_tool",
        }

        if selected_tool in specialized_tools:
            (
                tool_used,
                payload,
                tool_error,
                irrigation_res,
                fertilizer_res,
                weather_res,
                market_res,
                knowledge_res,
            ) = self._run_selected_tool(selected_tool, context, crop_context, farm_data)

            # Synthesize verified tool results in target language (or deterministic fallback if offline)
            reply = reasoning.synthesize_tool_response(
                context=context,
                tool_used=tool_used,
                tool_payload=payload,
                tool_error=tool_error,
            )
            if not reply:
                reply = self._format_deterministic_tool_reply(
                    selected_tool=tool_used,
                    context=context,
                    tool_error=tool_error,
                    irrigation_res=irrigation_res,
                    fertilizer_res=fertilizer_res,
                    weather_res=weather_res,
                    market_res=market_res,
                    knowledge_res=knowledge_res,
                    payload=payload,
                )

            if tool_error:
                tool_used = f"{selected_tool}_error"

            return (
                reply,
                tool_used,
                None,
                irrigation_res,
                fertilizer_res,
                weather_res,
                market_res,
                knowledge_res,
            )

        # Open-Domain Agricultural Question Answering (General Reasoning + Reference Context)
        if nlu.is_pure_greeting(request.message) and not (plan and not plan.get("is_pure_greeting", False)):
            return t["greeting"], "agri_assistant_chat", None, None, None, None, None, None

        resolved_crop = context.get("resolved_crop")
        stage_overview = get_stage_nutrient_overview(resolved_crop) if resolved_crop else None
        rag_doc = search_crop_knowledge(context["normalized_query"].lower())

        ref_parts = []
        if stage_overview:
            import json as _json
            ref_parts.append(f"Verified ICAR Stage Nutrient Overview for {stage_overview['crop']}: {_json.dumps(stage_overview, ensure_ascii=False)}")
        if rag_doc and rag_doc.source_metadata.get("status") != "not_found":
            ref_parts.append(f"ICAR/SAU Handbook Excerpt ({rag_doc.source_document} - {rag_doc.relevant_section}): {rag_doc.answer}")
        verified_reference = "\n\n".join(ref_parts) if ref_parts else None

        missing_info = list((plan or {}).get("missing_critical_info") or (plan or {}).get("missing_info") or [])
        if context.get("uncertain_stage") and "growth_stage" not in missing_info:
            missing_info.append("growth_stage")

        norm_query = (plan or {}).get("normalized_english_query") or context["normalized_query"]
        is_live_query = bool((plan or {}).get("is_live_current_info_query", False))

        reply = reasoning.generate_general_agricultural_answer(
            context=context,
            normalized_query=norm_query,
            verified_reference=verified_reference,
            missing_info=missing_info,
            is_live_current_info_query=is_live_query,
        )
        if not reply:
            reply = self._offline_open_domain_fallback(context, stage_overview, rag_doc)

        return reply, "agri_assistant_chat", None, None, None, None, None, None


agent_engine = AgentEngine()
