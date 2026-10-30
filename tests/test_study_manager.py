
from services.study_manager import StudyManager


class MockRAGService:

    def ask(
        self,
        question,
        mode,
        top_k,
        conversation_history,
        interview_state=None
    ):

        return {
            "answer": "Depreciation is the systematic allocation of an asset's depreciable amount over its useful life.",
            "model": "test-model",
            "mode": mode,
            "sources": [
                {"source": "2025_FA"}
            ]
        }


def main():

    study_manager = StudyManager(
        rag=MockRAGService()
    )

    session = {
        "session_id": "test-session",
        "mode": "study",
        "status": "active",
        "conversation_history": [
            {
                "role": "user",
                "content": "Explain depreciation."
            }
        ]
    }

    response = study_manager.process_message(
        question="Explain depreciation.",
        session=session
    )

    assert response["mode"] == "study"
    assert response["model"] == "test-model"
    assert len(response["sources"]) == 1

    print("Answer:", response["answer"])
    print("Mode:", response["mode"])
    print("Sources:", response["sources"])
    print("All study manager tests passed.")


if __name__ == "__main__":
    main()
