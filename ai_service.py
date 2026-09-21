import os
import json
import time

from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in .env")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_quiz(subject, topic, difficulty="medium", count=5):

    prompt = f"""
You are QuizOne, an AI quiz generator for students.

Generate exactly {count} multiple-choice questions.

Subject: {subject}
Topic: {topic}
Difficulty: {difficulty}

Rules:
- Generate exactly {count} questions.
- Each question must have exactly 4 options.
- There must be exactly one correct answer.
- correct_answer must exactly match one option.
- Give a short, clear explanation.
- Questions must be relevant to the given subject and topic.
- Avoid duplicate questions.
- Return ONLY valid JSON.
- Do not use markdown.
- Do not add any text outside the JSON.

JSON format:

{{
  "questions": [
    {{
      "question": "Question text",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "correct_answer": "Option A",
      "explanation": "Short explanation"
    }}
  ]
}}
"""

    # -----------------------------------
    # Gemini API with automatic retry
    # -----------------------------------

    response = None

    for attempt in range(3):

        try:
            print(
                f"Gemini request attempt {attempt + 1}/3..."
            )

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )

            # Request successful
            break

        except Exception as e:

            error_text = str(e)

            # Temporary Gemini server overload
            if "503" in error_text or "UNAVAILABLE" in error_text:

                if attempt < 2:
                    print(
                        "Gemini is temporarily unavailable."
                    )
                    print(
                        "Retrying in 3 seconds..."
                    )

                    time.sleep(3)
                    continue

                raise RuntimeError(
                    "Gemini is currently busy. "
                    "Please try again after a few seconds."
                )

            # Other Gemini errors
            raise RuntimeError(
                f"Gemini API error: {error_text}"
            )

    # -----------------------------------
    # Read Gemini response
    # -----------------------------------

    try:

        text = (response.text or "").strip()

        if not text:
            raise ValueError(
                "Gemini returned an empty response"
            )

        # Remove markdown code fences if Gemini adds them
        if text.startswith("```"):
            text = text.replace("```json", "")
            text = text.replace("```", "")
            text = text.strip()

        # Convert JSON string to Python object
        result = json.loads(text)

    except json.JSONDecodeError as e:

        raise ValueError(
            f"Gemini returned invalid JSON: {str(e)}"
        )

    # -----------------------------------
    # Validate questions
    # -----------------------------------

    questions = result.get("questions")

    if not isinstance(questions, list):
        raise ValueError(
            "Invalid questions format"
        )

    if len(questions) != count:
        raise ValueError(
            f"Expected {count} questions "
            f"but received {len(questions)}"
        )

    # -----------------------------------
    # Validate each question
    # -----------------------------------

    for i, q in enumerate(questions, start=1):

        if not isinstance(q, dict):
            raise ValueError(
                f"Question {i} has invalid format"
            )

        if not q.get("question"):
            raise ValueError(
                f"Question {i} is missing"
            )

        options = q.get("options")

        if not isinstance(options, list):
            raise ValueError(
                f"Question {i} options are invalid"
            )

        if len(options) != 4:
            raise ValueError(
                f"Question {i} must contain exactly 4 options"
            )

        correct_answer = q.get("correct_answer")

        if correct_answer not in options:
            raise ValueError(
                f"Question {i} has invalid correct answer"
            )

        if not q.get("explanation"):
            q["explanation"] = (
                "Explanation not available."
            )

    # -----------------------------------
    # Return final quiz
    # -----------------------------------

    return {
        "questions": questions
    }