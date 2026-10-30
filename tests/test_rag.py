
from services.rag_service import rag_service


question = "What are the responsibilities of an external auditor?"

try:

    response = rag_service.ask(
        question=question,
        mode="study",
        top_k=5
    )

    print("\nATSWA STUDY ASSISTANT")
    print("=" * 50)

    print("\nQUESTION:")
    print(question)

    print("\nANSWER:")
    print(response["answer"])

    print("\nMODE:")
    print(response["mode"])

    print("\nMODEL:")
    print(response["model"])

    print("\nREFERENCES:")

    for source in response["sources"]:
        print(f"- {source['source']}")

    print("\n" + "=" * 50)

except Exception as error:
    print("\nRAG ERROR:")
    print(error)
