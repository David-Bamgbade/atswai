from services.gemini_service import gemini_service
import asyncio


async def main():
    prompt = """
    Explain the responsibilities of an external auditor
    in three sentences.
    """

    try:
        result = await gemini_service.generate(prompt)

        print("\nSUCCESS!")
        print("Model used:", result["model"])
        print("\nResponse:")
        print(result["answer"])

    except Exception as error:
        print("\nGEMINI ERROR:")
        print(error)


if __name__ == "__main__":
    asyncio.run(main())
