
import json
import math
import re
from copy import deepcopy
from pathlib import Path


class QuestionAllocator:
    """
    Allocates examination questions using:
    - The official examination blueprint.
    - Validated syllabus topic weightings.
    - Existing extracted syllabus JSON files.

    Syllabus section headings are detected from the content
    beginning at the Contents heading.
    """

    def __init__(
        self,
        exam_blueprint,
        data_directory="data/extracted/papers"
    ):
        self.exam_blueprint = exam_blueprint
        self.data_directory = Path(data_directory)

    # ---------------------------------------------------------
    # 1. LOAD EXTRACTED PAPER
    # ---------------------------------------------------------

    def _load_paper_data(self, paper_number):
        pattern = f"paper_{paper_number:02d}_*.json"
        matches = list(self.data_directory.glob(pattern))

        if not matches:
            raise FileNotFoundError(
                f"Extracted syllabus not found for Paper {paper_number}: "
                f"{pattern}"
            )

        with open(matches[0], "r", encoding="utf-8") as file:
            return json.load(file)

    # ---------------------------------------------------------
    # 2. NORMALIZE TEXT
    # ---------------------------------------------------------

    @staticmethod
    def _normalize(text):
        text = str(text).upper()
        text = re.sub(r"[^A-Z0-9\s]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _clean_topic_name(topic):
        return re.sub(
            r"^\s*\d+[\.\)]?\s*",
            "",
            topic
        ).strip()

    # ---------------------------------------------------------
    # 3. GET SYLLABUS CONTENT AFTER CONTENTS
    # ---------------------------------------------------------

    
    def _get_syllabus_pages(self, paper_data, topics):
        """
        Find the beginning of the actual syllabus content.

        First tries the Contents heading. If it is absent,
        starts from the first page containing a known syllabus topic.
        """

        pages = paper_data.get("pages", [])

        for index, page in enumerate(pages):
            page_text = page.get("text", "")

            match = re.search(
                r"\bCONTENTS\b",
                page_text,
                re.IGNORECASE
            )

            if match:
                syllabus_pages = []

                for page_index, item in enumerate(pages[index:]):
                    text = item.get("text", "")

                    if page_index == 0:
                        text = text[match.end():]

                    syllabus_pages.append({
                        "page": item.get("page"),
                        "text": text
                    })

                return syllabus_pages

        # Fallback: locate the first actual syllabus topic.
        for index, page in enumerate(pages):
            normalized_text = self._normalize(
                page.get("text", "")
            )

            for topic in topics:
                topic_name = self._normalize(
                    self._clean_topic_name(topic["topic"])
                )

                if topic_name and topic_name in normalized_text:
                    return [
                        {
                            "page": item.get("page"),
                            "text": item.get("text", "")
                        }
                        for item in pages[index:]
                    ]

        raise ValueError(
            f"Could not locate syllabus content for "
            f"Paper {paper_data.get('paper_number')}."
        )


    # ---------------------------------------------------------
    # 4. DETECT SYLLABUS SECTION HEADINGS
    # ---------------------------------------------------------

    def _extract_section_headings(self, syllabus_pages):
        """
        Detect headings in either format:

        SECTION A: MICROECONOMICS

        or:

        SECTION A:
        MICROECONOMICS

        Headings are detected only after Contents.
        """

        headings = []

        for page in syllabus_pages:
            lines = page["text"].splitlines()

            for index, line in enumerate(lines):
                match = re.match(
                    r"^\s*SECTION\s+([A-Z0-9]+)\s*:\s*(.*?)\s*$",
                    line,
                    re.IGNORECASE
                )

                if not match:
                    continue

                section_letter = match.group(1).strip()
                heading_name = match.group(2).strip()

                # The heading name may be on the next line.
                if not heading_name:
                    for next_index in range(index + 1, len(lines)):
                        candidate = lines[next_index].strip()

                        if not candidate:
                            continue

                        # Avoid treating another section label
                        # as the heading name.
                        if re.match(
                            r"^SECTION\s+[A-Z0-9]+\s*:",
                            candidate,
                            re.IGNORECASE
                        ):
                            break

                        heading_name = candidate
                        break

                if heading_name:
                    headings.append({
                        "section": section_letter,
                        "heading": heading_name,
                        "page": page["page"]
                    })

        return headings

    # ---------------------------------------------------------
    # 5. FIND TOPIC LOCATIONS
    # ---------------------------------------------------------

    
    def _find_topic_location(self, topic, syllabus_pages):
        """
        Locate a syllabus topic heading.

        Supports numbered headings and lettered headings used
        in Paper 12, while matching the actual topic title.
        """

        original_topic = topic["topic"].strip()

        match = re.match(
            r"^\s*(?:\((\d+)\)|(\d+)[\.\)]?|([a-z])[\.\)])\s*(.+)$",
            original_topic,
            re.IGNORECASE
        )

        if not match:
            return None

        topic_name = self._normalize(match.group(4))

        for page_index, page in enumerate(syllabus_pages):
            normalized_text = self._normalize(page["text"])

            position = normalized_text.find(topic_name)

            if position >= 0:
                return {
                    "page": page["page"],
                    "page_index": page_index,
                    "position": position
                }

        return None


    # 6. ASSOCIATE TOPICS WITH HEADINGS
    # ---------------------------------------------------------

    def _classify_topics(self, topics, syllabus_pages, headings):
        """
        A topic belongs to the most recent preceding syllabus
        section heading.

        Page position is considered as well as position within
        the page, so a heading and topic on the same page are
        handled correctly.
        """

        classified_topics = []

        heading_locations = []

        for heading in headings:
            page_index = next(
                (
                    index
                    for index, page in enumerate(syllabus_pages)
                    if page["page"] == heading["page"]
                ),
                None
            )

            if page_index is None:
                continue

            page_text = syllabus_pages[page_index]["text"]

            # Find the section label in the original page text.
            match = re.search(
                rf"SECTION\s+{re.escape(heading['section'])}\s*:",
                page_text,
                re.IGNORECASE
            )

            if match:
                heading_locations.append({
                    **heading,
                    "page_index": page_index,
                    "position": match.start()
                })

        for topic in topics:
            topic_copy = deepcopy(topic)

            location = self._find_topic_location(
                topic,
                syllabus_pages
            )

            topic_copy["syllabus_section"] = None
            topic_copy["source_page"] = None

            if location:
                topic_copy["source_page"] = location["page"]

                preceding_headings = [
                    heading
                    for heading in heading_locations
                    if (
                        heading["page_index"],
                        heading["position"]
                    ) <= (
                        location["page_index"],
                        location["position"]
                    )
                ]

                if preceding_headings:
                    latest_heading = max(
                        preceding_headings,
                        key=lambda heading: (
                            heading["page_index"],
                            heading["position"]
                        )
                    )

                    topic_copy["syllabus_section"] = (
                        latest_heading["heading"]
                    )

            classified_topics.append(topic_copy)

        return classified_topics

    # ---------------------------------------------------------
    # 7. MATCH EXAMINATION SECTION TO SYLLABUS GROUP
    # ---------------------------------------------------------

    def _topics_for_section(self, topics, section):
        """
        Allocate Economics topics to their correct examination sections.

        Microeconomics covers topics 1-5.
        Macroeconomics covers topics 6-12.
        """

        description = self._normalize(
            section.get("description", "")
        )

        requested_group = None

        if "MICROECONOMICS" in description:
            requested_group = "MICROECONOMICS"

        elif "MACROECONOMICS" in description:
            requested_group = "MACROECONOMICS"

        if requested_group:
            matching_topics = []

            for topic in topics:
                match = re.match(
                    r"^\s*(\d+)",
                    topic.get("topic", "")
                )

                if not match:
                    continue

                topic_number = int(match.group(1))

                if requested_group == "MICROECONOMICS":
                    if 1 <= topic_number <= 5:
                        matching_topics.append(topic)

                elif requested_group == "MACROECONOMICS":
                    if 6 <= topic_number <= 12:
                        matching_topics.append(topic)

            if not matching_topics:
                raise ValueError(
                    f"No topics found for {requested_group}."
                )

            return matching_topics

        return topics
    

    # ---------------------------------------------------------
    # 8. DISTRIBUTE QUESTION COUNTS BY WEIGHTING
    # ---------------------------------------------------------

    def _distribute_question_counts(self, topics, question_count):
        """
        Largest-remainder allocation.

        The result always adds up to the exact question count.
        """

        if not topics:
            raise ValueError("No topics available for allocation.")

        if question_count <= 0:
            return [0] * len(topics)

        total_weight = sum(
            float(topic["weighting"])
            for topic in topics
        )

        if total_weight <= 0:
            raise ValueError("Topic weightings must be positive.")

        exact_counts = [
            question_count
            * float(topic["weighting"])
            / total_weight
            for topic in topics
        ]

        counts = [
            math.floor(value)
            for value in exact_counts
        ]

        remaining = question_count - sum(counts)

        order = sorted(
            range(len(topics)),
            key=lambda index: (
                exact_counts[index] - counts[index]
            ),
            reverse=True
        )

        for index in order[:remaining]:
            counts[index] += 1

        return counts

    # ---------------------------------------------------------
    # 9. COMPULSORY QUESTIONS
    # ---------------------------------------------------------

    def _allocate_compulsory_questions(self,topics,question_count,marks_per_question,question_type):

        if question_count <= 0:
            return []

        counts = self._distribute_question_counts(
            topics,
            question_count
        )

        questions = []

        for topic, count in zip(topics, counts):
            if count == 0:
                continue

            questions.append({
                "topic": topic["topic"],
                "question_type": question_type,
                "question_count": count,
                "marks_per_question": marks_per_question,
                "allocated_marks": round(
                    count * marks_per_question,
                    2
                ),
                "compulsory": True
            })

        return questions

    # ---------------------------------------------------------
    # 10. OPTIONAL STRUCTURED QUESTIONS
    # ---------------------------------------------------------

    def _allocate_optional_questions(
        self,
        topics,
        section,
        exam_version=1
    ):
        """Allocate optional questions using weighted topic rotation."""

        available = section["questions_available"]
        to_answer = section["questions_to_answer"]
        marks_per_question = section["marks_per_question"]

        if not topics:
            raise ValueError("No topics available for allocation.")

        if exam_version < 1:
            raise ValueError("Exam version must be at least 1.")

        ranked_topics = sorted(
            topics,
            key=lambda topic: float(topic["weighting"]),
            reverse=True
        )

        topic_count = len(ranked_topics)

        start_index = (
            (exam_version - 1)
        ) % topic_count

        rotated_topics = (
            ranked_topics[start_index:]
            + ranked_topics[:start_index]
        )

        selected_topics = rotated_topics[:min(available, topic_count)]

        counts = {
            topic["topic"]: 1
            for topic in selected_topics
        }

        remaining = available - len(selected_topics)

        if remaining > 0:
            extra_counts = self._distribute_question_counts(
                selected_topics,
                remaining
            )

            for topic, count in zip(selected_topics, extra_counts):
                counts[topic["topic"]] += count

        questions = []
        question_number = 1

        for topic in selected_topics:
            for _ in range(counts[topic["topic"]]):
                questions.append({
                    "question_number": question_number,
                    "topic": topic["topic"],
                    "question_type": "structured",
                    "marks": marks_per_question,
                    "compulsory": False
                })

                question_number += 1

        return {
            "questions": questions,
            "questions_available": available,
            "questions_to_answer": to_answer,
            "marks_offered": round(
                available * marks_per_question, 2
            ),
            "marks_attempted": round(
                to_answer * marks_per_question, 2
            )
        }

    # ---------------------------------------------------------
    # 11. BUILD PAPER ALLOCATION
    # ---------------------------------------------------------

    def allocate(self, paper_number, exam_version=1):
        blueprint = self.exam_blueprint.build(paper_number)

        paper_data = self._load_paper_data(paper_number)

        syllabus_pages = self._get_syllabus_pages(paper_data,blueprint["topics"])

        headings = self._extract_section_headings(
            syllabus_pages
        )

        topics = self._classify_topics(
            deepcopy(blueprint["topics"]),
            syllabus_pages,
            headings
        )

        result = {
            "paper_number": paper_number,
            "subject": blueprint["subject"],
            "duration_minutes": blueprint.get(
                "duration_minutes",
                180
            ),
            "total_marks": blueprint["total_marks"],
            "detected_syllabus_sections": headings,
            "sections": []
        }

        for section in deepcopy(blueprint["sections"]):
            section_topics = self._topics_for_section(
                topics,
                section
            )

            section_result = {
                "name": section["name"],
                "description": section["description"],
                "total_marks": section["total_marks"],
                "questions": [],
                "topic_coverage": [
                    topic["topic"]
                    for topic in section_topics
                ]
            }

            # Objective and short-answer questions
            if "question_types" in section:
                question_types = section["question_types"]

                mcq_count = question_types.get(
                    "multiple_choice",
                    0
                )

                short_answer_count = question_types.get(
                    "short_answer",
                    0
                )

                total_questions = (
                    mcq_count + short_answer_count
                )

                if total_questions:
                    marks_per_question = (
                        section["total_marks"] / total_questions
                    )

                    section_result["questions"].extend(
                        self._allocate_compulsory_questions(
                            section_topics,
                            mcq_count,
                            marks_per_question,
                            "multiple_choice"
                        )
                    )

                    section_result["questions"].extend(
                        self._allocate_compulsory_questions(
                            section_topics,
                            short_answer_count,
                            marks_per_question,
                            "short_answer"
                        )
                    )

            # Optional structured questions
            elif "questions_available" in section:
                section_result.update(
                    self._allocate_optional_questions(
                        section_topics,
                        section,
                        exam_version
                    )
                )

            # Other compulsory sections
            else:
                section_result["questions"].append({
                    "question_type": "section_specific",
                    "question_count": section.get(
                        "question_count",
                        1
                    ),
                    "marks": section["total_marks"],
                    "compulsory": True,
                    "topics": [
                        {
                            "topic": topic["topic"],
                            "weighting": topic["weighting"]
                        }
                        for topic in section_topics
                    ]
                })

            result["sections"].append(section_result)

        self._validate_allocation(result)

        return result

    # ---------------------------------------------------------
    # 12. VALIDATE ALLOCATION
    # ---------------------------------------------------------

    def _validate_allocation(self, result):
        section_total = sum(
            section["total_marks"]
            for section in result["sections"]
        )

        if abs(section_total - result["total_marks"]) > 0.01:
            raise ValueError(
                f"Paper {result['paper_number']} section marks "
                f"total {section_total}, expected "
                f"{result['total_marks']}."
            )

        for section in result["sections"]:
            if "questions_available" not in section:
                continue

            expected_available = section["questions_available"]
            actual_available = len(section["questions"])

            if actual_available != expected_available:
                raise ValueError(
                    f"Section {section['name']} should offer "
                    f"{expected_available} questions, but "
                    f"{actual_available} were allocated."
                )

    # ---------------------------------------------------------
    # 13. DISPLAY
    # ---------------------------------------------------------

    def display(self, paper_number):
        allocation = self.allocate(paper_number)

        print("\n" + "=" * 70)
        print(
            f"PAPER {allocation['paper_number']}: "
            f"{allocation['subject']}"
        )
        print("=" * 70)

        print("\nDETECTED SYLLABUS SECTIONS:")

        for heading in allocation["detected_syllabus_sections"]:
            print(
                f"Page {heading['page']}: "
                f"Section {heading['section']} - "
                f"{heading['heading']}"
            )

        for section in allocation["sections"]:
            print(f"\nSECTION {section['name']}")
            print(f"Description: {section['description']}")
            print(f"Marks: {section['total_marks']}")

            print("\nTopic coverage:")

            for topic in section["topic_coverage"]:
                print(f"- {topic}")

            print("\nQuestion allocation:")

            for question in section["questions"]:
                print(question)

            if "marks_offered" in section:
                print(
                    f"\nMarks offered: {section['marks_offered']}"
                )
                print(
                    f"Marks attempted: {section['marks_attempted']}"
                )


if __name__ == "__main__":
    from services.exam_blueprint import ExamBlueprint

    blueprint = ExamBlueprint()
    allocator = QuestionAllocator(blueprint)

    for paper_number in [1, 2, 4]:
        allocator.display(paper_number)
