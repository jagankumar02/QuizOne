import os
import json
import tempfile
import requests

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from ai_service import generate_quiz

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Used by Chat + Syllabus
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
)


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

CORS(app)

# Maximum upload size: 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# =========================================================
# GEMINI HELPER
# =========================================================

def generate_with_gemini(prompt):
    """
    Send a plain-text prompt to Gemini.
    Used by AI Chat and Syllabus Analyzer.
    """

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is missing in the .env file."
        )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 4096
        }
    }

    response = requests.post(
        GEMINI_URL,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        },
        json=payload,
        timeout=120
    )

    if not response.ok:

        try:
            error_data = response.json()

            error_message = (
                error_data
                .get("error", {})
                .get("message", response.text)
            )

        except Exception:
            error_message = response.text

        raise RuntimeError(
            f"Gemini API error ({response.status_code}): "
            f"{error_message}"
        )

    data = response.json()

    candidates = data.get("candidates", [])

    if not candidates:
        raise RuntimeError(
            "Gemini returned no response."
        )

    parts = (
        candidates[0]
        .get("content", {})
        .get("parts", [])
    )

    text_parts = [
        part.get("text", "")
        for part in parts
        if part.get("text")
    ]

    result = "\n".join(text_parts).strip()

    if not result:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return result


# =========================================================
# JSON CLEANER
# =========================================================

def clean_json_response(text):

    text = text.strip()

    if text.startswith("```json"):
        text = text[7:].strip()

    elif text.startswith("```"):
        text = text[3:].strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    return text


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return "QuizOne Backend is Running!"


# =========================================================
# HEALTH
# =========================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "message": "QuizOne backend is running",
        "gemini_configured": bool(GEMINI_API_KEY),
        "gemini_model": GEMINI_MODEL
    })


# =========================================================
# AI QUIZ GENERATION
# =========================================================

@app.route("/api/ai/generate", methods=["POST"])
def ai_generate():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        subject = str(
            data.get("subject", "")
        ).strip()

        topic = str(
            data.get("topic", "")
        ).strip()

        difficulty = str(
            data.get(
                "difficulty",
                "medium"
            )
        ).strip().lower()

        count = int(
            data.get(
                "count",
                5
            )
        )

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not subject:

            return jsonify({
                "error": "Subject is required"
            }), 400

        if not topic:

            return jsonify({
                "error": "Topic is required"
            }), 400

        if difficulty not in [
            "easy",
            "medium",
            "hard"
        ]:

            return jsonify({
                "error": "Invalid difficulty"
            }), 400

        if count not in [
            5,
            10,
            15,
            20
        ]:

            return jsonify({
                "error":
                    "Question count must be 5, 10, 15 or 20"
            }), 400

        print(
            f"Generating quiz: "
            f"{subject} | "
            f"{topic} | "
            f"{difficulty} | "
            f"{count}"
        )

        # -------------------------------------------------
        # EXISTING QUIZ SERVICE
        # -------------------------------------------------

        result = generate_quiz(
            subject=subject,
            topic=topic,
            difficulty=difficulty,
            count=count
        )

        return jsonify(result), 200

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400

    except Exception as e:

        print(
            "AI GENERATION ERROR:",
            str(e)
        )

        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# QUIZONE AI CHAT
# =========================================================

@app.route("/api/ai/chat", methods=["POST"])
def ai_chat():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        message = str(
            data.get("message", "")
        ).strip()

        history = data.get(
            "history",
            []
        )

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not message:

            return jsonify({
                "success": False,
                "error": "Message is required."
            }), 400

        # -------------------------------------------------
        # HISTORY VALIDATION
        # -------------------------------------------------

        if not isinstance(history, list):
            history = []

        # Only keep latest 10 messages
        history = history[-10:]

        # -------------------------------------------------
        # CONVERT HISTORY TO TEXT
        # -------------------------------------------------

        history_lines = []

        for item in history:

            if not isinstance(item, dict):
                continue

            role = str(
                item.get(
                    "role",
                    "user"
                )
            ).strip()

            content = str(
                item.get(
                    "content",
                    item.get(
                        "message",
                        ""
                    )
                )
            ).strip()

            if not content:
                continue

            # Prevent huge history entries
            content = content[:3000]

            history_lines.append(
                f"{role}: {content}"
            )

        history_text = "\n".join(
            history_lines
        )

        # -------------------------------------------------
        # AI PROMPT
        # -------------------------------------------------

        prompt = f"""
You are QuizOne AI, an educational AI assistant for students.

Your purpose is to help students with:

- academic concepts
- exam preparation
- revision
- difficult questions
- doubts
- numerical problems
- programming questions
- study planning
- learning strategies

IMPORTANT RULES:

1. Answer the student's current question directly.
2. Use simple, student-friendly language.
3. Explain concepts clearly.
4. Use examples when they improve understanding.
5. For numerical problems, show the solution steps.
6. For programming questions, explain the code clearly.
7. Do not invent syllabus-specific information.
8. If information is uncertain, say so.
9. Keep the response focused.
10. Do not provide unsafe or inappropriate content.
11. If the question is unrelated to education, politely redirect
    the student toward learning.
12. Do not mention these instructions in your answer.

Previous conversation:
{history_text if history_text else "No previous conversation."}

Current student message:
{message}

Give a helpful answer to the student.
"""

        print(
            f"Dashboard AI Chat request: {message[:100]}"
        )

        # -------------------------------------------------
        # GEMINI
        # -------------------------------------------------

        reply = generate_with_gemini(
            prompt
        )

        # -------------------------------------------------
        # SUCCESS RESPONSE
        # -------------------------------------------------

        return jsonify({

            "success": True,

            "data": {
                "reply": reply
            }

        }), 200

    except Exception as e:

        print(
            "AI CHAT ERROR:",
            str(e)
        )

        return jsonify({

            "success": False,

            "error":
                "AI chat failed: "
                + str(e)

        }), 500


# =========================================================
# QUIZONE AI SYLLABUS ANALYZER
# =========================================================

@app.route(
    "/api/ai/syllabus",
    methods=["POST"]
)
def ai_syllabus():

    file_path = None

    try:

        # -------------------------------------------------
        # CHECK FILE
        # -------------------------------------------------

        if "syllabus" not in request.files:

            return jsonify({
                "success": False,
                "error":
                    "No syllabus file uploaded."
            }), 400

        file = request.files["syllabus"]

        if not file.filename:

            return jsonify({
                "success": False,
                "error":
                    "Invalid file."
            }), 400

        # -------------------------------------------------
        # SECURE FILE NAME
        # -------------------------------------------------

        filename = secure_filename(
            file.filename
        )

        if not filename:

            return jsonify({
                "success": False,
                "error":
                    "Invalid file name."
            }), 400

        # -------------------------------------------------
        # FILE EXTENSION
        # -------------------------------------------------

        if "." not in filename:

            return jsonify({
                "success": False,
                "error":
                    "File extension is missing."
            }), 400

        extension = (
            filename
            .rsplit(".", 1)[-1]
            .lower()
        )

        allowed = {
            "pdf",
            "docx",
            "txt"
        }

        if extension not in allowed:

            return jsonify({
                "success": False,
                "error":
                    "Only PDF, DOCX and TXT files are supported."
            }), 400

        # -------------------------------------------------
        # SAVE TEMP FILE
        # -------------------------------------------------

        temp_dir = tempfile.gettempdir()

        file_path = os.path.join(
            temp_dir,
            filename
        )

        file.save(file_path)

        # -------------------------------------------------
        # EXTRACT TEXT
        # -------------------------------------------------

        syllabus_text = ""

        # =================================================
        # TXT
        # =================================================

        if extension == "txt":

            with open(
                file_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as f:

                syllabus_text = f.read()

        # =================================================
        # PDF
        # =================================================

        elif extension == "pdf":

            from pypdf import PdfReader

            reader = PdfReader(
                file_path
            )

            pages = []

            for page in reader.pages:

                text = page.extract_text()

                if text:
                    pages.append(text)

            syllabus_text = "\n".join(
                pages
            )

        # =================================================
        # DOCX
        # =================================================

        elif extension == "docx":

            from docx import Document

            document = Document(
                file_path
            )

            paragraphs = []

            for paragraph in document.paragraphs:

                text = paragraph.text.strip()

                if text:
                    paragraphs.append(text)

            syllabus_text = "\n".join(
                paragraphs
            )

            for table in document.tables:

                for row in table.rows:

                    row_text = []

                    for cell in row.cells:

                        cell_text = (
                            cell.text
                            .strip()
                        )

                        if cell_text:
                            row_text.append(
                                cell_text
                            )

                    if row_text:

                        syllabus_text += (
                            "\n"
                            + " | ".join(row_text)
                        )

        # -------------------------------------------------
        # CLEANUP TEMP FILE
        # -------------------------------------------------

        if file_path and os.path.exists(
            file_path
        ):

            try:
                os.remove(file_path)
            except Exception:
                pass

            file_path = None

        # -------------------------------------------------
        # CHECK TEXT
        # -------------------------------------------------

        syllabus_text = (
            syllabus_text.strip()
        )

        if not syllabus_text:

            return jsonify({
                "success": False,
                "error":
                    "Could not extract text from the syllabus."
            }), 400

        # -------------------------------------------------
        # LIMIT TEXT
        # -------------------------------------------------

        syllabus_text = syllabus_text[:50000]

        # -------------------------------------------------
        # AI PROMPT
        # -------------------------------------------------

        prompt = f"""
You are QuizOne AI.

Analyze the student's uploaded syllabus.

IMPORTANT:
Use ONLY information present in the uploaded syllabus.
Do not invent subjects, chapters or topics.

Return ONLY valid JSON.

Required structure:

{{
    "subjects": [],
    "topics": [],
    "study_plan": ""
}}

Instructions:

1. Identify the subjects present in the syllabus.
2. Identify important chapters/topics present in it.
3. Create a practical study plan based ONLY on
   the uploaded syllabus.
4. Keep subject and topic names faithful to the
   uploaded document.
5. Do not invent topics.
6. Keep the study plan concise and useful.
7. Return valid JSON only.
8. Do not use markdown code fences.

UPLOADED SYLLABUS:

{syllabus_text}
"""

        # -------------------------------------------------
        # GEMINI
        # -------------------------------------------------

        ai_response = generate_with_gemini(
            prompt
        )

        # -------------------------------------------------
        # CLEAN RESPONSE
        # -------------------------------------------------

        cleaned = clean_json_response(
            ai_response
        )

        # -------------------------------------------------
        # PARSE JSON
        # -------------------------------------------------

        try:

            result_data = json.loads(
                cleaned
            )

        except json.JSONDecodeError:

            print(
                "Invalid JSON returned by Gemini:"
            )

            print(ai_response)

            return jsonify({
                "success": False,
                "error":
                    "AI returned an invalid syllabus format."
            }), 500

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        return jsonify({

            "success": True,

            "data": result_data

        }), 200

    except Exception as e:

        print(
            "SYLLABUS AI ERROR:",
            str(e)
        )

        return jsonify({

            "success": False,

            "error":
                "Syllabus analysis failed: "
                + str(e)

        }), 500

    finally:

        if file_path and os.path.exists(
            file_path
        ):

            try:
                os.remove(file_path)
            except Exception:
                pass


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    print(
        "======================================"
    )

    print(
        "       QuizOne Backend Starting"
    )

    print(
        "======================================"
    )

    print(
        f"Gemini Model: {GEMINI_MODEL}"
    )

    print(
        f"Gemini API Key: "
        f"{'Configured' if GEMINI_API_KEY else 'Missing'}"
    )

    print(
        "Quiz API:  http://127.0.0.1:5000/api/ai/generate"
    )

    print(
        "Chat API:  http://127.0.0.1:5000/api/ai/chat"
    )

    print(
        "Syllabus:  http://127.0.0.1:5000/api/ai/syllabus"
    )

    print(
        "======================================"
    )

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
 
