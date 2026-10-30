
from datetime import datetime, timezone
from threading import Lock
import uuid


class ConversationManager:

    def __init__(self):
        self.sessions = {}
        self.lock = Lock()

        # Managers are connected later through initialize_managers().
        self.study_manager = None
        self.interview_manager = None

    def initialize_managers(self, study_manager, interview_manager):
        """Register the study and interview managers."""

        self.study_manager = study_manager
        self.interview_manager = interview_manager

    def create_session(self, mode, job_role=None):

        if mode not in ("study", "interview"):
            raise ValueError("Invalid conversation mode.")

        if mode == "interview":
            if not isinstance(job_role, str) or not job_role.strip():
                raise ValueError(
                    "A job role is required for interview mode."
                )

            job_role = job_role.strip()
        else:
            job_role = None

        session_id = str(uuid.uuid4())

        session = {
            "session_id": session_id,
            "mode": mode,
            "job_role": job_role,
            "status": "active",
            "question_number": 0,
            "current_question": None,
            "conversation_history": [],
            "evaluations": [],
            "total_score": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None
        }

        with self.lock:
            self.sessions[session_id] = session
            return self._copy_session(session)

    def _copy_session(self, session):

        return {
            **session,
            "conversation_history": [
                message.copy()
                for message in session["conversation_history"]
            ],
            "evaluations": [
                evaluation.copy()
                for evaluation in session["evaluations"]
            ]
        }

    def get_session(self, session_id):

        with self.lock:
            session = self.sessions.get(session_id)

            if session is None:
                return None

            return self._copy_session(session)

    def add_message(self, session_id, role, content):

        if role not in ("user", "assistant"):
            raise ValueError("Invalid message role.")

        if not isinstance(content, str) or not content.strip():
            raise ValueError("Message content cannot be empty.")

        message = {
            "role": role,
            "content": content.strip(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        with self.lock:
            session = self.sessions.get(session_id)

            if session is None:
                raise ValueError("Conversation session not found.")

            if session["status"] != "active":
                raise ValueError("This conversation has been completed.")

            session["conversation_history"].append(message)

            return message.copy()

    def process_message(self, session_id, question, top_k=5):
        """
        Route a user message to the appropriate manager.
        """

        if not isinstance(question, str) or not question.strip():
            raise ValueError("Please enter a question.")

        session = self.get_session(session_id)

        if session is None:
            raise ValueError("Conversation session not found.")

        if session["status"] != "active":
            raise ValueError("This conversation has been completed.")

        if self.study_manager is None or self.interview_manager is None:
            raise RuntimeError(
                "Study and interview managers have not been initialized."
            )

        self.add_message(session_id, "user", question)

        # Refresh history after adding the user's message.
        session = self.get_session(session_id)

        if session["mode"] == "study":

            response = self.study_manager.process_message(
                question=question,
                session=session,
                top_k=top_k
            )

        elif session["mode"] == "interview":

            response = self.interview_manager.process_message(
                question=question,
                session=session,
                top_k=top_k
            )

        else:
            raise ValueError("Unsupported conversation mode.")

        answer = response.get("answer")

        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("The manager returned an empty response.")

        self.add_message(session_id, "assistant", answer)

        updated_session = self.get_session(session_id)

        return {
            **response,
            "answer": answer,
            "mode": updated_session["mode"],
            "session_id": session_id,
            "conversation_history": updated_session["conversation_history"]
        }

    def set_current_question(self, session_id, question):

        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question cannot be empty.")

        with self.lock:
            session = self.sessions.get(session_id)

            if session is None:
                raise ValueError("Conversation session not found.")

            if session["status"] != "active":
                raise ValueError("This conversation has been completed.")

            session["current_question"] = question.strip()
            session["question_number"] += 1

    def add_evaluation(
        self,
        session_id,
        question,
        candidate_answer,
        score,
        feedback
    ):

        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError("Score must be a number.")

        if not 0 <= score <= 10:
            raise ValueError("Score must be between 0 and 10.")

        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question cannot be empty.")

        if not isinstance(candidate_answer, str):
            raise ValueError("Candidate answer must be text.")

        if not isinstance(feedback, str) or not feedback.strip():
            raise ValueError("Feedback cannot be empty.")

        evaluation = {
            "question": question.strip(),
            "candidate_answer": candidate_answer.strip(),
            "score": float(score),
            "feedback": feedback.strip(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        with self.lock:
            session = self.sessions.get(session_id)

            if session is None:
                raise ValueError("Conversation session not found.")

            if session["status"] != "active":
                raise ValueError("This conversation has been completed.")

            session["evaluations"].append(evaluation)
            session["total_score"] += float(score)
            session["current_question"] = None

            return evaluation.copy()

    def get_average_score(self, session_id):

        with self.lock:
            session = self.sessions.get(session_id)

            if session is None:
                raise ValueError("Conversation session not found.")

            evaluations = session["evaluations"]

            if not evaluations:
                return 0.0

            return round(
                session["total_score"] / len(evaluations),
                2
            )

    def complete_session(self, session_id):

        with self.lock:
            session = self.sessions.get(session_id)

            if session is None:
                raise ValueError("Conversation session not found.")

            session["status"] = "completed"
            session["completed_at"] = datetime.now(timezone.utc).isoformat()

            return self._copy_session(session)

    def delete_session(self, session_id):

        with self.lock:
            return self.sessions.pop(session_id, None) is not None


conversation_manager = ConversationManager()
