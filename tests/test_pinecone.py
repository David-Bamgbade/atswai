from services.vector_store import vector_store

try:
    stats = vector_store.get_index_stats()

    print("\nPinecone connection successful!")
    print("Index statistics:")
    print(stats)

except Exception as error:
    print("\nPinecone connection failed:")
    print(error)