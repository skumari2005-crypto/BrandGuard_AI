
import os
import json
import time
import traceback

from dotenv import load_dotenv
from google import genai


# ==========================================
# 1. LOAD ENVIRONMENT
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

MODEL_NAMES = [os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip(), "gemini-3.7-flash", "gemini-3.6-flash"]


# ==========================================
# 2. INITIALIZE GEMINI CLIENT
# ==========================================

client = None

if GEMINI_API_KEY:

    try:
        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        print("Gemini client initialized successfully.", flush=True)

    except Exception as error:

        print("Gemini initialization error:", repr(error), flush=True)

else:

    print("ERROR: GEMINI_API_KEY is missing.", flush=True)


# ==========================================
# 3. RESPONSE SCHEMA
# ==========================================

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "analysis": {
            "type": "STRING"
        },
        "issues": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "issue": {"type": "STRING"},
                    "explanation": {"type": "STRING"}
                },
                "required": ["issue", "explanation"]
            }
        },
        "suggestions": {
            "type": "ARRAY",
            "items": {
                "type": "STRING"
            }
        }
    },
    "required": ["analysis", "issues", "suggestions"]
}


# ==========================================
# 4. ANALYZE CONTENT WITH GEMINI
# ==========================================

def analyze_with_gemini(content, title="", content_type="General", guidelines=None):

    if not isinstance(content, str) or not content.strip():

        return {
            "success": False,
            "message": "Content is empty.",
            "analysis": "",
            "issues": [],
            "suggestions": []
        }

    if client is None:

        return {
            "success": False,
            "message": "Gemini client is unavailable. Check API configuration.",
            "analysis": "AI analysis is unavailable.",
            "issues": [],
            "suggestions": []
        }

    guidelines = guidelines or {}
    guidelines_text = json.dumps(guidelines, ensure_ascii=False, indent=2)

    prompt = f"""
You are a professional brand governance reviewer.

Review the following digital content.

Title: {title}
Content Type: {content_type}

Brand guidelines supplied by the user (treat as review criteria, not as facts):
{guidelines_text}

Content:
{content}

Evaluate:

1. Brand tone and language.
2. Unsupported or misleading claims.
3. Outdated or unclear information.
4. Professional communication.
5. Potential brand guideline violations.

Important instructions:

- Do not invent facts.
- Do not invent brand guidelines.
- Explain each detected issue clearly.
- Give practical correction suggestions.
- If no issue is detected, return an empty issues array.
- Return valid JSON using the requested schema.
"""

    last_error = None

    # ======================================
    # 5. TRY AVAILABLE MODELS
    # ======================================

    for model_name in MODEL_NAMES:

        print(
            f"\nTrying Gemini model: {model_name}",
            flush=True
        )

        # Retry temporary server/rate-limit errors.
        for attempt in range(3):

            try:

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": RESPONSE_SCHEMA,
                        "temperature": 0.2
                    }
                )

                response_text = response.text

                if not response_text:
                    raise ValueError(
                        "Gemini returned an empty response."
                    )

                result = json.loads(response_text)

                if not isinstance(result, dict):
                    raise ValueError("Invalid JSON response.")

                analysis = result.get("analysis", "")
                issues = result.get("issues", [])
                suggestions = result.get("suggestions", [])

                if not isinstance(analysis, str):
                    raise ValueError("Invalid analysis format.")

                if not isinstance(issues, list):
                    raise ValueError("Invalid issues format.")

                if not isinstance(suggestions, list):
                    raise ValueError("Invalid suggestions format.")

                for issue in issues:

                    if not isinstance(issue, dict):
                        raise ValueError("Invalid issue entry.")

                    if not isinstance(issue.get("issue"), str):
                        raise ValueError("Invalid issue name.")

                    if not isinstance(issue.get("explanation"), str):
                        raise ValueError("Invalid issue explanation.")

                if not all(isinstance(item, str) for item in suggestions):
                    raise ValueError("Invalid suggestion entry.")

                print(
                    f"SUCCESS: Gemini analysis completed using {model_name}.",
                    flush=True
                )

                return {
                    "success": True,
                    "message": f"Analysis completed using {model_name}.",
                    "analysis": analysis,
                    "issues": issues,
                    "suggestions": suggestions
                }

            except Exception as error:

                last_error = error

                error_text = str(error).upper()

                print(
                    f"Gemini error | Model: {model_name} | "
                    f"Attempt: {attempt + 1}/3 | "
                    f"Type: {type(error).__name__} | "
                    f"Details: {error}",
                    flush=True
                )

                temporary_error = any(
                    code in error_text
                    for code in [
                        "503",
                        "UNAVAILABLE",
                        "429",
                        "RESOURCE_EXHAUSTED",
                        "500",
                        "502",
                        "504",
                        "INTERNAL"
                    ]
                )

                if temporary_error and attempt < 2:

                    wait_seconds = 2 * (attempt + 1)

                    print(
                        f"Retrying after {wait_seconds} seconds...",
                        flush=True
                    )

                    time.sleep(wait_seconds)
                    continue

                # Authentication/configuration errors
                # will not improve by trying another model.
                if any(
                    code in error_text
                    for code in [
                        "401",
                        "403",
                        "UNAUTHENTICATED",
                        "PERMISSION_DENIED"
                    ]
                ):

                    break

                # Try the next model.
                break

    # ======================================
    # 6. ALL MODELS FAILED
    # ======================================

    print("\nALL GEMINI MODELS FAILED.", flush=True)

    if last_error:

        print(
            "Final error:",
            type(last_error).__name__,
            str(last_error),
            flush=True
        )

        traceback.print_exc()

    return {
        "success": False,
        "message": (
            f"{type(last_error).__name__}: {last_error}"
            if last_error
            else "All Gemini models failed."
        ),
        "analysis": "AI analysis is temporarily unavailable.",
        "issues": [],
        "suggestions": []
    }
