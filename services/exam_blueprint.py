
import json
from pathlib import Path


class ExamBlueprint:

    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent

        self.weightings_path = (
            self.project_root
            / "data"
            / "extracted"
            / "validated_topic_weightings.json"
        )

        self.exam_duration_minutes = 180
        self.total_exam_marks = 100

        self.paper_formats = self._define_paper_formats()

        self.topic_data = self._load_topic_data()

    def _define_paper_formats(self):
        """
        Defines examination formats based on the
        ATSWA September 2026 syllabus.
        """

        standard_format = {
            "duration_minutes": 180,
            "total_marks": 100,
            "sections": [
                {
                    "name": "A",
                    "description": "Objective and short-answer questions",
                    "total_marks": 50,
                    "question_count": 50,
                    "compulsory": True,
                    "question_types": {
                        "multiple_choice": 30,
                        "short_answer": 20
                    }
                },
                {
                    "name": "B",
                    "description": "Structured and essay questions",
                    "total_marks": 50,
                    "questions_available": 6,
                    "questions_to_answer": 4,
                    "marks_per_question": 12.5,
                    "compulsory": False
                }
            ]
        }

        formats = {}

        # Papers using the standard two-section format.
        standard_papers = [
            3, 5, 6, 7, 8, 9, 10, 11, 12
        ]

        for paper_number in standard_papers:
            formats[paper_number] = json.loads(
                json.dumps(standard_format)
            )

        # Paper 1: Basic Accounting.
        formats[1] = json.loads(
            json.dumps(standard_format)
        )

        # Paper 2: Economics.
        formats[2] = {
            "duration_minutes": 180,
            "total_marks": 100,
            "sections": [
                {
                    "name": "A",
                    "description": "Objective and short-answer questions",
                    "total_marks": 50,
                    "question_count": 50,
                    "compulsory": True,
                    "question_types": {
                        "multiple_choice": 30,
                        "short_answer": 20
                    }
                },
                {
                    "name": "B",
                    "description": "Microeconomics",
                    "total_marks": 25,
                    "questions_available": 3,
                    "questions_to_answer": 2,
                    "marks_per_question": 12.5,
                    "compulsory": False
                },
                {
                    "name": "C",
                    "description": "Macroeconomics",
                    "total_marks": 25,
                    "questions_available": 3,
                    "questions_to_answer": 2,
                    "marks_per_question": 12.5,
                    "compulsory": False
                }
            ]
        }

        # Paper 4: Communication Skills.
        formats[4] = {
            "duration_minutes": 180,
            "total_marks": 100,
            "sections": [
                {
                    "name": "A",
                    "description": "Objective and short-answer questions",
                    "total_marks": 40,
                    "question_count": 40,
                    "compulsory": True,
                    "question_types": {
                        "multiple_choice": 20,
                        "short_answer": 20
                    }
                },
                {
                    "name": "B",
                    "description": "Comprehension or summary",
                    "total_marks": 30,
                    "question_count": 1,
                    "compulsory": True
                },
                {
                    "name": "C",
                    "description": "Communication skills questions",
                    "total_marks": 30,
                    "questions_available": 4,
                    "questions_to_answer": 2,
                    "marks_per_question": 15,
                    "compulsory": False
                }
            ]
        }

        return formats

    def _load_topic_data(self):
        if not self.weightings_path.exists():
            raise FileNotFoundError(
                "Validated topic weighting file not found: "
                f"{self.weightings_path}"
            )

        with open(
            self.weightings_path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        return {
            paper["paper_number"]: paper
            for paper in data
        }

    def _validate_paper(self, paper_number):
        if paper_number not in self.paper_formats:
            raise ValueError(
                f"Invalid ATSWA paper number: {paper_number}"
            )

        if paper_number not in self.topic_data:
            raise ValueError(
                f"Topic weighting data missing for Paper {paper_number}"
            )

        paper = self.topic_data[paper_number]

        total_weighting = sum(
            topic["weighting"]
            for topic in paper["topics"]
        )

        if abs(total_weighting - 100) > 0.01:
            raise ValueError(
                f"Paper {paper_number} has invalid topic weightings: "
                f"{total_weighting}%"
            )

    def _calculate_topic_targets(self, paper_number):
        paper = self.topic_data[paper_number]

        topic_targets = []

        for topic in paper["topics"]:
            weighting = topic["weighting"]

            target_marks = (
                weighting / 100
            ) * self.total_exam_marks

            topic_targets.append({
                "topic": topic["topic"],
                "weighting": weighting,
                "target_marks": round(target_marks, 2),
                "pdf_page": topic.get("pdf_page")
            })

        return topic_targets

    def build(self, paper_number):
        self._validate_paper(paper_number)

        topic_data = self.topic_data[paper_number]

        return {
            "paper_number": paper_number,
            "subject": topic_data["subject"],
            "duration_minutes": self.exam_duration_minutes,
            "total_marks": self.total_exam_marks,
            "sections": self.paper_formats[paper_number]["sections"],
            "topics": self._calculate_topic_targets(paper_number)
        }

    def build_all(self):
        blueprints = []

        for paper_number in range(1, 13):
            blueprints.append(
                self.build(paper_number)
            )

        return blueprints

    def display(self, paper_number):
        blueprint = self.build(paper_number)

        print("\n" + "=" * 75)
        print(
            f"ATSWA PAPER {blueprint['paper_number']}: "
            f"{blueprint['subject']}"
        )
        print("=" * 75)

        print(
            f"Duration: {blueprint['duration_minutes'] // 60} hours"
        )
        print(f"Total marks: {blueprint['total_marks']}")

        print("\nEXAMINATION SECTIONS")
        print("-" * 75)

        for section in blueprint["sections"]:
            print(
                f"\nSECTION {section['name']}: "
                f"{section['description']}"
            )

            print(f"Marks: {section['total_marks']}")

            if "question_count" in section:
                print(
                    f"Questions: {section['question_count']} "
                    "(compulsory)"
                )

            if "questions_available" in section:
                print(
                    f"Available: {section['questions_available']} | "
                    f"Answer: {section['questions_to_answer']}"
                )

            if "question_types" in section:
                for question_type, count in (
                    section["question_types"].items()
                ):
                    print(f"{question_type}: {count}")

        print("\nTOPIC MARK ALLOCATION")
        print("-" * 75)

        for topic in blueprint["topics"]:
            print(
                f"{topic['weighting']:>6.2f}% | "
                f"{topic['target_marks']:>6.2f} marks | "
                f"{topic['topic']}"
            )

        print("-" * 75)

        print(
            "Total topic marks:",
            sum(
                topic["target_marks"]
                for topic in blueprint["topics"]
            )
        )


if __name__ == "__main__":
    blueprint_engine = ExamBlueprint()

    # Test Paper 1 first.
    blueprint_engine.display(1)
