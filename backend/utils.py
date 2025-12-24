import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

# Initialize embeddings (must match the engine)
embeddings = OllamaEmbeddings(model="nomic-embed-text")


async def process_pdf(file):
    """
    Takes an uploaded file, saves it, splits it into chunks,
    and saves it to the local Chroma vector DB.
    """
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())

    try:
        # Load the PDF
        loader = PyPDFLoader(temp_path)
        documents = loader.load()

        # Split the PDF into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
        )
        chunks = text_splitter.split_documents(documents)

        # Save chunks to ChromaDB
        Chroma.from_documents(
            documents=chunks,
            embedding_function=embeddings,
            persist_directory="./data"
        )

    finally:
        # Remove temporary PDF
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return len(chunks)
