from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from ai_service import generate_quiz

load_dotenv()

app = Flask(__name__)

# Allow frontend to communicate with Flask
CORS(app)


@app.route("/")
def home():
    return "QuizOne Backend is Running!"


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "message": "QuizOne backend is running"
    })


@app.route("/api/ai/generate", methods=["POST"])
def ai_generate():

    try:

        data = request.get_json(silent=True) or {}

        subject = str(data.get("subject", "")).strip()
        topic = str(data.get("topic", "")).strip()
        difficulty = str(
            data.get("difficulty", "medium")
        ).strip().lower()

        count = int(data.get("count", 5))

        # Validation
        if not subject:
            return jsonify({
                "error": "Subject is required"
            }), 400

        if not topic:
            return jsonify({
                "error": "Topic is required"
            }), 400

        if difficulty not in ["easy", "medium", "hard"]:
            return jsonify({
                "error": "Invalid difficulty"
            }), 400

        if count not in [5, 10, 15, 20]:
            return jsonify({
                "error": "Question count must be 5, 10, 15 or 20"
            }), 400

        print(
            f"Generating quiz: "
            f"{subject} | {topic} | {difficulty} | {count}"
        )

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

        print("AI GENERATION ERROR:", str(e))

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )