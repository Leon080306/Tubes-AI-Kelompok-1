
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from config.llm import embeddings


# =========================================
# CONFIGURATION
# =========================================

ROOT_DIR = Path(__file__).resolve().parent

KNOWLEDGE_BASE_DIR = ROOT_DIR / "knowledge_base"

VECTORSTORE_DIR = ROOT_DIR / "vectorstore" / "chroma_db"

COLLECTION_NAME = "sql_optimization_knowledge"


# =========================================
# DOCUMENT CATEGORIES
# =========================================

CATEGORY_MAPPING = {
    "indexing_best_practices.md": "indexing",
    "composite_index.md": "indexing",
    "query_optimization.md": "query_optimization",
    "execution_plan.md": "execution_plan"
}


# =========================================
# INITIALIZE VECTOR STORE
# =========================================

def create_vector_store():

    VECTORSTORE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(VECTORSTORE_DIR),
        collection_metadata={
            "hnsw:space": "cosine"
        }
    )


# =========================================
# LOAD KNOWLEDGE BASE DOCUMENTS
# =========================================

def load_documents():

    documents = []

    for file_path in KNOWLEDGE_BASE_DIR.glob("*.md"):

        content = file_path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            print(f"[SKIPPED] Empty document: {file_path.name}")
            continue

        category = CATEGORY_MAPPING.get(
            file_path.name,
            "general"
        )

        title = content.splitlines()[0].lstrip("# ").strip()

        document = Document(
            page_content=content,
            metadata={
                "source": file_path.name,
                "title": title,
                "category": category
            }
        )

        documents.append(document)

        print(f"[LOADED] {file_path.name}")

    if not documents:
        raise RuntimeError(
            "No Markdown documents found in knowledge_base/."
        )

    return documents


# =========================================
# SPLIT DOCUMENTS INTO CHUNKS
# =========================================

def split_documents(documents):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
        add_start_index=True
    )

    chunks = splitter.split_documents(documents)

    for index, chunk in enumerate(chunks):

        chunk.metadata["chunk_id"] = index

    return chunks


# =========================================
# BUILD VECTOR DATABASE
# =========================================

def build_knowledge_base():

    print("\nLoading Knowledge Base Documents...")

    documents = load_documents()

    print(f"\nTotal documents: {len(documents)}")

    print("\nSplitting documents into chunks...")

    chunks = split_documents(documents)

    print(f"Total chunks: {len(chunks)}")

    print("\nInitializing ChromaDB...")

    vector_store = create_vector_store()

    # Rebuild only this dedicated collection to avoid duplicates
    print("\nRebuilding knowledge collection...")

    vector_store.delete_collection()

    vector_store = create_vector_store()

    # Stable IDs make each chunk identifiable
    ids = [
        f"{chunk.metadata['source']}::{index}"
        for index, chunk in enumerate(chunks)
    ]

    print("\nGenerating embeddings and storing documents...")

    vector_store.add_documents(
        documents=chunks,
        ids=ids
    )

    print("\n===================================")
    print("KNOWLEDGE BASE BUILD COMPLETED")
    print("===================================")

    print(f"Documents : {len(documents)}")
    print(f"Chunks    : {len(chunks)}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Storage   : {VECTORSTORE_DIR}")


if __name__ == "__main__":
    build_knowledge_base()
