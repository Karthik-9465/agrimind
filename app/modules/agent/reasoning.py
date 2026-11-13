import json
import logging
import time
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, field_validator

from app.config import settings

logger = logging.getLogger("agrimind.reasoning")

VALID_PLANNER_TOOLS = (
    "fertilizer_rules_engine",
    "irrigation_rules_engine",
    "weather_service",
    "mandi_market_lookup",
    "rag_knowledge_tool",
    "farm_management_tool",
    "agri_assistant_chat",
)

VALID_RESPONSE_LANGUAGES = ("en", "te", "hi", "romanized_te", "hinglish")
VALID_GROWTH_STAGES = ("basal", "vegetative", "flowering", "late_season")


class PlannerDecision(BaseModel):
    """Strict schema for Gemini semantic NLU & tool-routing planner output."""

    is_agricultural: bool = True
    is_pure_greeting: bool = False
    refusal_message: Optional[str] = None
    response_language: Literal["en", "te", "hi", "romanized_te", "hinglish"] = "en"
    normalized_english_query: str = ""
    selected_tool: Literal[
        "fertilizer_rules_engine",
        "irrigation_rules_engine",
        "weather_service",
        "mandi_market_lookup",
        "rag_knowledge_tool",
        "farm_management_tool",
        "agri_assistant_chat",
    ] = "agri_assistant_chat"
    crop: Optional[str] = None
    growth_stage: Optional[Literal["basal", "vegetative", "flowering", "late_season"]] = None
    soil_type: Optional[str] = None
    location: Optional[str] = None
    missing_critical_info: List[str] = Field(default_factory=list)
    is_live_current_info_query: bool = False

    @field_validator("response_language", mode="before")
    @classmethod
    def _coerce_language(cls, v: Any) -> str:
        s = str(v or "en").strip().lower()
        return s if s in VALID_RESPONSE_LANGUAGES else "en"

    @field_validator("selected_tool", mode="before")
    @classmethod
    def _coerce_tool(cls, v: Any) -> str:
        s = str(v or "agri_assistant_chat").strip()
        return s if s in VALID_PLANNER_TOOLS else "agri_assistant_chat"

    @field_validator("growth_stage", mode="before")
    @classmethod
    def _coerce_stage(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip().lower()
        if s in ("", "null", "none", "unknown", "unspecified"):
            return None
        if s in ("bloom", "fruit", "fruiting", "boll", "panicle", "reproductive"):
            return "flowering"
        if s in ("seedling", "sowing", "initial"):
            return "basal"
        return s if s in VALID_GROWTH_STAGES else None

    @field_validator("crop", "soil_type", "location", "refusal_message", mode="before")
    @classmethod
    def _clean_nullable_str(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return None if not s or s.lower() in ("null", "none", "n/a", "unknown") else s

    @field_validator("missing_critical_info", mode="before")
    @classmethod
    def _clean_missing_list(cls, v: Any) -> List[str]:
        if isinstance(v, list):
            return [str(item).strip() for item in v if item is not None and str(item).strip()]
        if isinstance(v, str) and v.strip():
            return [v.strip()]
        return []


def is_gemini_live_enabled() -> bool:
    """Returns True only when Gemini is in LIVE mode with a non-placeholder API key."""
    return settings.get_gemini_mode() != "DEMO" and bool(settings.get_gemini_api_key())


def _extract_clean_json(raw_text: str) -> Dict[str, Any]:
    """Strips optional markdown code fences or stray wrapper prose and parses a JSON object."""
    cleaned = (raw_text or "").strip()
    if not cleaned:
        raise ValueError("Empty JSON response")

    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].rsplit("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].rsplit("```", 1)[0].strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx == -1 or end_idx <= start_idx:
            raise
        parsed = json.loads(cleaned[start_idx : end_idx + 1])

    if not isinstance(parsed, dict):
        raise ValueError(f"Expected JSON object for planner, got {type(parsed).__name__}")
    return parsed


def validate_planner_payload(raw_or_dict: Any) -> Optional[Dict[str, Any]]:
    """
    Validates raw JSON text or dict from Gemini against PlannerDecision.
    Returns validated dict or None when empty, malformed, incomplete, or unexpected.
    """
    if raw_or_dict is None:
        return None
    try:
        if isinstance(raw_or_dict, PlannerDecision):
            return raw_or_dict.model_dump()
        if isinstance(raw_or_dict, dict):
            # Require core routing indicator so arbitrary unrelated dicts are rejected cleanly
            if "selected_tool" not in raw_or_dict and "is_agricultural" not in raw_or_dict:
                logger.warning("Gemini planner dict missing required keys ('selected_tool' / 'is_agricultural').")
                return None
            return PlannerDecision.model_validate(raw_or_dict).model_dump()
        if isinstance(raw_or_dict, str):
            parsed = _extract_clean_json(raw_or_dict)
            if "selected_tool" not in parsed and "is_agricultural" not in parsed:
                logger.warning("Gemini planner JSON missing required keys ('selected_tool' / 'is_agricultural').")
                return None
            return PlannerDecision.model_validate(parsed).model_dump()
    except Exception as exc:
        logger.warning(f"Failed to validate Gemini planner output ({exc}); falling back cleanly.")
        return None
    return None


def _language_instruction(target_language: str) -> str:
    """Maps resolved target language code to clear generation instructions."""
    mapping = {
        "te": "Write the complete response in clear, natural Telugu (తెలుగు script), using simple farmer-friendly terminology.",
        "hi": "Write the complete response in clear, natural Hindi (देवनागरी / हिन्दी), using simple farmer-friendly terminology.",
        "romanized_te": (
            "Write the response in natural, easy-to-read Romanized Telugu (Telugu written in English letters, "
            "matching the farmer's Telugu-English style) with key agronomic terms clearly explained."
        ),
        "hinglish": (
            "Write the response in natural Hinglish (Hindi written clearly in Roman/English letters mixed with simple "
            "English farming terms) matching the user's style."
        ),
        "en": "Write the response in clear, practical, farmer-friendly English.",
    }
    return mapping.get(target_language, mapping["en"])


def _extract_response_text_and_reason(response: Any) -> tuple[Optional[str], Optional[str], Optional[Any]]:
    """Safely extracts response text, candidate finish_reason, and structured parsed payload."""
    parsed_obj = getattr(response, "parsed", None)
    finish_reason = None
    candidates = getattr(response, "candidates", None) or []
    candidate_parts_text: List[str] = []

    if candidates:
        cand0 = candidates[0]
        raw_reason = getattr(cand0, "finish_reason", None)
        finish_reason = str(raw_reason) if raw_reason is not None else None
        content = getattr(cand0, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            if getattr(part, "thought", False):
                continue
            p_text = getattr(part, "text", None)
            if isinstance(p_text, str) and p_text:
                candidate_parts_text.append(p_text)

    if parsed_obj is not None:
        if isinstance(parsed_obj, BaseModel):
            return json.dumps(parsed_obj.model_dump(), ensure_ascii=False), finish_reason, parsed_obj
        if isinstance(parsed_obj, dict):
            return json.dumps(parsed_obj, ensure_ascii=False), finish_reason, parsed_obj

    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip(), finish_reason, None

    if candidate_parts_text:
        joined = "".join(candidate_parts_text).strip()
        if joined:
            return joined, finish_reason, None

    return None, finish_reason, None


def _generate_gemini_text(
    prompt: str,
    temperature: float = 0.2,
    max_output_tokens: int = 1200,
    expect_json: bool = False,
    response_schema: Optional[Any] = None,
    thinking_budget: Optional[int] = None,
) -> Optional[str]:
    """
    Executes a Google Gemini text or schema-constrained JSON generation call via google-genai SDK.
    Inspects candidate finish_reason, avoids thinking-token starvation on JSON planning,
    and never logs credentials or raw API keys. Returns None cleanly on unavailable/transient failure.
    """
    if not is_gemini_live_enabled():
        return None

    api_key = settings.get_gemini_api_key()
    model_name = settings.get_gemini_model()

    try:
        import os
        import google.genai as genai
        from google.genai import types
    except Exception as imp_err:
        logger.warning(f"google-genai SDK unavailable: {imp_err}")
        return None

    try:
        timeout_ms = max(4000, min(int(os.getenv("GEMINI_TEXT_TIMEOUT_MS", "15000")), 60000))
    except ValueError:
        timeout_ms = 15000

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=timeout_ms),
    )

    def _build_config(use_schema: bool) -> Any:
        cfg_kwargs: Dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        if expect_json:
            cfg_kwargs["response_mime_type"] = "application/json"
            if use_schema and response_schema is not None:
                cfg_kwargs["response_schema"] = response_schema
        if thinking_budget is not None and hasattr(types, "ThinkingConfig"):
            cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
        return types.GenerateContentConfig(**cfg_kwargs)

    use_schema = bool(expect_json and response_schema is not None)
    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            config = _build_config(use_schema=use_schema)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            text, finish_reason, _ = _extract_response_text_and_reason(response)
            if finish_reason and "MAX_TOKENS" in finish_reason.upper():
                logger.warning(
                    f"Gemini generation reached finish_reason={finish_reason} "
                    f"(expect_json={expect_json}, max_output_tokens={max_output_tokens}, chars={len(text or '')})."
                )
                if expect_json:
                    # Reject truncated JSON unless valid schema parses cleanly below
                    try:
                        _extract_clean_json(text or "")
                    except Exception:
                        logger.warning("Discarding truncated JSON response caused by MAX_TOKENS.")
                        return None

            if text and text.strip():
                return text.strip()
            logger.warning(f"Gemini text generation returned empty text (finish_reason={finish_reason}).")
            return None
        except Exception as exc:
            err_msg = str(exc)
            err_lower = err_msg.lower()

            # If model/endpoint rejects response_schema specifically, retry once with JSON mime type only
            if use_schema and any(k in err_lower for k in ("response_schema", "schema", "400", "invalid_argument")):
                logger.warning(f"Gemini rejected response_schema ({err_msg[:120]}); retrying with MIME-only JSON.")
                use_schema = False
                continue

            is_auth_err = any(
                k in err_lower
                for k in ("api_key_invalid", "api key not valid", "permission_denied", "401", "403")
            )
            is_quota_exhausted = any(
                k in err_lower
                for k in ("exceeded your current quota", "quota exceeded")
            )
            is_network_offline = any(
                k in err_lower
                for k in (
                    "getaddrinfo",
                    "nameresolutionerror",
                    "no such host",
                    "failed to resolve",
                    "server disconnected",
                    "eof occurred",
                    "timed out",
                    "timeout",
                )
            )
            if is_auth_err or is_quota_exhausted or is_network_offline:
                reason_tag = "auth" if is_auth_err else ("quota_exhausted" if is_quota_exhausted else "network/offline")
                logger.warning(f"Gemini text call aborted early ({reason_tag}): {err_msg[:120]}")
                return None

            is_transient = any(
                k in err_lower
                for k in ("503", "unavailable", "429", "resource_exhausted")
            )
            if is_transient and attempt < max_attempts:
                logger.warning(f"Gemini text call transient failure (attempt {attempt}), retrying...")
                time.sleep(0.8)
                continue

            logger.warning(f"Gemini text call failed without crash: {err_msg[:160]}")
            return None
    return None


def plan_agricultural_turn(context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Uses Gemini structured output (schema-constrained JSON + zero thinking budget to prevent
    output-token truncation) to understand any multilingual farmer query, prioritize current
    question over history, validate against PlannerDecision schema, and route cleanly.
    Returns validated dict or None when Gemini is offline/DEMO or returns unusable output.
    """
    if not is_gemini_live_enabled():
        return None

    prompt = f"""You are the NLU & Tool-Routing Planner for AgriMind AI (Indian Smart Agriculture Assistant).
Analyze the FARMER'S CURRENT QUESTION carefully. The CURRENT QUESTION is ALWAYS the primary input.

INPUTS:
- Current User Message (ORIGINAL): "{context['original_query']}"
- Normalized Hint (reference only): "{context['normalized_query']}"
- UI Language Setting: "{context['reply_language']}" (detected input style: "{context['detected_style']}")
- Recent Conversation History (use ONLY for genuine follow-up questions; NEVER let old crops/topics override the current question):
{context['history_text']}
- Optional Background Farm Profile (lowest priority; NEVER override explicit crop/soil/location in Current User Message):
  farm_crop="{context.get('farm_crop') or 'None'}", soil="{context.get('resolved_soil')}", location="{context.get('resolved_location')}"

AVAILABLE TOOLS (pick ONE):
1. "fertilizer_rules_engine" -> ONLY when ALL hold:
   - User asks about fertilizers/nutrients/NPK/Urea/DAP/MOP for a specific crop in {{Tomato, Rice, Wheat, Cotton, Maize, Chilli}}, AND
   - Growth stage is EXPLICITLY known (from current message or direct follow-up), OR user explicitly asks what fertilizers to apply to that crop overall.
   - IMPORTANT: Do NOT select this if the user says "at this stage" / "ప్రస్తుతం" / "current stage" without naming a stage! Route that to "agri_assistant_chat" so we ask for the growth stage instead of guessing. Do NOT select for general soil improvement (e.g. black soil reclamation).
2. "irrigation_rules_engine" -> When user asks for crop irrigation/water requirement, drip schedule, or watering interval.
3. "weather_service" -> When user asks about weather, rain, temperature, humidity, wind, or spraying weather window.
4. "mandi_market_lookup" -> When user asks about crop/commodity market prices, mandi rates, or bhav.
5. "rag_knowledge_tool" -> ONLY when user explicitly asks to search the local cultivation guide/handbook for Tomato, Cotton, Chilli, Rice, Wheat, or Maize planting depth/spacing/handbook practices.
6. "farm_management_tool" -> When user specifically asks to view/summarize their saved AgriMind farm profile, holdings, or acreage.
7. "agri_assistant_chat" -> Use for ALL open-domain agricultural questions across ANY subject (crop cultivation, black/red/alkaline soil improvement, seeds, pests/diseases without photos, weeds, water harvesting, organic/natural farming, horticulture, dairy/livestock, poultry, fisheries, beekeeping, sericulture, tractors/machinery, greenhouses/polyhouse, storage, post-harvest, agri-economics, government schemes like PM-KISAN/KCC, climate-smart farming, multi-stage nutrient questions when stage is unknown, or follow-ups).

CRITICAL RULES:
- Agriculture domain includes crops, horticulture, soil, water, livestock/dairy, poultry, fisheries, bees, silkworms, machinery, markets, farmer schemes, agri-tech, rural livelihoods, and any follow-up to the farm chat. Never reject an unfamiliar farming topic.
- Reject ONLY clearly unrelated non-agricultural queries (software coding, crypto/stocks, movies/sports, consumer electronics, politics, fiction) with is_agricultural=false and a polite refusal_message mentioning being AgriMind AI, a specialized agricultural assistant, in the response_language.
- Multilingual stage accuracy: Telugu "పూత", "పూత దశ", Hindi "फूल", "पुष्पन", English "flower/bloom/fruit/boll/panicle", Romanized "poota/puta/puvvu" MUST map to "flowering" (NEVER "vegetative"). If NO stage is stated and not carried from immediate follow-up, return null.
- Crop precedence: If Current User Message names Cotton / పత్తి / कपास while History or Background mentions Tomato, "crop" MUST be "Cotton". For non-crop topics (dairy farming, beekeeping, general soil improvement), set "crop": null.
- Respond in response_language="{context['reply_language']}" unless input script clearly requires another listed code."""

    raw = _generate_gemini_text(
        prompt,
        temperature=0.1,
        max_output_tokens=768,
        expect_json=True,
        response_schema=PlannerDecision,
        thinking_budget=0,
    )
    if not raw:
        return None
    return validate_planner_payload(raw)


def generate_general_agricultural_answer(
    context: Dict[str, Any],
    normalized_query: Optional[str] = None,
    verified_reference: Optional[str] = None,
    missing_info: Optional[List[str]] = None,
    is_live_current_info_query: bool = False,
) -> Optional[str]:
    """
    Generates an open-domain, scientifically grounded, multilingual agricultural answer via Gemini.
    Never invents dosages or real-time market/scheme facts; asks specific clarifying questions
    when field details are missing.
    """
    if not is_gemini_live_enabled():
        return None

    lang_rule = _language_instruction(context["reply_language"])
    missing_str = ", ".join(missing_info) if missing_info else "None flagged"
    ref_block = f"\nVERIFIED REFERENCE DATA (incorporate faithfully without altering numbers):\n{verified_reference}\n" if verified_reference else ""

    farm_bg = (
        f"Selected Farm Background (apply ONLY if relevant to the current question; do NOT let it override explicit topics/crops): "
        f"Crop={context.get('farm_crop') or 'None'}, Soil={context.get('resolved_soil')}, Location={context.get('resolved_location')}"
    )

    prompt = f"""You are AgriMind AI, a senior Indian agricultural scientist and extension agronomist helping a farmer.

CURRENT FARMER QUESTION (PRIMARY FOCUS — answer THIS question directly):
"{context['original_query']}"
Normalized English Meaning: "{normalized_query or context['normalized_query']}"

RECENT CONVERSATION HISTORY (use ONLY for follow-up continuity; NEVER override explicit crops/topics in the current question):
{context['history_text']}

{farm_bg}
{ref_block}
Potentially Missing Context: {missing_str}
Requires Real-Time External Data Outside Local Tools: {is_live_current_info_query}

LANGUAGE REQUIREMENT:
{lang_rule}

STRICT AGRONOMIC & SAFETY RULES:
1. Answer ANY legitimate agricultural or allied-farming question directly (crops, soils, organic farming, pests/diseases, horticulture, livestock/dairy, poultry, fisheries, beekeeping, sericulture, machinery, greenhouses, post-harvest, economics, farmer schemes, agri-tech). Do NOT output a generic welcome greeting.
2. Context discipline: If the current question asks about Cotton, Dairy Farming, or Black Soil, answer strictly about THAT — never inject Tomato or an unrelated previous turn. If the current question is a follow-up ("Which fertilizer should I apply now?"), seamlessly use the recent turn's crop/stage.
3. Agricultural safety & accuracy:
   - Do NOT invent unsupported numerical chemical pesticide concentrations, spray ml/liter dosages, or unverified exact fertilizer quantities for crops lacking verified calculations. Give sound nutrient/management principles and recommend checking label/ICAR/state university advisories or soil test reports for exact doses.
   - Distinguish clearly between general guidance and field-specific prescriptions (which depend on crop variety, growth stage, soil type, soil-test N-P-K/pH values, local weather, and prior applications).
   - If critical information (such as current growth stage, soil test, or symptoms) is missing and materially changes the recommendation, provide helpful stage-wise/general guidance AND ask 1–2 concise, specific clarifying questions!
   - If asked for live/real-time external data you do not have (such as today's live unindexed mandi auction rates, PM-KISAN installment payout dates, or real-time beneficiary eligibility), clearly state that you cannot verify live external status/rates and point to official sources (eNAM, Agmarknet, pmkisan.gov.in, local KVK/Mandi gate) rather than guessing numbers.
4. Keep the answer practical, clearly structured with short bullet points where helpful, and easy for a farmer to act on."""

    return _generate_gemini_text(
        prompt,
        temperature=0.3,
        max_output_tokens=1800,
        expect_json=False,
        thinking_budget=256,
    )


def synthesize_tool_response(
    context: Dict[str, Any],
    tool_used: str,
    tool_payload: Dict[str, Any],
    tool_error: Optional[str] = None,
) -> Optional[str]:
    """
    Synthesizes verified deterministic tool results (or honest tool-failure notices)
    into natural farmer-friendly explanations in the target language without altering verified values.
    """
    if not is_gemini_live_enabled():
        return None

    lang_rule = _language_instruction(context["reply_language"])
    payload_json = json.dumps(tool_payload, ensure_ascii=False, default=str)

    hint_note = ""
    if context["reply_language"] == "hi" and tool_used == "irrigation_rules_engine":
        hint_note = "- Naturally include Hindi phrases like 'सिंचाई' and 'जल आवश्यकता' when presenting the water requirement.\n"
    elif context["reply_language"] == "te" and tool_used == "fertilizer_rules_engine":
        hint_note = "- Naturally include Telugu crop/fertilizer terms like 'ఎరువుల' and the crop name (e.g., 'టమాటా' if Tomato).\n"

    error_section = (
        f"\nTOOL EXECUTION FAILURE NOTICE: The tool '{tool_used}' failed with error: {tool_error}. "
        "Do NOT fabricate a tool result! Honestly inform the farmer that the live lookup failed right now and give safe general guidance where helpful."
        if tool_error
        else ""
    )

    prompt = f"""You are AgriMind AI explaining verified agronomic tool output to a farmer.

FARMER'S ORIGINAL QUESTION:
"{context['original_query']}"

TOOL EXECUTED: {tool_used}
VERIFIED TOOL DATA (use ONLY these exact numbers, units, crops, growth stages, and caveats — NEVER alter or invent figures):
{payload_json}
{error_section}

LANGUAGE REQUIREMENT:
{lang_rule}

INSTRUCTIONS:
- Address the farmer's exact question directly using the verified data above.
- Include key actionable numbers, growth stage (note: if 'Flowering', state flowering/పూత దశ accurately — never call it vegetative), organic option, and any disclaimer/caveats (for example, if 'is_demo_data' is true for market data, note it is a benchmark dataset; if soil test values weren't supplied for fertilizer, note preliminary baseline status and invite soil test / pH details).
{hint_note}- Keep the tone practical, concise, and clear (short structured bullets)."""

    return _generate_gemini_text(
        prompt,
        temperature=0.2,
        max_output_tokens=1200,
        expect_json=False,
        thinking_budget=0,
    )

