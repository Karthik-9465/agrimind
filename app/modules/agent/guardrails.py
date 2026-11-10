import re
from typing import Tuple

class AgriMindGuardrail:
    """
    Input safety and domain relevance guardrails for AgriMind AI Agent.
    Enforces safety policies and prevents non-agricultural off-topic queries.
    Supports English, Telugu (తెలుగు), and Hindi (हिन्दी) agricultural vocabularies.
    """

    # Unsafe / Harmful content & prompt injection patterns
    UNSAFE_PATTERNS = [
        r'\b(bomb|weapon|explosive|hack|malware|virus|exploit|jailbreak|ignore previous|ignore system|dan mode|bypass|override system)\b',
        r'\b(suicide|self-harm|illegal drug|cocaine|meth|stolen credit card)\b'
    ]

    # Whitelisted domain keywords (English agricultural context)
    AGRI_KEYWORDS_EN = [
        r'\b(crop|farm|farmer|farming|field|soil|plant|planting|seed|seedling|harvest|irrigation|water|watering|moisture|drip|sprinkler)\b',
        r'\b(fertilizer|npk|urea|dap|mop|nitrogen|phosphorus|potassium|compost|manure|nutrient|nutrients|yield|pesticide|fungicide)\b',
        r'\b(disease|blight|fungus|fungal|rot|rust|wilt|pest|pests|bug|insects|worm|aphids|whitefly|lesion|spot|spots|diagnosis|diagnose)\b',
        r'\b(weather|rain|rainfall|temperature|humidity|wind|cloud|sunny|drought|climate|forecast)\b',
        r'\b(price|prices|mandi|apmc|market|rate|rates|cost|quintal|commodity|sell|buy crops)\b',
        r'\b(tomato|potato|rice|paddy|wheat|maize|corn|cotton|sugarcane|onion|chilli|soybean|groundnut|mustard|apple|mango|banana)\b',
        r'\b(guide|handbook|practices|cultivation|spacing|depth|sowing|loam|clay|sandy|ph|acidity|alkalinity|rotation)\b',
        r'\b(agrimind|agronomy|agronomist|agriculture|agritech|livestock|cattle|poultry)\b'
    ]

    # Telugu (తెలుగు) Agricultural Domain Keywords
    AGRI_KEYWORDS_TE = [
        r'(పంట|పంటలు|వ్యవసాయం|రైతు|భూమి|నేల|మట్టి|విత్తనం|నాటు|కోత|సాగు|నీరు|నీటి|తడి|డ్రిప్)',
        r'(ఎరువు|ఎరువులు|యూరియా|డిఎపి|పోటాష్|నత్రజని|భాస్వరం|సేంద్రీయ|పురుగు|మందు|తెగులు|వ్యాధి|మచ్చ|తెగుళ్లు)',
        r'(వాతావరణం|వర్షం|ఎండ|ఉష్ణోగ్రత|తేమ|గాలి|ధర|ధరలు|మార్కెట్|మండి|క్వింటాల్|రేటు|టమాటా|వరి|గోధుమ|పత్తి|మిర్చి|మొక్కజొన్న)'
    ]

    # Hindi (हिन्दी) Agricultural Domain Keywords
    AGRI_KEYWORDS_HI = [
        r'(फसल|खेती|किसान|खेत|मिट्टी|बीज|बुवाई|कटाई|सिंचाई|पानी|नमी|ड्रिप|फव्वारा)',
        r'(उर्वरक|खाद|यूरिया|डीएपी|पोटाश|नाइट्रोजन|फास्फोरस|जैविक|कीटनाशक|रोग|बीमारी|धब्बा|कीट|इल्ली)',
        r'(मौसम|बारिश|वर्षा|तापमान|आर्द्रता|हवा|मंडी|भाव|दाम|मूल्य|क्विंटल|टमाटर|धान|गेहूं|कपास|मिर्च|मक्का)'
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

        # 2. Image attachment automatically bypasses text off-topic checks
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

        # 4. Keyword relevance check across English, Telugu, and Hindi
        is_agri_en = any(re.search(pat, text_lower) for pat in cls.AGRI_KEYWORDS_EN)
        is_agri_te = any(re.search(pat, text) for pat in cls.AGRI_KEYWORDS_TE)
        is_agri_hi = any(re.search(pat, text) for pat in cls.AGRI_KEYWORDS_HI)

        is_agri_related = is_agri_en or is_agri_te or is_agri_hi

        # Allow general greetings & short general agronomy questions
        is_greeting_or_short = len(text_lower.split()) <= 4 or text_lower in ["hi", "hello", "hey", "help", "good morning", "good evening"]

        # Check for Indian non-ASCII scripts (Telugu / Devanagari)
        has_indic_script = bool(re.search(r'[\u0C00-\u0C7F\u0900-\u097F]', text))

        if not is_agri_related and not is_greeting_or_short and not has_indic_script:
            return False, "OFF_TOPIC", (
                "I am AgriMind AI, your specialized agricultural assistant. "
                "I can only assist with farming, crop health, irrigation, fertilizer guidance, weather forecasts, and Mandi market prices. "
                "Please ask a farming-related question!"
            )

        return True, "SAFE_AGRICULTURAL", ""
