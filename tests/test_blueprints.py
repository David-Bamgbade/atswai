from services.exam_blueprint import ExamBlueprint


def main():
    examiner = ExamBlueprint()

    print("\nATSWA BLUEPRINT VALIDATION")
    print("=" * 75)

    for paper_number in range(1, 13):
        blueprint = examiner.build(paper_number)

        section_marks = sum(
            section["total_marks"]
            for section in blueprint["sections"]
        )

        topic_marks = sum(
            topic["target_marks"]
            for topic in blueprint["topics"]
        )

        print(
            f'Paper {blueprint["paper_number"]:02d}: '
            f'{blueprint["subject"]} | '
            f'Sections: {section_marks} marks | '
            f'Topics: {topic_marks:.2f} marks'
        )

        if section_marks != 100:
            print("  ERROR: Section marks do not total 100.")

        if abs(topic_marks - 100) > 0.01:
            print("  ERROR: Topic marks do not total 100.")

    print("=" * 75)
    print("Validation test completed.")


if __name__ == "__main__":
    main()