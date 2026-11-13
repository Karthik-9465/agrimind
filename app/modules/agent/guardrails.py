import re
from typing import Tuple


class AgriMindGuardrail:
    """
    Input safety and open-domain relevance guardrails for AgriMind AI Agent.
    Blocks harmful/injection prompts and clear unrelated off-topic spam, while allowing
    any legitimate or unfamiliar agricultural, livestock, soil, rural, or follow-up question
    across English, Telugu, Hindi, and Romanized regional dialects.
    """

    # Unsafe / Harmful content & prompt injection patterns
    UNSAFE_PATTERNS = [
        r'\b(bomb|weapon|explosive|hack|malware|virus|exploit|jailbreak|ignore previous|ignore system|dan mode|bypass|override system)\b',
        r'\b(suicide|self-harm|illegal drug|cocaine|meth|stolen credit card)\b',
        r'\b(poison human|harm someone|make poison|lethal dose for human)\b',
    ]

    # Strong agricultural domain signals (do not include ambiguous commerce words like 'market' or 'prices')
    AGRI_SIGNAL_PATTERNS = [
        r'\b(crop|crops|farm|farmer|farming|field|soil|plant|planting|seed|seeds|seedling|harvest|irrigation|water|watering|moisture|drip|sprinkler)\b',
        r'\b(fertilizer|npk|urea|dap|mop|nitrogen|phosphorus|potassium|potash|compost|vermicompost|manure|nutrient|nutrients|yield|pesticide|fungicide|herbicide)\b',
        r'\b(disease|blight|fungus|fungal|rot|rust|wilt|pest|pests|insect|insects|worm|aphids|whitefly|lesion|spot|spots|diagnosis|diagnose|weed|weeds)\b',
        r'\b(weather|rain|rainfall|temperature|humidity|drought|forecast|monsoon)\b',
        r'\b(mandi|apmc|agmarknet|quintal|commodity|msp|enam)\b',
        r'\b(tomato|potato|rice|paddy|wheat|maize|corn|cotton|sugarcane|onion|chilli|soybean|groundnut|mustard|apple|mango|banana|turmeric|pulse|millet)\b',
        r'\b(agrimind|agronomy|agronomist|agriculture|agricultural|horticulture|floriculture|sericulture|apiculture|aquaculture|fisheries)\b',
        r'\b(livestock|cattle|dairy|milk|cow|buffalo|goat|sheep|poultry|hen|broiler|beekeeping|honey|bee|tractor|rotavator|greenhouse|polyhouse|hydroponic)\b',
        r'\b(pm-kisan|pm kisan|subsidy|crop insurance|fasal bima|kcc|kisan|rythu|organic|jeevamrutham|mulch|mulching|biofloc|fodder|silage)\b',
        # Romanized Telugu / Hindi agriculture roots
        r'\b(panta|pantaku|eruvu|eruvulu|poota|poshakalu|bhoomi|regadi|neeru|tegulu|purugu|patti|mirchi|tamata|fasal|kheti|mitti|khad|sinchai|paani)\b',
        # Indic script presence (Telugu or Devanagari)
        r'[\u0C00-\u0C7F\u0900-\u097F]',
    ]

    # Explicit non-agricultural off-topic patterns (only enforced when no strong agri signal is present)
    OFF_TOPIC_PATTERNS = [
        r'\b(python scraper|write python|coding tutorial|c\+\+|javascript|react component|html layout|web scraper|sql injection tutorial)\b',
        r'\b(stock market|crypto|bitcoin|ethereum|option trading|wall street|forex|invest in stock)\b',
        r'\b(movie script|hollywood|bollywood gossip|write a story|essay on sports|nfl|nba|football match|cricket score)\b',
        r'\b(election campaign|political party|vote for)\b',
    ]

    OFF_TOPIC_MESSAGE = (
        "I am AgriMind AI, your specialized agricultural assistant. "
        "I can assist with farming, crops, soil health, livestock/dairy, irrigation, fertilizers, "
        "pests, weather, agricultural schemes, and Mandi market topics. "
        "Please ask an agriculture-related question!"
    )

    @classmethod
    def has_agricultural_signal(cls, text: str) -> bool:
        """Non-blocking helper to detect strong agricultural domain cues."""
        low = (text or "").lower()
        return any(re.search(pat, low) for pat in cls.AGRI_SIGNAL_PATTERNS)

    @classmethod
    def validate_input(cls, text: str, has_image: bool = False) -> Tuple[bool, str, str]:
        """
        Validates input query safety and filters clear off-topic non-agricultural spam.
        Unfamiliar or open-domain questions without explicit off-topic patterns are permitted
        so semantic reasoning can handle any agricultural topic or follow-up turn.
        """
        if not text or not text.strip():
            if has_image:
                return True, "SAFE_AGRICULTURAL", ""
            return False, "OFF_TOPIC", "Please provide a query or upload a crop photo for diagnosis."

        text_lower = text.lower().strip()

        # 1. Unsafe Content / Prompt Injection Check
        for pattern in cls.UNSAFE_PATTERNS:
            if re.search(pattern, text_lower):
                return False, "UNSAFE_PROMPT", (
                    "I am sorry, but I cannot process this request as it violates AgriMind "
                    "safety and security policies."
                )

        # 2. Image attachment bypasses text off-topic checks
        if has_image:
            return True, "SAFE_AGRICULTURAL", ""

        # 3. Block explicit unrelated off-topic triggers unless strong agricultural context is present
        if not cls.has_agricultural_signal(text):
            for pattern in cls.OFF_TOPIC_PATTERNS:
                if re.search(pattern, text_lower):
                    return False, "OFF_TOPIC", cls.OFF_TOPIC_MESSAGE

        # Do NOT block unfamiliar agricultural questions using a static keyword allowlist!
        return True, "SAFE_AGRICULTURAL", ""
