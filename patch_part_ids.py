from pathlib import Path

path = Path("services/examiner_manager.py")
source = path.read_text(encoding="utf-8")

if "import math" not in source:
    source = "import math\n" + source

start = source.index("    async def _generate_structured_question(")
end = source.index("    def _validate_paper(", start)

new_block = r'''    def _assign_structured_part_ids(
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

'''

source = source[:start] + new_block + source[end:]
path.write_text(source, encoding="utf-8")
print("Updated examiner_manager.py successfully.")
