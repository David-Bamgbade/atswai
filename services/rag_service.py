import re

from services.vector_store import vector_store
from services.gemini_service import gemini_service


class RAGService:

    def __init__(self):
        self.vector_store = vector_store
        self.gemini_service = gemini_service

    def clean_response(self, answer):
        """Remove unwanted Markdown horizontal separators."""

        answer = re.sub(
            r"(?m)^[ \t]*(?:\*{3,}|-{3,}|_{3,})[ \t]*$",
            "",
            answer
        )

        return answer.strip()

    def format_history(self, conversation_history):
        """Convert conversation history into readable prompt text."""

        if not conversation_history:
            return "No previous conversation."

        history_parts = []

        # Keep the most recent 12 messages to control prompt size.
        for message in conversation_history[-12:]:

            role = message.get("role", "user")
            content = message.get("content", "")

            if role == "assistant":
                speaker = "ATSWA AI"
            else:
                speaker = "Candidate/Student"

            history_parts.append(
                f"{speaker}: {content}"
            )

        return "\n\n".join(history_parts)

    def build_prompt(
        self,
        question,
        context,
        mode,
        conversation_history=None,
        interview_state=None
    ):

        history = self.format_history(
            conversation_history or []
        )

        common_instructions = """
You are an expert ATSWA (Accounting Technicians Scheme
West Africa) educational and professional assessment assistant.

Your knowledge covers:
- Financial Accounting
- Management Accounting
- Auditing and Assurance
- Taxation
- Business Law
- Financial Reporting
- Economics and other relevant ATSWA subjects.

KNOWLEDGE BASE RULES:

1. Use the supplied knowledge context as your primary
   reference for technical accounting information.
2. Never invent accounting standards, regulations,
   tax laws, or examination requirements.
3. If the context does not adequately answer a question,
   clearly acknowledge the limitation.
4. Do not expose internal database information.
5. Do not mention chunks, retrieval scores, database IDs,
   or internal search operations.
6. Do not fabricate citations, page numbers, or sources.
7. Distinguish between information supported by the
   knowledge context and anything you cannot verify.
"""

        if mode == "study":

            mode_instructions = """
OPERATING MODE: ATSWA STUDY ASSISTANT

You are a personal ATSWA tutor.

Your responsibility is to teach candidates and help them
prepare effectively for ATSWA examinations.

CONVERSATION MEMORY:

1. Read the conversation history before answering.
2. Treat the latest message as part of the existing
   conversation, not automatically as a new topic.
3. Understand references such as:
   - Explain that again.
   - Give me an example.
   - What about the second point?
   - Why is that the case?
   - I don't understand.
4. Use previous messages to identify what the student
   is referring to.
5. Maintain the current topic unless the student
   clearly introduces a different topic.
6. Never pretend the student has not asked a previous
   question when that question appears in the history.

TEACHING RULES:

1. Answer the user's question directly.
2. Explain accounting concepts clearly.
3. Break complicated topics into understandable sections.
4. Give practical examples where supported.
5. Explain important accounting terminology.
6. Provide examination tips when relevant.
7. Generate practice questions when requested.
8. Explain correct answers to practice questions.
9. Adapt explanations when the student says they
   do not understand.
10. Never turn an ordinary study question into an interview.

If the student requests a quiz, start a quiz and ask
one question at a time. Remember the quiz question
and the student's responses in the conversation.
"""

        elif mode == "interview":

            state = interview_state or {}
            job_role = state.get(
                "job_role",
                "Accounting or Finance Candidate"
            )

            candidate_name = state.get("candidate_name") or "Candidate"
            candidate_background = (
                state.get("candidate_background")
                or "No background information provided."
            )
            current_question = state.get(
                "current_question"
            )

            question_number = state.get(
                "question_number",
                0
            )

            status = state.get(
                "status",
                "active"
            )

            interview_instructions = f"""
OPERATING MODE: ATSWA AI INTERVIEWER

You are conducting a professional accounting interview.
JOB ROLE:
{job_role}

CANDIDATE NAME:
{candidate_name}

CANDIDATE BACKGROUND:
{candidate_background}

INTERVIEW STATUS:
{status}

QUESTION NUMBER:
{question_number}

CURRENT QUESTION AWAITING AN ANSWER:
{current_question or "No question has been asked yet."}

INTERVIEW CONVERSATION RULES:

1. Always read the interview history and current
   interview state before responding.
2. Never forget a question already asked.
3. Never ask a new question when the candidate is
   still answering the previous question.
4. Ask only one interview question at a time.
5. Assess answers using the supplied ATSWA knowledge
   context.
6. Evaluate technical accuracy, completeness,
   reasoning and professional judgement.
7. Give constructive feedback after an answer.
8. Score attempted answers out of 10.
9. Explain important points the candidate missed.
10. Adjust question difficulty based on performance.

HANDLING CANDIDATE RESPONSES:

If the candidate provides an answer:
- Evaluate the answer against the knowledge context.
- Identify correct points.
- Identify missing or incorrect points.
- Give a score out of 10.
- Explain how the answer could be improved.
- Only then move to the next interview question.

If the candidate says:
"I don't know", "I am not sure", or similar:
- Recognise that the candidate cannot answer.
- Do not ask an unrelated question immediately.
- Explain the expected answer using the knowledge context.
- Give constructive feedback.
- Do not award marks for knowledge that was not demonstrated.
- After the explanation, ask whether the candidate
  is ready to continue.

If the candidate asks:
"What's the answer?" or "Explain the answer":
- Explain the correct answer to the current question.
- Do not pretend the candidate answered correctly.
- Do not start another question in the same response.

If the candidate asks a follow-up question:
- Explain the current question further.
- Do not treat the follow-up as an answer.
- Do not move to the next question.
If there is no current question:
- Consider the candidate's background and selected job role.
- Generate exactly ONE relevant opening interview question.
- Address the candidate by name when available.
- Do not repeat the onboarding welcome.
- Do not evaluate or score the onboarding responses.
- Do not ask multiple questions in the opening response.
If the candidate says they are ready to continue
after receiving feedback:
- Ask the next appropriate interview question.

IMPORTANT:
Do not invent previous answers, scores or interview progress.
Use the actual interview state and conversation history.
"""

            mode_instructions = interview_instructions

        else:
            raise ValueError(
                "Invalid mode. Choose 'study' or 'interview'."
            )

        formatting_instructions = """
RESPONSE FORMATTING:

1. Use professional, readable Markdown.
2. Use headings where necessary.
3. Use bold formatting for important terms.
4. Use numbered lists and bullet points where appropriate.
5. Never use horizontal rules or decorative separators.
6. Avoid unnecessary introductory statements.
7. Avoid repetitive conclusions.
8. Do not generate a separate Sources section.
   The application handles source references separately.
9. Keep responses structured and easy to read.
"""

        prompt = f"""
{common_instructions}

{mode_instructions}

{formatting_instructions}

PREVIOUS CONVERSATION:

{history}

KNOWLEDGE CONTEXT:

{context}

LATEST USER MESSAGE:

{question}

Read the previous conversation and the current state carefully.
Respond to the latest message in the correct operating mode.
"""

        return prompt

    async def ask(
        self,
        question,
        mode="study",
        top_k=5,
        conversation_history=None,
        interview_state=None
    ):

        if not question or not question.strip():
            raise ValueError("Please enter a question.")

        if mode not in ("study", "interview"):
            raise ValueError(
                "Mode must be either 'study' or 'interview'."
            )

        conversation_history = conversation_history or []

        # 1. Build a context-aware retrieval query.
        retrieval_query = question

        if conversation_history:

            recent_history = conversation_history[-4:]

            history_text = "\n".join(
                message.get("content", "")
                for message in recent_history
            )

            retrieval_query = (
                f"{history_text}\n{question}"
            )

        # For interviews, include the current question
        # so retrieval remains relevant when the candidate
        # answers with a short response.
        if mode == "interview" and interview_state:

            current_question = interview_state.get(
                "current_question"
            )

            if current_question:
                retrieval_query += (
                    f"\nInterview question: {current_question}"
                )

        # 2. Retrieve relevant ATSWA documents.
        retrieved_documents = await self.vector_store.search(
            question=retrieval_query,
            top_k=top_k
        )

        if not retrieved_documents:
            return {
                "answer": (
                    "I could not find sufficient relevant "
                    "information in the ATSWA knowledge base "
                    "to answer this question accurately."
                ),
                "sources": [],
                "model": None,
                "mode": mode
            }

        # 3. Build knowledge context.
        context_parts = []

        for index, document in enumerate(
            retrieved_documents, start=1
        ):

            context_parts.append(
                f"""
Source {index}: {document['source']}

{document['text']}
"""
            )

        context = "\n\n".join(context_parts)

        # 4. Build the context-aware prompt.
        prompt = self.build_prompt(
            question=question,
            context=context,
            mode=mode,
            conversation_history=conversation_history,
            interview_state=interview_state
        )

        # 5. Generate response with Gemini.
        generation = await self.gemini_service.generate(prompt)

        answer = self.clean_response(
            generation["answer"]
        )

        # 6. Prepare unique source references.
        sources = []
        seen_sources = set()

        for document in retrieved_documents:

            source_name = document["source"]

            if source_name not in seen_sources:

                seen_sources.add(source_name)

                sources.append({
                    "source": source_name
                })

        # 7. Return response.
        return {
            "answer": answer,
            "model": generation["model"],
            "mode": mode,
            "sources": sources
        }


rag_service = RAGService()

