# from flask import Flask, render_template, request, jsonify

# from services.rag_service import rag_service
# from services.conversation_manager import conversation_manager

# app = Flask(__name__)


# @app.route("/")
# def home():
#     return render_template("index.html")


# @app.route("/api/session", methods=["POST"])
# def create_session():

#     try:
#         data = request.get_json(silent=True) or {}

#         mode = data.get("mode", "study").strip().lower()

#         job_role = (data.get("job_role") or "").strip()

#         if mode == "interview" and not job_role:
#             return jsonify({
#                 "success": False,
#                 "error": "Please provide the job position for this interview."
#             }), 400

#         if mode not in ("study", "interview"):
#             return jsonify({
#                 "success": False,
#                 "error": "Invalid conversation mode."
#             }), 400

#         session = conversation_manager.create_session(
#             mode=mode,
#             job_role=job_role if mode == "interview" else None
#         )

#         return jsonify({
#             "success": True,
#             "session_id": session["session_id"],
#             "mode": session["mode"],
#             "job_role": session["job_role"]
#         }), 201

#     except Exception:
#         app.logger.exception("Session creation error")

#         return jsonify({
#             "success": False,
#             "error": "Unable to create conversation session."
#         }), 500


# @app.route("/api/session/<session_id>", methods=["GET"])
# def get_session(session_id):

#     session = conversation_manager.get_session(session_id)

#     if session is None:
#         return jsonify({
#             "success": False,
#             "error": "Conversation session not found."
#         }), 404

#     return jsonify({
#         "success": True,
#         "session": session
#     }), 200


# @app.route("/api/chat", methods=["POST"])
# def chat():

#     try:
#         data = request.get_json(silent=True) or {}

#         question = data.get("question", "").strip()
#         mode = data.get("mode", "study").strip().lower()
#         session_id = data.get("session_id")

#         if not question:
#             return jsonify({
#                 "success": False,
#                 "error": "Please enter a question."
#             }), 400

#         if not session_id:
#             return jsonify({
#                 "success": False,
#                 "error": "A conversation session is required."
#             }), 400

#         session = conversation_manager.get_session(session_id)

#         if session is None:
#             return jsonify({
#                 "success": False,
#                 "error": "Conversation session not found. Please start a new conversation."
#             }), 404

#         if session["mode"] != mode:
#             return jsonify({
#                 "success": False,
#                 "error": "Conversation mode does not match the session."
#             }), 400

#         if session["status"] != "active":
#             return jsonify({
#                 "success": False,
#                 "error": "This conversation has already been completed."
#             }), 400

#         # Save the candidate's or student's latest message.
#         conversation_manager.add_message(
#             session_id,
#             "user",
#             question
#         )

#         # Prepare interview state.
#         interview_state = {
#             "job_role": session["job_role"],
#             "current_question": session["current_question"],
#             "question_number": session["question_number"],
#             "status": session["status"]
#         }

#         # Generate the context-aware answer.
#         response = rag_service.ask(
#             question=question,
#             mode=mode,
#             top_k=5,
#             conversation_history=session["conversation_history"],
#             interview_state=interview_state if mode == "interview" else None
#         )

#         answer = response["answer"]

#         # Save the AI response.
#         conversation_manager.add_message(
#             session_id,
#             "assistant",
#             answer
#         )

#         # Refresh the session after saving messages.
#         updated_session = conversation_manager.get_session(session_id)

#         return jsonify({
#             "success": True,
#             "answer": answer,
#             "mode": mode,
#             "model": response["model"],
#             "sources": response["sources"],
#             "session_id": session_id,
#             "conversation_history": updated_session["conversation_history"]
#         }), 200

#     except ValueError as error:
#         return jsonify({
#             "success": False,
#             "error": str(error)
#         }), 400

#     except Exception:
#         app.logger.exception("Chat API error")

#         return jsonify({
#             "success": False,
#             "error": "Something went wrong while generating your response. Please try again."
#         }), 500


# @app.route("/api/session/<session_id>", methods=["DELETE"])
# def delete_session(session_id):

#     deleted = conversation_manager.delete_session(session_id)

#     if not deleted:
#         return jsonify({
#             "success": False,
#             "error": "Conversation session not found."
#         }), 404

#     return jsonify({
#         "success": True,
#         "message": "Conversation session deleted."
#     }), 200


# if __name__ == "__main__":
#     app.run(
#         host="127.0.0.1",
#         port=5000,
#         debug=True
#     )


from flask import Flask, render_template, request, jsonify

from services.conversation_manager import conversation_manager
from services.study_manager import study_manager
from services.interview_manager import interview_manager


app = Flask(__name__)

# Register the actual managers with the central conversation manager.
conversation_manager.initialize_managers(
    study_manager=study_manager,
    interview_manager=interview_manager
)


@app.route("/")
def home():
    return render_template("index.html")


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

        if mode == "interview" and not job_role:
            return jsonify({
                "success": False,
                "error": "Please provide the job position for this interview."
            }), 400

        session = conversation_manager.create_session(
            mode=mode,
            job_role=job_role if mode == "interview" else None
        )

        return jsonify({
            "success": True,
            "session_id": session["session_id"],
            "mode": session["mode"],
            "job_role": session["job_role"]
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
def chat():
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

        # All messages now pass through ConversationManager.
        response = conversation_manager.process_message(
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


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
