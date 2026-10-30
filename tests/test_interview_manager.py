
from services.interview_manager import InterviewManager


class MockRAGService:

    def ask(
        self,
        question,
        mode,
        top_k,
        conversation_history,
        interview_state=None
    ):
        assert mode == "interview"
        assert interview_state["job_role"] == "Internal Auditor"

        return {
            "answer": "Your answer demonstrates a good understanding of internal controls. Score: 8/10.",
            "model": "test-model",
            "sources": [
                {"source": "2025_Aud"}
            ]
        }


def test_interview_manager():

    interview_manager = InterviewManager(
        rag=MockRAGService()
    )

    session = {
        "session_id": "test-interview",
        "mode": "interview",
        "job_role": "Internal Auditor",
        "status": "active",
        "question_number": 1,
        "current_question": "What is internal auditing?",
        "conversation_history": [
            {
                "role": "assistant",
                "content": "What is internal auditing?"
            }
        ],
        "evaluations": [],
        "total_score": 0
    }

    response = interview_manager.process_message(
        question="Internal auditing evaluates internal controls and risk management.",
        session=session
    )

    assert response["mode"] == "interview"
    assert response["model"] == "test-model"
    assert len(response["sources"]) == 1
    assert "8/10" in response["answer"]

    print("Answer:", response["answer"])
    print("Mode:", response["mode"])
    print("Sources:", response["sources"])

    print("\nAll interview manager tests passed.")


if __name__ == "__main__":
    test_interview_manager()
