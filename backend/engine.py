import os
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

# Initialize Models
llm = OllamaLLM(model="llama3", temperature=0, num_ctx=2048)
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# Persistence directory
DATA_DIR = "./data"

# Global Vector DB instance
vector_db = Chroma(
    persist_directory=DATA_DIR,
    embedding_function=embeddings,
    collection_name="securesphere_collection" # Give it a specific name
)

PROMPT = PromptTemplate.from_template(
    """Use ONLY the context below to answer the question.
If the answer is not present, say "I don't know".

Context:
{context}

Question:
{question}

Answer:"""
)

def ingest_pdf(pdf_path: str):
    # Ensure we use ONLY the base filename (e.g., "test.pdf") for the filter
    filename = os.path.basename(pdf_path).lower()

    loader = PyPDFLoader(pdf_path)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)

    # Attach metadata to every chunk
    for chunk in chunks:
        chunk.metadata["filename"] = filename
    
    # Add to DB (Modern Chroma handles persistence automatically)
    vector_db.add_documents(chunks)
    
    return {"file": filename, "chunks": len(chunks)}

def ask_question(query: str, filename: str):
    clean_filename = filename.lower()
    
    # FIX: Use the specific "filter" syntax for Chroma
    docs = vector_db.similarity_search(
        query, 
        k=5, 
        filter={"filename": clean_filename}
    )

    if not docs:
        # Debugging: Print what's actually in the DB if search fails
        print(f"❌ No docs found for: {clean_filename}")
        return f"I don't know (no context found for {clean_filename})"

    context = "\n\n".join(d.page_content for d in docs)
    prompt = PROMPT.format(context=context, question=query)

    return llm.invoke(prompt)