import os
import json
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

# Load environment variables (if you want flexibility for DB path)
load_dotenv()

# Paths
DB_PATH = os.getenv("CHROMA_PATH", "chroma_db")
DATA_FILE = os.getenv("DATA_FILE", "dataset.json")
COLLECTION_NAME = "travel"

def main():
    # Ensure database directory exists
    os.makedirs(DB_PATH, exist_ok=True)

    # Initialize Chroma client
    client = chromadb.PersistentClient(path=DB_PATH)
    ef = embedding_functions.DefaultEmbeddingFunction()

    # Reset collection if exists
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"🗑️ Deleted old collection: {COLLECTION_NAME}")
    except Exception:
        print(f"ℹ️ No existing collection to delete")

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef
    )

    # Load dataset
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"❌ Error loading {DATA_FILE}: {e}")
            return

    ids, docs, metadatas = [], [], []

    # Process dataset rows
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            print(f"⚠️ Skipping invalid row: {item}")
            continue

        ids.append(str(i))  # unique ID
        docs.append(item.get("content", f"{item.get('type','unknown')} - {item.get('name','unnamed')}"))

        # Only keep simple metadata
        clean_meta = {}
        for k, v in item.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                clean_meta[k] = v
            else:
                clean_meta[k] = json.dumps(v)  # flatten objects

        metadatas.append(clean_meta)

    # Insert into collection
    if ids:
        collection.add(ids=ids, documents=docs, metadatas=metadatas)
        print(f"✅ Ingested {len(ids)} items into collection '{COLLECTION_NAME}' at {DB_PATH}")
    else:
        print("⚠️ No valid items found in dataset")

if __name__ == "__main__":
    main()
