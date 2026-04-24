"""Production-ready AI engine with error handling and timeouts"""
import os
import time
from typing import Optional, Dict, List
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.exceptions import LangChainException

from config import get_settings
from logger_config import logger

settings = get_settings()

# Initialize Models with error handling - lazy initialization
llm = None
embeddings = None
vector_db = None


def _initialize_models():
    """Lazy initialization of AI models"""
    global llm, embeddings, vector_db
    
    if llm is None:
        try:
            logger.info(f"Initializing AI models: LLM={settings.LLM_MODEL}, Embeddings={settings.EMBEDDING_MODEL}")
            # Use longer timeout for LLM - it can be slow (llama3 takes 60-100s sometimes)
            llm_timeout = max(settings.CHAT_TIMEOUT_SECONDS, 150)  # At least 150s for slow models
            logger.info(f"Setting LLM timeout to {llm_timeout}s")
            llm = OllamaLLM(
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                num_ctx=settings.LLM_CONTEXT_SIZE,
                timeout=llm_timeout
            )
            embeddings = OllamaEmbeddings(model=settings.EMBEDDING_MODEL)
            logger.info("AI models initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI models: {e}", exc_info=True)
            logger.warning("Make sure Ollama is running. You can start it with: ollama serve")
            raise RuntimeError(f"AI models initialization failed: {str(e)}. Make sure Ollama is running.")
    
    if vector_db is None:
        try:
            logger.info(f"Initializing vector database: {settings.DATA_DIR}")
            vector_db = Chroma(
                persist_directory=settings.DATA_DIR,
                embedding_function=embeddings,
                collection_name=settings.COLLECTION_NAME
            )
            logger.info("Vector database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}", exc_info=True)
            raise RuntimeError(f"Vector database initialization failed: {str(e)}")


# Try to initialize on import, but don't fail if Ollama isn't running yet
try:
    _initialize_models()
except Exception as e:
    logger.warning(f"Initial initialization failed: {e}. Models will be initialized on first use.")

PROMPT = PromptTemplate.from_template(
    """You are a helpful AI assistant. Use ONLY the context below to answer the question.
If the answer is not present in the context, say "I don't have enough information to answer this question based on the provided document."

Context:
{context}

Question:
{question}

Answer:"""
)

PROMPT_WITH_HISTORY = PromptTemplate.from_template(
    """You are a helpful AI assistant having a conversation about a document. Use the document context and previous conversation to answer the current question.
If the answer is not present in the context, say "I don't have enough information to answer this question based on the provided document."

Previous Conversation:
{conversation_history}

Document Context:
{context}

Current Question:
{question}

Answer (considering the previous conversation context):"""
)




def ingest_pdf(pdf_path: str) -> Dict[str, any]:
    """Ingest PDF into vector database with error handling"""
    # Ensure models are initialized
    _ensure_initialized()
    """
    Ingest PDF into vector database with error handling
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dictionary with file info and chunks count
        
    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If PDF is invalid or empty
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    filename = os.path.basename(pdf_path).lower()
    logger.info(f"Ingesting PDF: {filename}")
    
    try:
        # Load PDF
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
        
        if not docs:
            raise ValueError(f"PDF file is empty or cannot be read: {filename}")
        
        # Split into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        chunks = splitter.split_documents(docs)
        
        if not chunks:
            raise ValueError(f"No text chunks extracted from PDF: {filename}")
        
        # Attach metadata
        for chunk in chunks:
            chunk.metadata["filename"] = filename
        
        # Add to vector database
        vector_db.add_documents(chunks)
        
        logger.info(f"Successfully ingested {len(chunks)} chunks from {filename}")
        
        return {"file": filename, "chunks": len(chunks)}
        
    except Exception as e:
        logger.error(f"Error ingesting PDF {filename}: {e}", exc_info=True)
        raise


def _ensure_initialized():
    """Ensure models are initialized before use"""
    if llm is None or embeddings is None or vector_db is None:
        _initialize_models()


def ask_question(query: str, filename: str, conversation_history: Optional[List[dict]] = None) -> str:
    """
    Ask a question about a document with error handling and timeout
    
    Args:
        query: User's question
        filename: Name of the document file
        
    Returns:
        AI-generated answer
        
    Raises:
        ValueError: If query or filename is invalid
        TimeoutError: If operation takes too long
    """
    start_time = time.time()
    
    # Input validation
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    if len(query) > settings.MAX_QUERY_LENGTH:
        raise ValueError(f"Query too long. Maximum length: {settings.MAX_QUERY_LENGTH}")
    
    if len(query) < settings.MIN_QUERY_LENGTH:
        raise ValueError(f"Query too short. Minimum length: {settings.MIN_QUERY_LENGTH}")
    
    clean_filename = os.path.basename(filename).lower()
    logger.info(f"Processing question for {clean_filename}: {query[:50]}...")
    
    # Ensure models are initialized
    _ensure_initialized()
    
    try:
        # Search for relevant documents
        docs = vector_db.similarity_search(
            query,
            k=settings.SIMILARITY_SEARCH_K,
            filter={"filename": clean_filename}
        )
        
        if not docs:
            logger.warning(f"No documents found for: {clean_filename}")
            return f"I don't have enough information to answer this question. No context found for '{clean_filename}'."
        
        # Build context
        context = "\n\n".join(d.page_content for d in docs)
        
        # Generate prompt with or without conversation history
        if conversation_history and len(conversation_history) > 0:
            # Build conversation history string (last 5 exchanges to avoid too long prompts)
            recent_history = conversation_history[-5:]  # Last 5 Q&A pairs
            history_text = "\n".join([
                f"Q: {item.get('query', item.get('question', ''))}\nA: {item.get('answer', '')}"
                for item in recent_history
            ])
            logger.info(f"Using conversation history with {len(recent_history)} previous exchanges")
            prompt = PROMPT_WITH_HISTORY.format(
                conversation_history=history_text,
                context=context,
                question=query
            )
        else:
            # No conversation history - use simple prompt
            prompt = PROMPT.format(context=context, question=query)
        
        # Invoke LLM with timeout handling
        try:
            logger.info(f"Invoking LLM with prompt length: {len(prompt)} characters")
            answer = llm.invoke(prompt)
            
            # Validate answer
            if not answer or not answer.strip():
                logger.warning("Empty answer from LLM")
                return "I apologize, but I couldn't generate a response. Please try rephrasing your question."
            
            response_time = time.time() - start_time
            logger.info(f"Question answered in {response_time:.2f}s")
            
            if response_time > 90:
                logger.warning(f"Slow response time: {response_time:.2f}s - consider optimizing")
            
            return answer.strip()
            
        except TimeoutError as e:
            response_time = time.time() - start_time
            logger.error(f"LLM timeout after {response_time:.2f}s")
            raise TimeoutError(f"Request timed out after {response_time:.1f} seconds. The AI model is processing slowly. Try a shorter or simpler question.")
        except LangChainException as e:
            logger.error(f"LangChain error: {e}", exc_info=True)
            raise ValueError(f"Error processing question: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in ask_question: {e}", exc_info=True)
            raise
        
    except Exception as e:
        logger.error(f"Error in ask_question: {e}", exc_info=True)
        raise


def validate_document_exists(filename: str) -> bool:
    """Check if document exists in vector database"""
    try:
        _ensure_initialized()
        clean_filename = os.path.basename(filename).lower()
        docs = vector_db.similarity_search(
            "",
            k=1,
            filter={"filename": clean_filename}
        )
        return len(docs) > 0
    except Exception as e:
        logger.error(f"Error validating document: {e}")
        return False


def get_document_stats(filename: str) -> Optional[Dict]:
    """Get statistics about a document"""
    try:
        _ensure_initialized()
        clean_filename = os.path.basename(filename).lower()
        docs = vector_db.similarity_search(
            "",
            k=1000,  # Get all chunks
            filter={"filename": clean_filename}
        )
        
        if not docs:
            return None
        
        total_chars = sum(len(d.page_content) for d in docs)
        
        return {
            "filename": clean_filename,
            "chunks_count": len(docs),
            "total_characters": total_chars,
            "average_chunk_size": total_chars // len(docs) if docs else 0
        }
    except Exception as e:
        logger.error(f"Error getting document stats: {e}")
        return None


# ========== NEW AI FEATURES ==========

SUMMARY_PROMPT = PromptTemplate.from_template(
    """Summarize the following document content in a clear and concise manner.
Include the main topics, key points, and important information.

Document Content:
{content}

Summary:"""
)

EXTRACT_PROMPT = PromptTemplate.from_template(
    """Extract key information from the following text. Return a structured summary with:
- Main topics discussed
- Key dates mentioned
- Important names or entities
- Key statistics or numbers
- Main conclusions or findings

Text:
{content}

Extracted Information:"""
)

COMPARE_PROMPT = PromptTemplate.from_template(
    """Compare these two documents and highlight:
1. Similarities between the documents
2. Key differences
3. Unique points in each document

Document 1:
{doc1}

Document 2:
{doc2}

Comparison:"""
)

MULTI_DOC_PROMPT = PromptTemplate.from_template(
    """Answer the question using information from multiple documents provided below.
If information is found in multiple documents, mention which documents contain it.

Documents:
{context}

Question:
{question}

Answer:"""
)


def summarize_document(filename: str) -> str:
    """Generate a comprehensive summary of a document"""
    try:
        _ensure_initialized()
        clean_filename = os.path.basename(filename).lower()
        logger.info(f"Generating summary for: {clean_filename}")
        
        # Get all chunks for comprehensive summary
        docs = vector_db.similarity_search(
            "",
            k=20,
            filter={"filename": clean_filename}
        )
        
        if not docs:
            return "No content found for summarization."
        
        # Combine content
        full_content = "\n\n".join(d.page_content for d in docs)
        
        # If content is too long, summarize in parts
        if len(full_content) > 3000:
            chunks = [full_content[i:i+3000] for i in range(0, len(full_content), 3000)]
            summaries = []
            for chunk in chunks:
                prompt = SUMMARY_PROMPT.format(content=chunk)
                summaries.append(llm.invoke(prompt))
            # Summarize the summaries
            combined = "\n\n".join(summaries)
            prompt = SUMMARY_PROMPT.format(content=combined)
            return llm.invoke(prompt)
        
        prompt = SUMMARY_PROMPT.format(content=full_content)
        summary = llm.invoke(prompt)
        logger.info(f"Summary generated for {clean_filename}")
        return summary.strip()
    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)
        raise


def extract_key_information(filename: str) -> Dict:
    """Extract structured key information from a document"""
    try:
        _ensure_initialized()
        clean_filename = os.path.basename(filename).lower()
        logger.info(f"Extracting key information from: {clean_filename}")
        
        docs = vector_db.similarity_search(
            "",
            k=15,
            filter={"filename": clean_filename}
        )
        
        if not docs:
            return {"error": "Document not found"}
        
        content = "\n\n".join(d.page_content for d in docs)
        
        prompt = EXTRACT_PROMPT.format(content=content[:3000])
        extracted = llm.invoke(prompt)
        
        return {
            "filename": clean_filename,
            "extracted_info": extracted.strip()
        }
    except Exception as e:
        logger.error(f"Error extracting information: {e}", exc_info=True)
        raise


def compare_documents(filename1: str, filename2: str) -> str:
    """Compare two documents and highlight similarities and differences"""
    try:
        _ensure_initialized()
        clean_f1 = os.path.basename(filename1).lower()
        clean_f2 = os.path.basename(filename2).lower()
        logger.info(f"Comparing documents: {clean_f1} vs {clean_f2}")
        
        docs1 = vector_db.similarity_search("", k=10, filter={"filename": clean_f1})
        docs2 = vector_db.similarity_search("", k=10, filter={"filename": clean_f2})
        
        if not docs1 or not docs2:
            return "One or both documents not found."
        
        content1 = "\n\n".join(d.page_content for d in docs1)
        content2 = "\n\n".join(d.page_content for d in docs2)
        
        prompt = COMPARE_PROMPT.format(
            doc1=content1[:2000],
            doc2=content2[:2000]
        )
        
        comparison = llm.invoke(prompt)
        logger.info(f"Comparison completed for {clean_f1} and {clean_f2}")
        return comparison.strip()
    except Exception as e:
        logger.error(f"Error comparing documents: {e}", exc_info=True)
        raise


def multi_document_search(query: str, filenames: Optional[List[str]] = None) -> Dict:
    """Search across multiple documents simultaneously"""
    try:
        _ensure_initialized()
        logger.info(f"Multi-document search: {query[:50]}...")
        
        all_results = []
        found_docs = set()
        
        if filenames:
            # Search specific documents
            for filename in filenames:
                clean_filename = os.path.basename(filename).lower()
                docs = vector_db.similarity_search(
                    query,
                    k=3,
                    filter={"filename": clean_filename}
                )
                for doc in docs:
                    all_results.append({
                        "filename": clean_filename,
                        "content": doc.page_content,
                    })
                    found_docs.add(clean_filename)
        else:
            # Search all documents
            docs = vector_db.similarity_search(query, k=15)
            for doc in docs:
                filename = doc.metadata.get("filename", "unknown")
                if filename not in found_docs:
                    all_results.append({
                        "filename": filename,
                        "content": doc.page_content,
                    })
                    found_docs.add(filename)
        
        # Generate comprehensive answer
        if all_results:
            context = "\n\n".join([
                f"[From {r['filename']}]:\n{r['content']}"
                for r in all_results[:5]
            ])
            prompt = MULTI_DOC_PROMPT.format(context=context, question=query)
            answer = llm.invoke(prompt)
        else:
            answer = "No relevant content found in the documents."
        
        return {
            "answer": answer.strip(),
            "sources": list(found_docs),
            "total_matches": len(all_results)
        }
    except Exception as e:
        logger.error(f"Error in multi-document search: {e}", exc_info=True)
        raise


def generate_question_suggestions(filename: str, count: int = 5) -> List[str]:
    """Generate smart question suggestions based on document content"""
    try:
        _ensure_initialized()
        clean_filename = os.path.basename(filename).lower()
        docs = vector_db.similarity_search("", k=10, filter={"filename": clean_filename})
        
        if not docs:
            return []
        
        content = "\n\n".join(d.page_content for d in docs[:5])
        
        prompt = f"""Based on this document content, generate {count} relevant questions that would help someone understand the key information.

Document content:
{content[:2000]}

Generate exactly {count} questions, one per line, without numbering:"""
        
        response = llm.invoke(prompt)
        questions = [q.strip() for q in response.split("\n") if q.strip() and "?" in q]
        return questions[:count]
    except Exception as e:
        logger.error(f"Error generating suggestions: {e}")
        return []


def delete_document_from_db(filename: str) -> bool:
    """Delete all chunks of a document from vector database"""
    try:
        _ensure_initialized()
        clean_filename = os.path.basename(filename).lower()
        logger.info(f"Deleting document from vector DB: {clean_filename}")
        
        # Get all document IDs to delete
        docs = vector_db.similarity_search("", k=10000, filter={"filename": clean_filename})
        
        if not docs:
            logger.warning(f"No chunks found for {clean_filename}")
            return False
        
        # ChromaDB delete by metadata filter
        try:
            # Delete using collection
            collection = vector_db._collection
            ids_to_delete = []
            all_data = collection.get(where={"filename": clean_filename})
            if all_data and "ids" in all_data:
                ids_to_delete = all_data["ids"]
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} chunks for {clean_filename}")
                return True
        except Exception as e:
            logger.error(f"Error deleting from vector DB: {e}")
            return False
        
        return False
    except Exception as e:
        logger.error(f"Error deleting document: {e}", exc_info=True)
        return False


def search_documents(query: str, limit: int = 10, filenames: Optional[List[str]] = None) -> List[Dict]:
    """Search for documents by name or content
    
    Args:
        query: Search query
        limit: Maximum number of results
        filenames: Optional list of filenames to filter results (for user isolation)
    """
    try:
        _ensure_initialized()
        # Search in vector database
        docs = vector_db.similarity_search(query, k=limit * 2)
        
        found_files = {}
        for doc in docs:
            filename = doc.metadata.get("filename", "unknown")
            # Filter by filenames if provided (for user isolation)
            if filenames and filename not in filenames:
                continue
            if filename not in found_files:
                found_files[filename] = {
                    "filename": filename,
                    "preview": doc.page_content[:200] + "...",
                    "relevance_score": None
                }
        
        return list(found_files.values())[:limit]
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return []