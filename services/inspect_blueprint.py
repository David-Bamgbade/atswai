from services.exam_blueprint import ExamBlueprint
import json


def main():
    examiner = ExamBlueprint()

    for paper_number in [1, 2, 4]:
        blueprint = examiner.build(paper_number)

        print("\n" + "=" * 70)
        print(f"PAPER {paper_number}: {blueprint['subject']}")
        print("=" * 70)

        print("\nSECTIONS:")
        print(json.dumps(blueprint["sections"], indent=4))

        print("\nFIRST THREE TOPICS:")
        print(json.dumps(blueprint["topics"][:3], indent=4))


if __name__ == "__main__":
    main()