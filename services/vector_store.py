
from pinecone import Pinecone, TextQuery

from config import PINECONE_API_KEY, PINECONE_INDEX_NAME


class VectorStore:
    def __init__(self):
        if not PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY is missing from .env")

        self.client = Pinecone(api_key=PINECONE_API_KEY)
        self.index = self.client.Index(PINECONE_INDEX_NAME)

    def get_index_stats(self):
        return self.index.describe_index_stats()

    def search(self, question, top_k=5):
        response = self.index.documents.search(
            namespace="__default__",
            top_k=top_k,
            score_by=[
                TextQuery(
                    query=question,
                    fields=["text"]
                )
            ],
            include_fields=[
                "text",
                "source",
                "chunk_index",
                "type"
            ]
        )

        results = []

        for doc in response.matches:
            results.append({
                "id": doc.id,
                "score": doc.score,
                "text": getattr(doc, "text", ""),
                "source": getattr(doc, "source", "Unknown source"),
                "chunk_index": getattr(doc, "chunk_index", None),
                "type": getattr(doc, "type", None)
            })

        return results


vector_store = VectorStore()
