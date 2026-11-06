import asyncio
from services.vector_store import vector_store


QUERIES = [
    "ATSWA PART I examination PAPER 1 PAPER 2 PAPER 3 PAPER 4 subject names",
    "ATSWA PART II examination PAPER 5 PAPER 6 PAPER 7 PAPER 8 subject names",
    "ATSWA PART III examination PAPER 9 PAPER 10 PAPER 11 PAPER 12 subject names",
    "ATSWA official syllabus contents page list of all twelve papers",
    "ATSWA examination structure specification grid duration marks Section A Section B",
]


async def test_syllabus_retrieval():

    seen = set()

    for query in QUERIES:

        print("\n\n" + "#" * 85)
        print("QUERY:", query)
        print("#" * 85)

        results = await vector_store.search(query, top_k=20)

        for result in results:

            if result["source"] != (
                "ATSWA_NEW_SYLLABUS_EFFECTIVE_SEPTEMBER_2026"
            ):
                continue

            key = (
                result["source"],
                result["chunk_index"]
            )

            if key in seen:
                continue

            seen.add(key)

            print("\n" + "=" * 85)
            print("CHUNK:", result["chunk_index"])
            print("SCORE:", result["score"])
            print("=" * 85)
            print(result["text"])

    print("\nUnique official syllabus chunks:", len(seen))


if __name__ == "__main__":
    asyncio.run(test_syllabus_retrieval())
