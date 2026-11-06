
import json
import re
from pathlib import Path


class SyllabusInspector:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent

        self.papers_dir = (
            self.project_root
            / "data"
            / "extracted"
            / "papers"
        )

        self.output_dir = (
            self.project_root
            / "data"
            / "extracted"
        )

        self.keywords = [
            "structure of the paper",
            "structure of examination",
            "examination structure",
            "specification grid",
            "examination",
            "multiple choice",
            "short answer",
            "compulsory",
            "answer any",
            "duration",
            "hours",
            "marks",
            "weighting",
            "percentage",
        ]

    def load_paper(self, file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def inspect_paper(self, paper):
        results = []

        for page in paper["pages"]:
            page_text = page["text"]
            lines = page_text.splitlines()

            for index, line in enumerate(lines):
                normalized_line = line.lower()

                matched_keywords = [
                    keyword
                    for keyword in self.keywords
                    if keyword in normalized_line
                ]

                if not matched_keywords:
                    continue

                start = max(0, index - 3)
                end = min(len(lines), index + 5)

                excerpt = "\n".join(lines[start:end])

                results.append({
                    "page": page["page"],
                    "matched_keywords": matched_keywords,
                    "excerpt": excerpt
                })

        return results

    def analyze(self):
        if not self.papers_dir.exists():
            raise FileNotFoundError(
                "Extracted papers directory does not exist."
            )

        paper_files = sorted(self.papers_dir.glob("paper_*.json"))

        if len(paper_files) != 12:
            raise ValueError(
                f"Expected 12 paper files, found {len(paper_files)}."
            )

        report = []

        for file_path in paper_files:
            paper = self.load_paper(file_path)

            findings = self.inspect_paper(paper)

            report.append({
                "paper_number": paper["paper_number"],
                "subject": paper["subject"],
                "start_page": paper["start_page"],
                "end_page": paper["end_page"],
                "findings": findings
            })

            print(
                f"Inspected Paper {paper['paper_number']}: "
                f"{paper['subject']} "
                f"({len(findings)} relevant passages)"
            )

        report_path = (
            self.output_dir
            / "examination_structure_findings.json"
        )

        with open(report_path, "w", encoding="utf-8") as file:
            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )

        print("\nInspection completed.")
        print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    inspector = SyllabusInspector()
    inspector.analyze()
