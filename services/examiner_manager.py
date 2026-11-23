import math
import json
import re

from services.exam_blueprint import ExamBlueprint
from services.question_allocator import QuestionAllocator
from services.vector_store import vector_store
from services.gemini_service import gemini_service


class ExaminerManager:

    def __init__(self):
        self.blueprint = ExamBlueprint()
        self.allocator = QuestionAllocator(self.blueprint)

    async def _retrieve_context(self, allocation):
        topics = set()

        for section in allocation["sections"]:
            for item in section["questions"]:
                if item.get("topic"):
                    topics.add(item["topic"])

                for topic_item in item.get("topics", []):
                    if isinstance(topic_item, dict) and topic_item.get("topic"):
                        topics.add(topic_item["topic"])

        context = {}

        for topic in sorted(topics):
            try:
                results = await vector_store.search(topic, top_k=2)
                context[topic] = [
                    {
                        "source": result.get("source", "Unknown"),
                        "text": result.get("text", "")[:2200]
                    }
                    for result in results
                    if result.get("text")
                ]
            except Exception as error:
                print(f"Retrieval failed for {topic}: {error}")
                context[topic] = []

        return context

    def _extract_json(self, response_text):
        cleaned = response_text.strip()

        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE
        )
        cleaned = re.sub(r"\s*```$", "", cleaned)

        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1 or end == -1:
            raise ValueError("Gemini did not return a valid JSON object.")

        return json.loads(cleaned[start:end + 1])

    async def _generate_batch(self, instructions, allocation, context):
        prompt = f"""
You are an experienced ATSWA examination question setter.

Generate ONLY the questions requested in this batch.

STRICT RULES:
- Follow the supplied allocation exactly.
- Do not generate fewer or more questions than requested.
- Use only the specified syllabus topics.
- Do not duplicate questions.
- Use realistic ATSWA examination language.
- Use Nigerian accounting context where relevant.
- Questions must be academically sound and unambiguous.
- Use the supplied reference material as the primary source.
- Do not invent official syllabus requirements.
- Marks must match the allocation exactly.
- Return valid JSON only, without Markdown fences.

BATCH INSTRUCTIONS:
{instructions}

QUESTION ALLOCATION:
{json.dumps(allocation, ensure_ascii=False, indent=2)}

REFERENCE MATERIAL:
{json.dumps(context, ensure_ascii=False, indent=2)}

Return this JSON structure:

{{
  "questions": [
    {{
      "number": 1,
      "topic": "Exact allocated topic",
      "type": "multiple_choice",
      "marks": 1,
      "question": "Question text",
      "options": {{
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D"
      }}
    }}
  ],
  "answer_key": [
    {{
      "section": "A",
      "question_number": 1,
      "question_type": "multiple_choice",
      "correct_answer": "A",
      "explanation": "Brief explanation"
    }}
  ]
}}

For short-answer questions:
- Use type "short_answer".
- Include an expected answer in the answer key.
- Include a marking guide where appropriate.
- Do not include MCQ options.

For structured questions:
- Use type "structured".
- Include sub_questions.
- Every sub-question must have its own marks.
- Include a marking guide in the answer key.
- The marking-guide marks must add up to the question's total marks.
- The structured question number must match the supplied allocation.

Every question must have exactly one corresponding answer-key entry.
"""

        result = await gemini_service.generate(prompt, json_mode=True)
        data = self._extract_json(result["answer"])

        if not isinstance(data.get("questions"), list):
            raise ValueError("Gemini batch has no valid questions list.")

        if not isinstance(data.get("answer_key"), list):
            raise ValueError("Gemini batch has no valid answer_key list.")

        return data

    async def _generate_section_a_batch(
        self, question_type, items, context, start_number=1
    ):
        expected_count = sum(item["question_count"] for item in items)

        instructions = f"""
Generate exactly {expected_count} questions.

Question type: {question_type}

Distribute the questions across the topics using the exact counts below.
Each question must have one mark.

Use question numbers starting at {start_number} and continue sequentially.

For each topic, generate exactly its allocated number of questions.
"""

        batch = await self._generate_batch(
            instructions,
            items,
            context
        )

        questions = batch["questions"]
        answer_key = batch["answer_key"]

        if len(questions) != expected_count:
            raise ValueError(
                f"{question_type}: expected {expected_count} questions, "
                f"Gemini generated {len(questions)}."
            )

        if len(answer_key) != expected_count:
            raise ValueError(
                f"{question_type}: expected {expected_count} answer keys, "
                f"Gemini generated {len(answer_key)}."
            )

        for index, question in enumerate(questions, start=start_number):
            question["number"] = index
            question["type"] = question_type

        for index, entry in enumerate(answer_key, start=start_number):
            entry["section"] = "A"
            entry["question_number"] = index
            entry["question_type"] = question_type

        return questions, answer_key

    def _assign_structured_part_ids(
        self, question, answer, section_name, number, total_marks
    ):
        sub_questions = question.get("sub_questions")
        marking_guide = answer.get("marking_guide")

        if not isinstance(sub_questions, list) or not sub_questions:
            raise ValueError("Structured question has no valid sub-questions.")

        if not isinstance(marking_guide, list) or not marking_guide:
            raise ValueError("Structured question has no valid marking guide.")

        question_parts = {}
        guide_parts = {}

        for part in sub_questions:
            if not isinstance(part, dict):
                raise ValueError("Invalid structured sub-question.")

            label = str(part.get("part", "")).strip().lower()

            if not label or label in question_parts:
                raise ValueError(
                    f"Missing or duplicate question part label: {label!r}"
                )

            part_marks = float(part.get("marks", 0))

            if not math.isfinite(part_marks) or part_marks < 0:
                raise ValueError(
                    f"Invalid marks allocated to question part {label}."
                )

            part["part"] = label
            question_parts[label] = part_marks

        for entry in marking_guide:
            if not isinstance(entry, dict):
                raise ValueError("Invalid marking-guide entry.")

            label = str(entry.get("part", "")).strip().lower()

            if not label or label in guide_parts:
                raise ValueError(
                    f"Missing or duplicate marking-guide label: {label!r}"
                )

            guide_marks = float(entry.get("marks", 0))

            if not math.isfinite(guide_marks) or guide_marks < 0:
                raise ValueError(
                    f"Invalid marking-guide marks for part {label}."
                )

            entry["part"] = label
            guide_parts[label] = guide_marks

        if set(question_parts) != set(guide_parts):
            raise ValueError(
                "Question and marking-guide labels do not match. "
                f"Question labels: {sorted(question_parts)}; "
                f"guide labels: {sorted(guide_parts)}."
            )

        for label, part_marks in question_parts.items():
            if abs(part_marks - guide_parts[label]) > 0.01:
                raise ValueError(
                    f"Mark allocation mismatch for part {label}: "
                    f"question={part_marks}, guide={guide_parts[label]}."
                )

        question_total = sum(question_parts.values())
        guide_total = sum(guide_parts.values())

        if (
            abs(question_total - total_marks) > 0.01
            or abs(guide_total - total_marks) > 0.01
        ):
            raise ValueError(
                "Structured question or marking-guide marks "
                "do not match the allocated question total."
            )

        # IDs are generated exclusively by Python.
        for index, part in enumerate(sub_questions, start=1):
            part_id = f"{section_name}-Q{number}-P{index:02d}"
            part["part_id"] = part_id

        ids_by_label = {
            part["part"]: part["part_id"]
            for part in sub_questions
        }

        for entry in marking_guide:
            entry["part_id"] = ids_by_label[entry["part"]]

        return question, answer

    async def _generate_structured_question(
        self, item, context, section_name="B"
    ):
        number = item["question_number"]
        topic = item.get("topic", " / ".join(
            entry.get("topic", "") for entry in item.get("topics", [])
        ))
        marks = float(item["marks"])

        instructions = f"""
Generate exactly ONE ATSWA structured examination question.

Question number: {number}
Section: {section_name}
Topic: {topic}
Total marks: {marks}

The question must contain meaningful sub-questions.
The sub-question marks must add up to exactly {marks}.

Generate one answer-key entry with a detailed marking guide.

The marking_guide MUST be a JSON ARRAY of objects.
Each object must contain:
- part: the sub-question letter
- criteria: detailed expected answer and marking criteria
- marks: numeric marks

The marking guide marks must add up to exactly {marks}.

Use exactly the same part labels in the question and marking guide.
Each question part must have exactly one corresponding marking-guide entry.
Do not generate part_id fields. They are assigned by the application.
Do not generate additional questions.
"""

        last_error = None

        for attempt in range(1, 4):
            attempt_instructions = instructions

            if last_error:
                attempt_instructions += f"""

IMPORTANT: Your previous generation was rejected:
{last_error}

Regenerate the entire question and marking guide.
Correct the mismatch while preserving the allocated topic and total marks.
Ensure every question part has exactly one matching marking-guide entry.
"""

            batch = await self._generate_batch(
                attempt_instructions, item, context
            )

            try:
                if (
                    len(batch["questions"]) != 1
                    or len(batch["answer_key"]) != 1
                ):
                    raise ValueError(
                        "Expected exactly one question and one answer key."
                    )

                question = batch["questions"][0]
                answer = batch["answer_key"][0]

                question["number"] = number
                question["topic"] = topic
                question["type"] = "structured"
                question["marks"] = marks

                answer["section"] = section_name
                answer["question_number"] = number
                answer["question_type"] = "structured"
                answer["total_marks"] = marks

                return self._assign_structured_part_ids(
                    question, answer, section_name, number, marks
                )

            except (ValueError, TypeError, KeyError, AttributeError) as error:
                last_error = str(error)
                print(
                    f"Structured question {section_name}-{number}: "
                    f"attempt {attempt}/3 rejected: {last_error}"
                )

        raise ValueError(
            f"Could not generate a valid structured question "
            f"for {section_name}-{number} after 3 attempts. "
            f"Last error: {last_error}"
        )

    async def _generate_section_specific_question(
        self, item, context, section_name
    ):
        number = item.get("question_number", 1)
        marks = float(item["marks"])
        topics = item.get("topics", [])

        topic_names = [
            entry.get("topic", "")
            for entry in topics
            if isinstance(entry, dict) and entry.get("topic")
        ]

        instructions = f"""
Generate exactly ONE compulsory ATSWA Communication Skills
comprehension OR summary examination exercise.

Section: {section_name}
Question number: {number}
Total marks: {marks}
Relevant syllabus topics:
{json.dumps(topic_names, ensure_ascii=False)}

Create an original, realistic passage suitable for an ATSWA examination.
The passage must be included in the question JSON as "passage".
Do not claim that the passage is an official ICAN passage.

Create one clear examination task based on the passage.
The task must be represented by "question".
If the task has sub-parts, use "sub_questions", each with:
- "part": a, b, c, etc.
- "question": the instruction
- "marks": numeric marks

If the task is a single summary response, use one sub-question.
The sub-question marks must total exactly {marks}.

The answer key must contain one entry with:
- "expected_answer"
- "marking_guide": a JSON array
Each marking-guide object must contain "part", "criteria", and numeric "marks".
The marking-guide marks must total exactly {marks}.

Use exactly the same part labels in the question and marking guide.
Each question part must have exactly one corresponding marking-guide entry.
Do not generate part_id fields. They are assigned by the application.

Return exactly one question and one answer-key entry.
Use the supplied reference material as the primary academic guidance.
"""

        last_error = None

        for attempt in range(1, 4):
            attempt_instructions = instructions

            if last_error:
                attempt_instructions += f"""

IMPORTANT: Your previous generation was rejected:
{last_error}

Regenerate the entire passage, question and marking guide.
Correct the mismatch while preserving the allocated topic and total marks.
Ensure every question part has exactly one matching marking-guide entry.
"""

            batch = await self._generate_batch(
                attempt_instructions, item, context
            )

            try:
                if (
                    len(batch["questions"]) != 1
                    or len(batch["answer_key"]) != 1
                ):
                    raise ValueError(
                        "Expected exactly one question and one answer key."
                    )

                question = batch["questions"][0]
                answer = batch["answer_key"][0]

                question["number"] = number
                question["topic"] = "Comprehension or summary"
                question["type"] = "structured"
                question["marks"] = marks

                if not question.get("passage"):
                    raise ValueError(
                        "The comprehension/summary exercise has no passage."
                    )

                answer["section"] = section_name
                answer["question_number"] = number
                answer["question_type"] = "structured"
                answer["total_marks"] = marks

                return self._assign_structured_part_ids(
                    question, answer, section_name, number, marks
                )

            except (ValueError, TypeError, KeyError, AttributeError) as error:
                last_error = str(error)
                print(
                    f"Section-specific question {section_name}-{number}: "
                    f"attempt {attempt}/3 rejected: {last_error}"
                )

        raise ValueError(
            f"Could not generate a valid section-specific question "
            f"for {section_name}-{number} after 3 attempts. "
            f"Last error: {last_error}"
        )

    def _validate_paper(self, paper, allocation):
        generated_sections = paper.get("sections", [])
        allocated_sections = allocation.get("sections", [])

        if len(generated_sections) != len(allocated_sections):
            raise ValueError("Generated section count is incorrect.")

        expected_keys = set()

        for allocated, generated in zip(allocated_sections, generated_sections):
            section_name = str(allocated["name"])

            if str(generated.get("name")) != section_name:
                raise ValueError(f"Section order/name mismatch for {section_name}.")

            allocated_items = allocated.get("questions", [])
            generated_questions = generated.get("questions", [])

            expected_mcq = sum(
                item.get("question_count", 0)
                for item in allocated_items
                if item.get("question_type") == "multiple_choice"
            )
            expected_short = sum(
                item.get("question_count", 0)
                for item in allocated_items
                if item.get("question_type") == "short_answer"
            )
            expected_structured = sum(
                1 for item in allocated_items
                if item.get("question_type") in ("structured", "section_specific")
            )

            actual_mcq = [
                q for q in generated_questions
                if q.get("type") == "multiple_choice"
            ]
            actual_short = [
                q for q in generated_questions
                if q.get("type") == "short_answer"
            ]
            actual_structured = [
                q for q in generated_questions
                if q.get("type") == "structured"
            ]

            if len(actual_mcq) != expected_mcq:
                raise ValueError(
                    f"Section {section_name}: expected {expected_mcq} MCQs, "
                    f"received {len(actual_mcq)}."
                )

            if len(actual_short) != expected_short:
                raise ValueError(
                    f"Section {section_name}: expected {expected_short} "
                    f"short answers, received {len(actual_short)}."
                )

            if len(actual_structured) != expected_structured:
                raise ValueError(
                    f"Section {section_name}: expected {expected_structured} "
                    f"structured questions, received {len(actual_structured)}."
                )

            for question in actual_mcq:
                if set(question.get("options", {}).keys()) != {"A", "B", "C", "D"}:
                    raise ValueError(
                        f"Section {section_name}, MCQ {question.get('number')} "
                        "does not have exactly four options."
                    )
                expected_keys.add((
                    section_name, "multiple_choice", question["number"]
                ))

            for question in actual_short:
                expected_keys.add((
                    section_name, "short_answer", question["number"]
                ))

            for question in actual_structured:
                number = question["number"]
                maximum = float(question["marks"])
                sub_questions = question.get("sub_questions", [])

                sub_marks = sum(
                    float(part.get("marks", 0))
                    for part in sub_questions
                )

                if not sub_questions or abs(sub_marks - maximum) > 0.01:
                    raise ValueError(
                        f"Section {section_name}, question {number}: "
                        "sub-question marks do not match the question total."
                    )

                expected_keys.add((section_name, "structured", number))

        answer_keys = paper.get("answer_key", [])
        actual_keys = set()

        for entry in answer_keys:
            identity = (
                str(entry.get("section")),
                entry.get("question_type"),
                entry.get("question_number")
            )

            if identity in actual_keys:
                raise ValueError(f"Duplicate answer key: {identity}")

            actual_keys.add(identity)

            if entry.get("question_type") == "multiple_choice":
                if entry.get("correct_answer") not in ("A", "B", "C", "D"):
                    raise ValueError(
                        f"Invalid MCQ answer in Section {identity[0]}, "
                        f"question {identity[2]}."
                    )

        if actual_keys != expected_keys:
            raise ValueError(
                "Answer keys do not match generated questions. "
                f"Missing: {expected_keys - actual_keys}; "
                f"unexpected: {actual_keys - expected_keys}"
            )

        for section in generated_sections:
            section_name = str(section["name"])

            for question in section.get("questions", []):
                if question.get("type") != "structured":
                    continue

                entry = next(
                    (
                        item for item in answer_keys
                        if str(item.get("section")) == section_name
                        and str(item.get("question_number")) == str(question["number"])
                    ),
                    None
                )

                if entry is None:
                    raise ValueError(
                        f"Missing marking guide for {section_name}-{question['number']}."
                    )

                guide = entry.get("marking_guide", [])
                guide_marks = sum(
                    float(point.get("marks", 0))
                    for point in guide
                    if isinstance(point, dict)
                )

                if not guide or abs(guide_marks - float(question["marks"])) > 0.01:
                    raise ValueError(
                        f"Marking guide total is incorrect for "
                        f"{section_name}-{question['number']}."
                    )

        return True

    async def generate_exam(self, paper_number, exam_version=1):
        allocation = self.allocator.allocate(
            paper_number,
            exam_version=exam_version
        )

        context = await self._retrieve_context(allocation)

        if not any(context.values()):
            raise RuntimeError(
                "No reference material was retrieved from Pinecone. "
                "Generation stopped."
            )

        generated_sections = []
        all_answer_keys = []

        for section_allocation in allocation["sections"]:
            section_name = str(section_allocation["name"])
            items = section_allocation.get("questions", [])

            print(f"Generating Section {section_name}...")

            questions = []
            section_answers = []

            if section_name == "A":
                mcq_items = [
                    item for item in items
                    if item.get("question_type") == "multiple_choice"
                ]
                short_items = [
                    item for item in items
                    if item.get("question_type") == "short_answer"
                ]

                mcqs, mcq_answers = await self._generate_section_a_batch(
                    "multiple_choice", mcq_items, context
                )
                short_questions, short_answers = await self._generate_section_a_batch(
                    "short_answer",
                    short_items,
                    context,
                    start_number=len(mcqs) + 1
                )

                questions = mcqs + short_questions
                section_answers = mcq_answers + short_answers

            else:
                for item in items:
                    question_type = item.get("question_type")

                    if question_type == "section_specific":
                        question, answer = await self._generate_section_specific_question(
                            item, context, section_name
                        )
                    elif question_type == "structured":
                        question, answer = await self._generate_structured_question(
                            item, context, section_name
                        )
                    else:
                        raise ValueError(
                            f"Unsupported allocation type in Section "
                            f"{section_name}: {question_type}"
                        )

                    questions.append(question)
                    section_answers.append(answer)

            section = {
                "name": section_name,
                "description": section_allocation.get("description"),
                "total_marks": section_allocation.get("total_marks"),
                "questions": questions
            }

            for field in (
                "questions_available",
                "questions_to_answer",
                "marks_offered",
                "marks_attempted"
            ):
                if field in section_allocation:
                    section[field] = section_allocation[field]

            generated_sections.append(section)
            all_answer_keys.extend(section_answers)

        paper = {
            "paper_number": allocation["paper_number"],
            "subject": allocation["subject"],
            "duration_minutes": allocation["duration_minutes"],
            "total_marks": allocation["total_marks"],
            "exam_version": exam_version,
            "sections": generated_sections,
            "answer_key": all_answer_keys,
            "generation_model": GEMINI_MODEL_NAME(),
            "reference_sources": sorted({
                item["source"]
                for topic_items in context.values()
                for item in topic_items
            })
        }

        self._validate_paper(paper, allocation)

        print("Exam generation and structural validation completed.")
        return paper

def GEMINI_MODEL_NAME():
    return getattr(gemini_service, "last_successful_model", None)


examiner_manager = ExaminerManager()




