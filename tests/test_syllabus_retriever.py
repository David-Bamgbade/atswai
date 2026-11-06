
from services.syllabus_retriever import syllabus_retriever


def test_syllabus_retriever():

    result = syllabus_retriever.retrieve_subject(
        subject="Basic Accounting",
        paper="Part I Paper 1",
        top_k=20
    )

    print("\nSUBJECT:", result["subject"])
    print("PAPER:", result["paper"])
    print("SOURCE:", result["source"])
    print("CHUNKS RETRIEVED:", result["chunk_count"])

    print("\n" + "=" * 80)

    for chunk in result["chunks"]:

        print("\nCHUNK:", chunk["chunk_index"])
        print("-" * 80)
        print(chunk["text"])

    context = syllabus_retriever.build_context(result)

    assert result["subject"] == "Basic Accounting"
    assert result["source"] == (
        "ATSWA_NEW_SYLLABUS_EFFECTIVE_SEPTEMBER_2026"
    )
    assert result["chunk_count"] > 0
    assert context.strip()

    print("\nSyllabus retrieval tests passed.")


if __name__ == "__main__":
    test_syllabus_retriever()
