import re
from typing import Tuple

class AgriMindGuardrail:
    """
    Input safety and domain relevance guardrails for AgriMind AI Agent.
    Enforces safety policies and prevents non-agricultural off-topic queries.
    """

    # Unsafe / Harmful content & prompt injection patterns
    UNSAFE_PATTERNS = [
        r'\b(bomb|weapon|explosive|hack|malware|virus|exploit|jailbreak|ignore previous|ignore system|dan mode|bypass|override system)\b',
        r'\b(suicide|self-harm|illegal drug|cocaine|meth|stolen credit card)\b'
    ]

    # Whitelisted domain keywords (agricultural context)
    AGRI_KEYWORDS = [
        r'\b(crop|farm|farmer|farming|field|soil|plant|planting|seed|seedling|harvest|irrigation|water|watering|moisture|drip|sprinkler)\b',
        r'\b(fertilizer|npk|urea|dap|mop|nitrogen|phosphorus|potassium|compost|manure|nutrient|nutrients|yield|pesticide|fungicide)\b',
        r'\b(disease|blight|fungus|fungal|rot|rust|wilt|pest|pests|bug|insects|worm|aphids|whitefly|lesion|spot|spots|diagnosis|diagnose)\b',
        r'\b(weather|rain|rainfall|temperature|humidity|wind|cloud|sunny|drought|climate|forecast)\b',
        r'\b(price|prices|mandi|apmc|market|rate|rates|cost|quintal|commodity|sell|buy crops)\b',
        r'\b(tomato|potato|rice|wheat|maize|corn|cotton|sugarcane|onion|chilli|soybean|groundnut|mustard|apple|mango|banana)\b',
        r'\b(guide|handbook|practices|cultivation|spacing|depth|sowing|loam|clay|sandy|ph|acidity|alkalinity)\b',
        r'\b(agrimind|agronomy|agronomist|agriculture|agritech|livestock|cattle|poultry)\b'
    ]

    # Explicit off-topic non-agricultural triggers
    OFF_TOPIC_PATTERNS = [
        r'\b(python scraper|write python|coding tutorial|c\+\+|javascript|react component|html layout)\b',
        r'\b(stock market|crypto|bitcoin|option trading|wall street|forex|invest in stock)\b',
        r'\b(movie script|hollywood|write a story|poetry|sing a song|essay on sports|nfl|nba|football match)\b',
        r'\b(president|election|political party|prime minister|politics)\b'
    ]

    @classmethod
    def validate_input(cls, text: str, has_image: bool = False) -> Tuple[bool, str, str]:
        """
        Validates input query.
        Returns tuple of (is_valid: bool, category: str, refusal_message: str).
        Categories: "SAFE_AGRICULTURAL", "UNSAFE_PROMPT", "OFF_TOPIC".
        """
        if not text or not text.strip():
            # Empty text with image is valid for image analysis
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

        # 2. Image attachment automatically bypasses text off-topic checks (since leaf photo is attached)
        if has_image:
            return True, "SAFE_AGRICULTURAL", ""

        # 3. Explicit Off-Topic Trigger Check
        for pattern in cls.OFF_TOPIC_PATTERNS:
            if re.search(pattern, text_lower):
                return False, "OFF_TOPIC", (
                    "I am AgriMind AI, your specialized agricultural assistant. "
                    "I can only assist with farming, crop health, irrigation, fertilizer guidance, weather forecasts, and Mandi market prices. "
                    "Please ask a farming-related question!"
                )

        # 4. Keyword relevance check: check if any agricultural keyword matches
        is_agri_related = any(re.search(pat, text_lower) for pat in cls.AGRI_KEYWORDS)

        # Allow general greetings & short general agronomy questions
        is_greeting_or_short = len(text_lower.split()) <= 4 or text_lower in ["hi", "hello", "hey", "help", "good morning", "good evening"]

        if not is_agri_related and not is_greeting_or_short:
            return False, "OFF_TOPIC", (
                "I am AgriMind AI, your specialized agricultural assistant. "
                "I can only assist with farming, crop health, irrigation, fertilizer guidance, weather forecasts, and Mandi market prices. "
                "Please ask a farming-related question!"
            )

        return True, "SAFE_AGRICULTURAL", ""
