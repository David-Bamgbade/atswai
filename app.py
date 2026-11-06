from flask import Flask, render_template, request, jsonify

from services.conversation_manager import conversation_manager
from services.study_manager import study_manager
from services.interview_manager import interview_manager
from services.exam_session_manager import exam_session_manager


app = Flask(__name__)

# Register existing conversation managers.
conversation_manager.initialize_managers(
    study_manager=study_manager,
    interview_manager=interview_manager
)


@app.route("/")
def home():
    return render_template("index.html")


# --------------------------------------------------
# STUDY ASSISTANT AND AI INTERVIEWER
# --------------------------------------------------

@app.route("/api/session", methods=["POST"])
def create_session():
    try:
        data = request.get_json(silent=True) or {}

        mode = data.get("mode", "study")
        job_role = data.get("job_role", "")

        if not isinstance(mode, str):
            return jsonify({
                "success": False,
                "error": "Invalid conversation mode."
            }), 400

        mode = mode.strip().lower()

        if not isinstance(job_role, str):
            job_role = ""

        job_role = job_role.strip()

        if mode not in ("study", "interview"):
            return jsonify({
                "success": False,
                "error": "Invalid conversation mode."
            }), 400



        session = conversation_manager.create_session(
            mode=mode,
            job_role=job_role if mode == "interview" and job_role else None
        )

        greeting = None

        if mode == "interview":
            greeting = (
                "Hello! Welcome to your AI interview. "
                "I'll guide you through a few short introductory questions "
                "before we begin. What is your name? You may also say "
                "'prefer not to say' if you would rather not share it."
            )

            conversation_manager.add_message(
                session["session_id"],
                "assistant",
                greeting
            )

        return jsonify({
            "success": True,
            "session_id": session["session_id"],
            "mode": session["mode"],
            "job_role": session["job_role"],
            "greeting": greeting
        }), 201

    except Exception:
        app.logger.exception("Session creation error")

        return jsonify({
            "success": False,
            "error": "Unable to create conversation session."
        }), 500


@app.route("/api/session/<session_id>", methods=["GET"])
def get_session(session_id):
    session = conversation_manager.get_session(session_id)

    if session is None:
        return jsonify({
            "success": False,
            "error": "Conversation session not found."
        }), 404

    return jsonify({
        "success": True,
        "session": session
    }), 200


@app.route("/api/chat", methods=["POST"])
async def chat():
    try:
        data = request.get_json(silent=True) or {}

        question = data.get("question", "")
        mode = data.get("mode", "study")
        session_id = data.get("session_id")

        if not isinstance(question, str) or not question.strip():
            return jsonify({
                "success": False,
                "error": "Please enter a question."
            }), 400

        if not isinstance(session_id, str) or not session_id.strip():
            return jsonify({
                "success": False,
                "error": "A conversation session is required."
            }), 400

        if not isinstance(mode, str):
            return jsonify({
                "success": False,
                "error": "Invalid conversation mode."
            }), 400

        mode = mode.strip().lower()
        session_id = session_id.strip()

        session = conversation_manager.get_session(session_id)

        if session is None:
            return jsonify({
                "success": False,
                "error": "Conversation session not found. Please start a new conversation."
            }), 404

        if session["mode"] != mode:
            return jsonify({
                "success": False,
                "error": "Conversation mode does not match the session."
            }), 400

        response = await conversation_manager.process_message(
            session_id=session_id,
            question=question,
            top_k=5
        )

        return jsonify({
            "success": True,
            "answer": response["answer"],
            "mode": response["mode"],
            "model": response.get("model"),
            "sources": response.get("sources", []),
            "session_id": session_id,
            "conversation_history": response["conversation_history"]
        }), 200

    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

    except Exception:
        app.logger.exception("Chat API error")

        return jsonify({
            "success": False,
            "error": "Something went wrong while generating your response. Please try again."
        }), 500


@app.route("/api/session/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    deleted = conversation_manager.delete_session(session_id)

    if not deleted:
        return jsonify({
            "success": False,
            "error": "Conversation session not found."
        }), 404

    return jsonify({
        "success": True,
        "message": "Conversation session deleted."
    }), 200


# --------------------------------------------------
# ATSWA AI EXAMINER
# --------------------------------------------------

@app.route("/api/exam/start", methods=["POST"])
async def start_exam():
    try:
        data = request.get_json(silent=True) or {}

        paper_number = data.get("paper_number")
        exam_version = data.get("exam_version", 1)

        if isinstance(paper_number, bool) or not isinstance(paper_number, int):
            return jsonify({
                "success": False,
                "error": "A valid paper number from 1 to 12 is required."
            }), 400

        if not 1 <= paper_number <= 12:
            return jsonify({
                "success": False,
                "error": "Paper number must be between 1 and 12."
            }), 400

        if isinstance(exam_version, bool) or not isinstance(exam_version, int) or exam_version < 1:
            return jsonify({
                "success": False,
                "error": "Exam version must be a positive integer."
            }), 400

        exam = await exam_session_manager.start_exam(
            paper_number=paper_number,
            exam_version=exam_version
        )

        return jsonify({
            "success": True,
            "exam": exam
        }), 201

    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

    except Exception:
        app.logger.exception("Exam generation error")

        return jsonify({
            "success": False,
            "error": "Unable to generate the examination. Please try again."
        }), 500


@app.route("/api/exam/<exam_id>", methods=["GET"])
def get_exam(exam_id):
    try:
        exam = exam_session_manager.get_exam(exam_id)

        return jsonify({
            "success": True,
            "exam": exam
        }), 200

    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 404

    except Exception:
        app.logger.exception("Exam retrieval error")

        return jsonify({
            "success": False,
            "error": "Unable to retrieve this examination."
        }), 500


@app.route("/api/exam/<exam_id>/submit", methods=["POST"])
async def submit_exam(exam_id):
    try:
        data = request.get_json(silent=True) or {}
        answers = data.get("answers")

        if not isinstance(answers, list):
            return jsonify({
                "success": False,
                "error": "Answers must be submitted as a list."
            }), 400

        result = await exam_session_manager.submit_exam(
            exam_id=exam_id,
            answers=answers
        )

        return jsonify({
            "success": True,
            "message": "Examination marked successfully.",
            "result": result
        }), 200

    except ValueError as error:
        app.logger.exception("EXAM MARKING VALIDATION FAILED")
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

# --------------------------------------------------
# APPLICATION ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )

