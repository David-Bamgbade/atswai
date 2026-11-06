import asyncio
from services.vector_store import vector_store


async def main():
    question = "What are the responsibilities of an auditor?"

    try:
        results = await vector_store.search(question, top_k=5)

        print(f"\nFound {len(results)} results.\n")

        for i, result in enumerate(results, start=1):
            print(f"RESULT {i}")
            print("Source:", result["source"])
            print("Score:", result["score"])
            print("Chunk:", result["chunk_index"])
            print("Text:", result["text"][:500])
            print("-" * 70)

    except Exception as error:
        print("\nPINECONE ERROR:")
        print(error)


if __name__ == "__main__":
    asyncio.run(main())
