
from services.rag_service import rag_service


class StudyManager:

    def __init__(self, rag=None):
        self.rag = rag or rag_service

    def process_message(self, question, session, top_k=5):
        """
        Process a student's message using the ATSWA RAG service.
        """

        if not isinstance(question, str) or not question.strip():
            raise ValueError("Please enter a study question.")

        if not session:
            raise ValueError("Study session is required.")

        if session.get("mode") != "study":
            raise ValueError("This is not a study session.")

        if session.get("status") != "active":
            raise ValueError("This study session is no longer active.")

        conversation_history = session.get(
            "conversation_history", []
        )

        response = self.rag.ask(
            question=question.strip(),
            mode="study",
            top_k=top_k,
            conversation_history=conversation_history
        )

        if not isinstance(response, dict):
            raise RuntimeError("Invalid response from RAG service.")

        answer = response.get("answer")

        if not answer:
            raise RuntimeError("The AI returned an empty response.")

        return {
            "answer": answer,
            "model": response.get("model"),
            "mode": "study",
            "sources": response.get("sources", [])
        }


study_manager = StudyManager()
