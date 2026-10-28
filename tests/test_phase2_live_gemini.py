import os
import sys
import io
import pytest
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.modules.agent.tools.disease import diagnose_crop_disease_with_gemini

def test_live_gemini_vision_call():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\nGEMINI_API_KEY is not set in environment. Skipping live API call test.")
        return

    img = Image.new("RGB", (200, 200), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    image_bytes = buf.getvalue()

    assessment = diagnose_crop_disease_with_gemini(
        image_bytes=image_bytes,
        mime_type="image/jpeg",
        crop_context="Tomato leaf"
    )

    assert assessment.possible_condition != ""
    assert assessment.assessment_level in ["Likely", "Possible", "Uncertain"]
    assert assessment.is_mock is False
    print("\nLive Gemini Vision Output:")
    print("Condition:", assessment.possible_condition)
    print("Level:", assessment.assessment_level)
    print("Symptoms:", assessment.symptoms)

if __name__ == "__main__":
    test_live_gemini_vision_call()
