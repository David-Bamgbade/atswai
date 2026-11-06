import asyncio

from services.conversation_manager import ConversationManager


class MockStudyManager:

    async def process_message(self, question, session, top_k=5):
        return {
            "answer": "This is a study response.",
            "model": "test-model",
            "mode": "study",
            "sources": []
        }


class MockInterviewManager:

    async def process_message(self, question, session, top_k=5):
        assert session["job_role"] == "Internal Auditor"

        return {
            "answer": "This is an interview response. Score: 8/10.",
            "model": "test-model",
            "mode": "interview",
            "sources": []
        }


async def test_conversation_manager():

    manager = ConversationManager()

    manager.initialize_managers(
        study_manager=MockStudyManager(),
        interview_manager=MockInterviewManager()
    )

    # Test study session routing.
    study_session = manager.create_session(mode="study")

    study_response = await manager.process_message(
        session_id=study_session["session_id"],
        question="Explain depreciation."
    )

    assert study_response["mode"] == "study"
    assert study_response["answer"] == "This is a study response."
    assert len(study_response["conversation_history"]) == 2

    # Test interview session routing.
    interview_session = manager.create_session(
        mode="interview",
        job_role="Internal Auditor"
    )

    interview_response = await manager.process_message(
        session_id=interview_session["session_id"],
        question="What is internal auditing?"
    )

    assert interview_response["mode"] == "interview"
    assert interview_response["answer"] == (
        "This is an interview response. Score: 8/10."
    )
    assert len(interview_response["conversation_history"]) == 2

    # Confirm both sessions remain independently stored.
    assert manager.get_session(study_session["session_id"]) is not None
    assert manager.get_session(interview_session["session_id"]) is not None

    print("Study response:", study_response["answer"])
    print("Interview response:", interview_response["answer"])
    print("\\nAll conversation manager tests passed.")


if __name__ == "__main__":
    asyncio.run(test_conversation_manager())
