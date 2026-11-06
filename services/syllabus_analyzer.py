
import json
from pathlib import Path

from pypdf import PdfReader


class SyllabusAnalyzer:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent

        self.pdf_path = (
            self.project_root
            / "data"
            / "atswa_2026_syllabus.pdf"
        )

        self.output_dir = (
            self.project_root
            / "data"
            / "extracted"
        )

        self.papers_dir = self.output_dir / "papers"

        self.papers_dir.mkdir(parents=True, exist_ok=True)

        self.paper_names = {
            1: "Basic Accounting",
            2: "Economics",
            3: "Business Law",
            4: "Communication Skills",
            5: "Financial Accounting",
            6: "Public Sector Accounting",
            7: "Quantitative Analysis",
            8: "Information Technology",
            9: "Principles of Auditing and Assurance",
            10: "Cost Accounting",
            11: "Taxation",
            12: "Management",
        }

    def extract_pdf_text(self):
        if not self.pdf_path.exists():
            raise FileNotFoundError(
                f"ATSWA syllabus not found: {self.pdf_path}"
            )

        reader = PdfReader(str(self.pdf_path))

        pages = []

        for page_number, page in enumerate(reader.pages, start=1):
            pages.append({
                "page": page_number,
                "text": page.extract_text() or ""
            })

        return pages

    def load_analysis_report(self):
        report_path = self.output_dir / "analysis_report.json"

        if not report_path.exists():
            raise FileNotFoundError(
                "Analysis report not found. Run the analyser first."
            )

        with open(report_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def validate_headings(self, headings):
        detected_numbers = [
            item["paper_number"]
            for item in headings
        ]

        expected_numbers = list(self.paper_names.keys())

        if detected_numbers != expected_numbers:
            raise ValueError(
                "Paper headings are missing, duplicated, "
                "or out of order."
            )

        for index in range(len(headings) - 1):
            current_page = headings[index]["page"]
            next_page = headings[index + 1]["page"]

            if current_page >= next_page:
                raise ValueError(
                    "Invalid page boundaries detected."
                )

    def extract_papers(self, pages, headings):
        self.validate_headings(headings)

        extracted_papers = []

        for index, heading in enumerate(headings):
            paper_number = heading["paper_number"]

            start_page = heading["page"]

            if index + 1 < len(headings):
                end_page = headings[index + 1]["page"] - 1
            else:
                end_page = len(pages)

            paper_pages = [
                page for page in pages
                if start_page <= page["page"] <= end_page
            ]

            paper_text = "\n\n".join(
                page["text"]
                for page in paper_pages
            )

            paper_data = {
                "paper_number": paper_number,
                "subject": self.paper_names[paper_number],
                "start_page": start_page,
                "end_page": end_page,
                "total_pages": len(paper_pages),
                "pages": paper_pages,
                "full_text": paper_text
            }

            filename = (
                f"paper_{paper_number:02d}_"
                f"{self.paper_names[paper_number].lower().replace(' ', '_')}.json"
            )

            output_path = self.papers_dir / filename

            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(
                    paper_data,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

            extracted_papers.append({
                "paper_number": paper_number,
                "subject": self.paper_names[paper_number],
                "start_page": start_page,
                "end_page": end_page,
                "total_pages": len(paper_pages),
                "file": str(output_path)
            })

        return extracted_papers

    def save_manifest(self, extracted_papers):
        manifest = {
            "source": self.pdf_path.name,
            "total_papers": len(extracted_papers),
            "papers": extracted_papers
        }

        manifest_path = self.output_dir / "papers_manifest.json"

        with open(manifest_path, "w", encoding="utf-8") as file:
            json.dump(
                manifest,
                file,
                indent=4,
                ensure_ascii=False
            )

        return manifest_path

    def analyze(self):
        print("Reading ATSWA syllabus...")

        pages = self.extract_pdf_text()

        print(f"Extracted {len(pages)} PDF pages.")

        report = self.load_analysis_report()
        headings = report["detected_headings"]

        extracted_papers = self.extract_papers(
            pages,
            headings
        )

        manifest_path = self.save_manifest(extracted_papers)

        print("\nSuccessfully extracted papers:\n")

        for paper in extracted_papers:
            print(
                f"Paper {paper['paper_number']}: "
                f"{paper['subject']} | "
                f"Pages {paper['start_page']}-{paper['end_page']} | "
                f"{paper['total_pages']} pages"
            )

        print(f"\nTotal papers extracted: {len(extracted_papers)}")
        print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    analyzer = SyllabusAnalyzer()
    analyzer.analyze()
