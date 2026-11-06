
from services.rag_service import rag_service


class InterviewManager:

    def __init__(self, rag=None):
        self.rag = rag or rag_service

    def _build_interview_state(self, session):
        return {
            "job_role": session.get("job_role"),
            "candidate_name": session.get("candidate_name"),
            "candidate_background": session.get("candidate_background"),
            "current_question": session.get("current_question"),
            "question_number": session.get("question_number", 0),
            "status": session.get("status"),
            "evaluations": session.get("evaluations", []),
            "total_score": session.get("total_score", 0)
        }

    async def start_interview(self, session, top_k=5):
        if not isinstance(session, dict):
            raise ValueError("Interview session is required.")

        if session.get("mode") != "interview":
            raise ValueError("This is not an interview session.")

        if session.get("status") != "active":
            raise ValueError("This interview session is no longer active.")

        if session.get("interview_stage") != "in_progress":
            raise ValueError("Interview onboarding is not complete.")

        if not session.get("job_role"):
            raise ValueError("Interview job role is missing.")

        response = await self.rag.ask(
            question="Begin the interview by asking one relevant opening question.",
            mode="interview",
            top_k=top_k,
            conversation_history=session.get("interview_history", []),
            interview_state=self._build_interview_state(session)
        )

        if not isinstance(response, dict):
            raise RuntimeError("Invalid response from RAG service.")

        answer = response.get("answer")

        if not answer or not response.get("model"):
            raise RuntimeError(
                "The AI interviewer could not generate an opening question. "
                "Check the ATSWA knowledge base and Gemini service."
            )

        return {
            "answer": answer,
            "model": response.get("model"),
            "mode": "interview",
            "sources": response.get("sources", [])
        }

    async def process_message(self, question, session, top_k=5):

        if not isinstance(question, str) or not question.strip():
            raise ValueError("Please provide an interview response.")

        if not isinstance(session, dict):
            raise ValueError("Interview session is required.")

        if session.get("mode") != "interview":
            raise ValueError("This is not an interview session.")

        if session.get("status") != "active":
            raise ValueError("This interview session is no longer active.")

        job_role = session.get("job_role")

        if not job_role:
            raise ValueError("Interview job role is missing.")

        interview_state = self._build_interview_state(session)

        interview_history = session.get("interview_history", [])

        response = await self.rag.ask(
            question=question.strip(),
            mode="interview",
            top_k=top_k,
            conversation_history=interview_history,
            interview_state=interview_state
        )

        if not isinstance(response, dict):
            raise RuntimeError("Invalid response from RAG service.")

        answer = response.get("answer")

        if not answer:
            raise RuntimeError("The AI interviewer returned an empty response.")

        return {
            "answer": answer,
            "model": response.get("model"),
            "mode": "interview",
            "sources": response.get("sources", [])
        }


interview_manager = InterviewManager()

