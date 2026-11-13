import re
from typing import Optional, Tuple, Dict, Any, List


# Word-boundary ASCII & Indic script crop alias lookup -> Canonical English crop name
ASCII_CROP_ALIASES: Dict[str, str] = {
    "tomato": "Tomato",
    "tomatoes": "Tomato",
    "tamata": "Tomato",
    "tamatar": "Tomato",
    "cotton": "Cotton",
    "patti": "Cotton",
    "kapas": "Cotton",
    "rice": "Rice",
    "paddy": "Rice",
    "vari": "Rice",
    "dhaan": "Rice",
    "dhan": "Rice",
    "wheat": "Wheat",
    "godhuma": "Wheat",
    "godhumalu": "Wheat",
    "gehu": "Wheat",
    "gehun": "Wheat",
    "maize": "Maize",
    "corn": "Maize",
    "mokka jonna": "Maize",
    "makka": "Maize",
    "chilli": "Chilli",
    "chili": "Chilli",
    "chillies": "Chilli",
    "mirchi": "Chilli",
    "mirapa": "Chilli",
    "mirch": "Chilli",
    "potato": "Potato",
    "potatoes": "Potato",
    "aloo": "Potato",
    "onion": "Onion",
    "onions": "Onion",
    "ullipaya": "Onion",
    "pyaj": "Onion",
    "pyaz": "Onion",
    "sugarcane": "Sugarcane",
    "sugar cane": "Sugarcane",
    "cheruku": "Sugarcane",
    "ganna": "Sugarcane",
    "soybean": "Soybean",
    "soya": "Soybean",
    "groundnut": "Groundnut",
    "peanut": "Groundnut",
    "verusenaga": "Groundnut",
    "moongfali": "Groundnut",
    "mustard": "Mustard",
    "sarson": "Mustard",
    "mango": "Mango",
    "mamidi": "Mango",
    "aam": "Mango",
    "banana": "Banana",
    "arati": "Banana",
    "kela": "Banana",
    "turmeric": "Turmeric",
    "pasupu": "Turmeric",
    "haldi": "Turmeric",
    "brinjal": "Brinjal",
    "eggplant": "Brinjal",
    "vankaya": "Brinjal",
    "baingan": "Brinjal",
    "okra": "Okra",
    "bhindi": "Okra",
    "bendakaya": "Okra",
    "red gram": "Red Gram",
    "pigeon pea": "Red Gram",
    "arhar": "Red Gram",
    "toor": "Red Gram",
    "kandi": "Red Gram",
    "bengal gram": "Bengal Gram",
    "chickpea": "Bengal Gram",
    "chana": "Bengal Gram",
    "green gram": "Green Gram",
    "moong": "Green Gram",
    "pesara": "Green Gram",
    "pomegranate": "Pomegranate",
    "papaya": "Papaya",
    "coconut": "Coconut",
    "capsicum": "Capsicum",
    "cucumber": "Cucumber",
    "watermelon": "Watermelon",
    "sunflower": "Sunflower",
    "sesame": "Sesame",
    "ragi": "Finger Millet",
    "millet": "Millet",
    "jowar": "Sorghum",
    "bajra": "Pearl Millet",
    "apple": "Apple",
    "grape": "Grape",
    "grapes": "Grape",
    "coffee": "Coffee",
    "tea": "Tea",
    "ginger": "Ginger",
    "garlic": "Garlic",
    "cauliflower": "Cauliflower",
    "cabbage": "Cabbage",
}

INDIC_CROP_ALIASES: List[Tuple[str, str]] = [
    ("టమాటా", "Tomato"), ("టొమాటో", "Tomato"), ("टमाटर", "Tomato"),
    ("పత్తి", "Cotton"), ("कपास", "Cotton"),
    ("వరి", "Rice"), ("ధాన్యం", "Rice"), ("धान", "Rice"), ("चावल", "Rice"),
    ("గోధుమ", "Wheat"), ("गेहूं", "Wheat"), ("गेहूँ", "Wheat"),
    ("మొక్కజొన్న", "Maize"), ("मक्का", "Maize"),
    ("మిర్చి", "Chilli"), ("మిరప", "Chilli"), ("मिर्च", "Chilli"),
    ("బంగాళాదుంప", "Potato"), ("ఆలుగడ్డ", "Potato"), ("आलू", "Potato"),
    ("ఉల్లిపాయ", "Onion"), ("ఉల్లి", "Onion"), ("ప्याज", "Onion"), ("प्याज", "Onion"),
    ("చెరకు", "Sugarcane"), ("गन्ना", "Sugarcane"),
    ("వేరుశెనగ", "Groundnut"), ("మూంగ్‌ఫలి", "Groundnut"), ("मूंगफली", "Groundnut"),
    ("సోయాబీన్", "Soybean"), ("सोयाबीन", "Soybean"),
    ("ఆవాలు", "Mustard"), ("सरसों", "Mustard"),
    ("మామిడి", "Mango"), ("आम", "Mango"),
    ("అరటి", "Banana"), ("केला", "Banana"),
    ("పసుపు", "Turmeric"), ("हल्दी", "Turmeric"),
    ("వంకాయ", "Brinjal"), ("बैंगन", "Brinjal"),
    ("బెండకాయ", "Okra"), ("भिंडी", "Okra"),
    ("కంది", "Red Gram"), ("अरहर", "Red Gram"), ("तूर", "Red Gram"),
    ("శనగ", "Bengal Gram"), ("चना", "Bengal Gram"),
    ("పెసర", "Green Gram"), ("मूंग", "Green Gram"),
    ("దానిమ్మ", "Pomegranate"), ("अनार", "Pomegranate"),
    ("కొబ్బరి", "Coconut"), ("नारियल", "Coconut"),
    ("బొప్పాయి", "Papaya"), ("पपीता", "Papaya"),
]

NON_CROP_AGRI_TOPICS_PATTERN = re.compile(
    r'\b(dairy|milk|milking|cow|cows|buffalo|cattle|livestock|calf|goats?|sheep|poultry|broiler|layer|hen|chicken|duck|'
    r'fish|fishery|fisheries|aquaculture|biofloc|prawn|shrimp|bee|beekeeping|apiculture|honey|sericulture|silkworm|'
    r'tractor|harvester|rotavator|thresher|machinery|polyhouse|greenhouse|shade\s*net|hydroponics|mushroom|'
    r'pm-kisan|pm kisan|subsidy|scheme|loan|kcc|insurance|fasal bima|rythu|black soil|red soil|soil health|'
    r'compost|vermicompost|jeevamrutham|manure|mulching|drip system)\b',
    re.IGNORECASE,
)

# Romanized Telugu & Hinglish cue sets for language detection & normalization
ROMANIZED_TE_MARKERS = {
    "panta", "pantaku", "pantalo", "eruvu", "eruvulu", "poota", "puta", "puvvu", "puvvulu",
    "poshakalu", "mokka", "bhoomi", "bhumi", "nalla", "regadi", "neeru", "neellu", "tadi",
    "tegulu", "purugu", "mandu", "mandulu", "kavali", "cheyali", "veyali", "vadali", "ela",
    "emi", "emiti", "prastutam", "dasha", "dashalo", "dhara", "dharalu", "patti", "mirapa",
    "vankaya", "mamidi", "cheruku", "verusenaga", "tamata", "pantu", "raitu", "rythu",
}

ROMANIZED_HI_MARKERS = {
    "fasal", "kheti", "kisan", "mitti", "khad", "urvarak", "sinchai", "paani", "pani",
    "keeda", "keet", "bimari", "rog", "phool", "fali", "bujai", "buwai", "ropai",
    "kaun", "kaunsa", "kaise", "kitna", "chahiye", "daalna", "dalna", "lagaye", "lagayen",
    "gehun", "dhaan", "kapas", "bhav", "mandi",
}

NORMALIZATION_REPLACEMENTS: List[Tuple[str, str]] = [
    ("టమాటా", "tomato"), ("టొమాటో", "tomato"), ("పత్తి", "cotton"), ("వరి", "rice paddy"),
    ("ధాన్యం", "paddy"), ("గోధుమ", "wheat"), ("మిర్చి", "chilli"), ("మిరప", "chilli"),
    ("మొక్కజొన్న", "maize"), ("వేరుశెనగ", "groundnut"), ("సోయాబీన్", "soybean"),
    ("పూత దశ", "flowering stage"), ("పూతదశ", "flowering stage"), ("పూత", "flowering"),
    ("కాయ దశ", "fruiting stage"), ("పిలక", "tillering"), ("నాటు", "transplanting"),
    ("విత్తనం", "seed sowing"), ("ఎరువులు", "fertilizer"), ("ఎరువు", "fertilizer"),
    ("పోషకాలు", "nutrients"), ("నీరు", "irrigation water"), ("తడి", "irrigation"),
    ("తెగులు", "disease"), ("పురుగు", "pest"), ("నల్ల రేగడి", "black soil"),
    ("నేల", "soil"), ("మట్టి", "soil"), ("వాతావరణం", "weather"), ("ధర", "price"),
    ("टमाटर", "tomato"), ("कपास", "cotton"), ("धान", "rice paddy"), ("गेहूं", "wheat"),
    ("फूल", "flowering"), ("खाद", "fertilizer"), ("उर्वरक", "fertilizer"),
    ("सिंचाई", "irrigation"), ("पानी", "water"), ("मिट्टी", "soil"), ("मौसम", "weather"),
    ("poota", "flowering"), ("puta", "flowering"), ("puvvu", "flower"),
    ("eruvulu", "fertilizer"), ("eruvu", "fertilizer"), ("poshakalu", "nutrients"),
    ("neeru", "irrigation water"), ("tegulu", "disease"), ("purugu", "pest"),
    ("bhoomi", "soil"), ("regadi", "black soil"), ("patti", "cotton"), ("mirchi", "chilli"),
    ("fasal", "crop"), ("khad", "fertilizer"), ("sinchai", "irrigation"), ("mitti", "soil"),
]

DISTRICT_ALIASES: Dict[str, str] = {
    "mandya": "Mandya, India",
    "మండ్య": "Mandya, India",
    "hyderabad": "Hyderabad, India",
    "హైదరాబాద్": "Hyderabad, India",
    "rangareddy": "Rangareddy, India",
    "guntur": "Guntur, India",
    "గుంటూరు": "Guntur, India",
    "warangal": "Warangal, India",
    "వరంగల్": "Warangal, India",
    "vijayawada": "Vijayawada, India",
    "విజయవాడ": "Vijayawada, India",
    "kurnool": "Kurnool, India",
    "కర్నూలు": "Kurnool, India",
    "anantapur": "Anantapur, India",
    "nizamabad": "Nizamabad, India",
    "karimnagar": "Karimnagar, India",
    "khammam": "Khammam, India",
    "nellore": "Nellore, India",
    "karnal": "Karnal, India",
    "khanna": "Khanna, India",
    "rajkot": "Rajkot, India",
    "indore": "Indore, India",
    "nagpur": "Nagpur, India",
    "nashik": "Nashik, India",
    "pune": "Pune, India",
    "varanasi": "Varanasi, India",
    "delhi": "Delhi, India",
    "bengaluru": "Bengaluru, India",
    "bangalore": "Bengaluru, India",
    "hubballi": "Hubballi, India",
    "hubli": "Hubballi, India",
    "kolar": "Kolar, India",
    "davangere": "Davangere, India",
}


def detect_language_and_style(text: str, preferred_language: Optional[str] = "en") -> Tuple[str, str]:
    """
    Detects input language/script style without overwriting original transcript.
    Returns (detected_style, target_reply_lang), where:
      - detected_style in {"te", "hi", "romanized_te", "hinglish", "en"}
      - target_reply_lang in {"te", "hi", "romanized_te", "hinglish", "en"}
    """
    ui_lang = (preferred_language or "en").strip().lower()
    if ui_lang not in ("en", "te", "hi"):
        ui_lang = "en"

    has_te = bool(re.search(r"[\u0C00-\u0C7F]", text or ""))
    has_hi = bool(re.search(r"[\u0900-\u097F]", text or ""))

    if has_te:
        return "te", (ui_lang if ui_lang in ("te", "hi") else "te")
    if has_hi:
        return "hi", (ui_lang if ui_lang in ("te", "hi") else "hi")

    tokens = set(re.findall(r"[a-z]+", (text or "").lower()))
    te_hits = len(tokens & ROMANIZED_TE_MARKERS)
    hi_hits = len(tokens & ROMANIZED_HI_MARKERS)

    if te_hits >= 2 or (te_hits >= 1 and bool(tokens & {"ela", "emi", "kavali", "cheyali", "veyali", "vadali", "panta", "eruvu", "eruvulu", "poota", "poshakalu"})):
        return "romanized_te", ("te" if ui_lang == "te" else "romanized_te")
    if hi_hits >= 2 or (hi_hits >= 1 and bool(tokens & {"kaise", "kitna", "kaunsa", "chahiye", "dalna", "lagaye", "fasal", "khad", "sinchai"})):
        return "hinglish", ("hi" if ui_lang == "hi" else "hinglish")

    return "en", ui_lang


def normalize_for_reasoning(text: str) -> str:
    """Produces a non-destructive normalized English hint string for downstream matching/RAG."""
    norm = (text or "").strip()
    for src, dst in NORMALIZATION_REPLACEMENTS:
        if src in norm or src in norm.lower():
            norm = re.sub(re.escape(src), f" {dst} ", norm, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", norm).strip()


def extract_crop(text: str, crop_context: str = "", allow_farm_context: bool = False) -> Optional[str]:
    """
    Extracts an explicitly mentioned crop using multilingual aliases and word-boundary matching.
    Returns None instead of silently guessing 'Tomato' when absent.
    """
    raw = text or ""
    low = raw.lower()

    # Check longest Indic script phrases first
    for alias, canonical in sorted(INDIC_CROP_ALIASES, key=lambda x: len(x[0]), reverse=True):
        if alias in raw:
            return canonical

    # Check word-boundary ASCII / Romanized aliases (longest first for multi-word names)
    for alias in sorted(ASCII_CROP_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", low):
            return ASCII_CROP_ALIASES[alias]

    if allow_farm_context and crop_context and "crop:" in crop_context.lower():
        match = re.search(r"crop:\s*([^\(\,\.;\n]+)", crop_context, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if candidate and candidate.lower() not in ("unspecified", "none", "general"):
                return candidate

    return None


def extract_growth_stage(text: str) -> Optional[str]:
    """
    Extracts growth stage across English, Telugu, Hindi, and Romanized expressions.
    Returns None when growth stage is omitted or uncertain.
    """
    raw = text or ""
    low = raw.lower()

    # Check Indic script stages directly (substring safe for Telugu/Hindi morphology)
    te_flowering = ("పూత", "పుష్ప", "పిందె", "కాయ దశ", "కంకి")
    hi_flowering = ("फूल", "पुष्पन", "फल ", "फल-", "फली", "बाली", "बॉल")
    if any(k in raw for k in te_flowering) or any(k in raw for k in hi_flowering):
        return "flowering"

    en_flowering = (
        r"\b(flower|flowering|bloom|blooming|blossom|fruit|fruiting|fruit set|panicle|heading|boll|tassel|tasseling|silking|booting|pod|podding)\b|"
        r"\b(poota|puta|puvvu|puvvulu|phool)\b"
    )
    if re.search(en_flowering, low):
        return "flowering"

    te_basal = ("నాటు", "నాట్లు", "విత్తన", "విత్తు", "నారు", "దుక్కి")
    hi_basal = ("बुवाई", "रोपाई", "नर्सरी")
    if any(k in raw for k in te_basal) or any(k in raw for k in hi_basal):
        return "basal"

    en_basal = r"\b(basal|seed|seedling|sow|sowing|nursery|transplant|transplanting|planting|initial|pre-sowing|germination|naatu|vittanam|naru|buwai|ropai)\b"
    if re.search(en_basal, low):
        return "basal"

    te_veg = ("ఎదుగుదల", "పిలక", "పెరుగుదల")
    hi_veg = ("वानस्पतिक", "कल्ले", "बढ़वार")
    if any(k in raw for k in te_veg) or any(k in raw for k in hi_veg):
        return "vegetative"

    en_veg = r"\b(vegetative|tillering|tiller|branching|squaring|square formation|knee-high|canopy growth|edugudala|pilaka)\b"
    if re.search(en_veg, low):
        return "vegetative"

    te_late = ("కోత", "పక్వ")
    hi_late = ("कटाई", "पकने", "तुड़ाई")
    if any(k in raw for k in te_late) or any(k in raw for k in hi_late):
        return "late_season"

    en_late = r"\b(harvest|harvesting|matur\w*|ripen\w*|late[- ]season|kota|katai)\b"
    if re.search(en_late, low):
        return "late_season"

    return None


def has_uncertain_stage_reference(text: str) -> bool:
    """True when the user mentions 'current / this stage' without specifying which stage."""
    if extract_growth_stage(text) is not None:
        return False
    raw = text or ""
    low = raw.lower()
    if any(t in raw for t in ("ప్రస్తుతం", "ప్రస్తుత దశ", "ఈ దశలో", "ఇప్పుడు", "अभी", "इस अवस्था", "वर्तमान अवस्था")):
        return True
    return bool(re.search(r"\b(at this stage|this stage|current stage|currently|right now|nowadays|prastutam|ee dasha|abhi)\b", low))


def extract_soil_type(text: str, default_soil: Optional[str] = None) -> Optional[str]:
    """Extracts explicitly named soil types across English, Telugu, Hindi, and Romanized terms."""
    raw = text or ""
    low = raw.lower()
    if "నల్ల రేగడి" in raw or "నల్ల మట్టి" in raw or "काली मिट्टी" in raw or re.search(r"\b(black cotton soil|black soil|black clay|vertisol|regadi)\b", low):
        return "Black Clay"
    if "ఎర్ర నేల" in raw or "ఎర్ర మట్టి" in raw or "लाल मिट्टी" in raw or re.search(r"\b(red soil|red sandy|red loam)\b", low):
        return "Red Sandy"
    if re.search(r"\bclay loam\b", low):
        return "Clay Loam"
    if re.search(r"\b(sandy loam|sandy soil|sand)\b", low) or "ఇసుక" in raw or "रेतीली" in raw:
        return "Sandy"
    if re.search(r"\b(clay soil|clay)\b", low) or "బంక మట్టి" in raw or "चिकनी मिट्टी" in raw:
        return "Clay"
    if re.search(r"\b(silt|silty)\b", low):
        return "Silt"
    if re.search(r"\b(loam|loamy|alluvial)\b", low) or "दोमट" in raw:
        return "Loam"
    return default_soil


def extract_location(text: str, default_location: Optional[str] = "Mandya, India") -> Optional[str]:
    """Extracts district/city mentions cleanly without letting unrelated words override farm default."""
    raw = text or ""
    low = raw.lower()
    for key, formatted in DISTRICT_ALIASES.items():
        if key.isascii():
            if re.search(rf"\b{re.escape(key)}\b", low):
                return formatted
        else:
            if key in raw:
                return formatted
    return default_location


def is_pure_greeting(text: str) -> bool:
    """Returns True ONLY for actual standalone greetings with no substantive question."""
    low = re.sub(r"[!.,?]+", "", (text or "").strip().lower())
    greetings = {
        "hi", "hello", "hey", "namaste", "namaskaram", "vanakkam", "good morning",
        "good afternoon", "good evening", "hii", "hlo",
        "నమస్కారం", "హలో", "హాయ్", "नमस्ते", "हेलो", "हाय", "प्रणाम",
    }
    return low in greetings


def _is_non_crop_topic_query(text: str) -> bool:
    """Detects livestock/dairy/beekeeping/fisheries/machinery/schemes/soil topics where a crop shouldn't hijack."""
    return bool(NON_CROP_AGRI_TOPICS_PATTERN.search(text or "")) and extract_crop(text) is None


def _is_contextual_follow_up(text: str) -> bool:
    """Detects whether the current query relies on prior conversation turns (anaphora or short continuation)."""
    raw = (text or "").strip()
    low = raw.lower()
    if extract_crop(raw) is not None or _is_non_crop_topic_query(raw):
        return False
    follow_up_cues = (
        r"\b(it|its|this crop|that crop|same crop|this stage|that stage|above|earlier|previous|now|next|"
        r"how much|which fertilizer|which nutrient|how often|how frequently|what about|what else|why|dose|dosage)\b|"
        r"\b(daaniki|daniki|ippudu|em cheyali|em veyali|ise|ab|kitna)\b"
    )
    if re.search(follow_up_cues, low):
        return True
    if any(t in raw for t in ("దీనికి", "దానికి", "ఇప్పుడు", "అదే", "ఇది", "ఏమి వేయాలి", "एवं", "इसमें", "इसके", "अब")):
        return True
    return len(low.split()) <= 5


def _mentions_user_farm_or_crop(text: str) -> bool:
    raw = text or ""
    low = raw.lower()
    if re.search(r"\b(my farm|my crop|my field|my land|this farm|farm profile|my holding|my harvest)\b", low):
        return True
    if any(t in raw for t in ("నా పొలం", "నా పంట", "మా పొలం", "मेरी फसल", "मेरे खेत", "मेरा खेत")):
        return True
    return False


def format_history_for_prompt(history: Optional[List[Any]], max_turns: int = 6) -> str:
    """Formats recent non-greeting conversation turns safely for Gemini reasoning prompts."""
    if not history:
        return "None"
    lines: List[str] = []
    for turn in history[-max_turns:]:
        role = getattr(turn, "role", None) if not isinstance(turn, dict) else turn.get("role")
        content = getattr(turn, "content", None) if not isinstance(turn, dict) else turn.get("content")
        if not content or not str(content).strip():
            continue
        label = "Farmer" if str(role).lower() in ("user", "farmer") else "Assistant"
        snippet = str(content).strip()
        if len(snippet) > 450:
            snippet = snippet[:447] + "..."
        lines.append(f"{label}: {snippet}")
    return "\n".join(lines) if lines else "None"


def resolve_context(
    current_message: str,
    history: Optional[List[Any]] = None,
    requested_language: Optional[str] = "en",
    crop_context: str = "",
    farm_location: str = "Mandya, India",
    soil_type: str = "Loam",
    field_area: float = 1.0,
) -> Dict[str, Any]:
    """
    Resolves structured agricultural context strictly prioritizing:
      1. Current user question (always primary; explicit crop/stage/soil/location overrides everything)
      2. Recent conversation history (only for genuine follow-up questions with no topic switch)
      3. Farm/crop cadastral context (only as background or when user references their farm/crop)
    """
    detected_style, reply_language = detect_language_and_style(current_message, requested_language)
    normalized_query = normalize_for_reasoning(current_message)

    explicit_crop = extract_crop(current_message, crop_context="", allow_farm_context=False)
    explicit_stage = extract_growth_stage(current_message)
    explicit_soil = extract_soil_type(current_message, default_soil=None)
    explicit_location = extract_location(current_message, default_location=None)
    non_crop_topic = _is_non_crop_topic_query(current_message)
    follow_up = _is_contextual_follow_up(current_message)

    history_crop: Optional[str] = None
    history_stage: Optional[str] = None
    history_soil: Optional[str] = None
    history_location: Optional[str] = None

    if history and follow_up and not non_crop_topic:
        # Walk backwards from most recent user turn first, then assistant turns
        for turn in reversed(history[-6:]):
            t_role = getattr(turn, "role", None) if not isinstance(turn, dict) else turn.get("role")
            t_content = getattr(turn, "content", "") if not isinstance(turn, dict) else turn.get("content", "")
            t_crop = getattr(turn, "crop", None) if not isinstance(turn, dict) else turn.get("crop")
            t_stage = getattr(turn, "growth_stage", None) if not isinstance(turn, dict) else turn.get("growth_stage")
            if not t_content:
                continue

            # Stop inheriting earlier topic if recent user turn explicitly asked a non-crop topic
            if str(t_role).lower() in ("user", "farmer") and _is_non_crop_topic_query(t_content):
                break

            if not history_crop:
                history_crop = t_crop or extract_crop(t_content)
            if not history_stage:
                history_stage = t_stage or extract_growth_stage(t_content)
            if not history_soil:
                history_soil = extract_soil_type(t_content)
            if not history_location:
                history_location = extract_location(t_content, default_location=None)
            if history_crop and history_stage:
                break

    mentions_farm = _mentions_user_farm_or_crop(current_message)
    farm_crop = extract_crop("", crop_context=crop_context, allow_farm_context=True) if crop_context else None

    # Precedence rules
    resolved_crop = explicit_crop
    if not resolved_crop and follow_up and not non_crop_topic:
        resolved_crop = history_crop
    if not resolved_crop and mentions_farm and not non_crop_topic:
        resolved_crop = farm_crop

    resolved_stage = explicit_stage
    if not resolved_stage and follow_up and not non_crop_topic:
        # Inherit stage from recent history ONLY if resolved_crop matches or no new crop switched
        if not explicit_crop or (history_crop and explicit_crop == history_crop):
            resolved_stage = history_stage

    resolved_soil = explicit_soil or history_soil or (soil_type or "Loam")
    resolved_location = explicit_location or history_location or (farm_location or "Mandya, India")

    return {
        "original_query": current_message,
        "normalized_query": normalized_query,
        "detected_style": detected_style,
        "reply_language": reply_language,
        "explicit_crop": explicit_crop,
        "resolved_crop": resolved_crop,
        "farm_crop": farm_crop,
        "explicit_stage": explicit_stage,
        "resolved_stage": resolved_stage,
        "uncertain_stage": has_uncertain_stage_reference(current_message) and resolved_stage is None,
        "resolved_soil": resolved_soil,
        "explicit_soil": explicit_soil,
        "resolved_location": resolved_location,
        "explicit_location": explicit_location,
        "field_area": field_area or 1.0,
        "crop_context_raw": crop_context,
        "is_follow_up": follow_up,
        "mentions_farm": mentions_farm,
        "non_crop_topic": non_crop_topic,
        "history_text": format_history_for_prompt(history),
    }

