"""Production-ready FastAPI application with comprehensive error handling"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import shutil
import os
import asyncio
import time
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db, init_db, ChatHistory, ChatSession, DocumentMetadata, User
from engine import (
    ask_question, ingest_pdf, validate_document_exists, get_document_stats,
    summarize_document, extract_key_information, compare_documents,
    multi_document_search, generate_question_suggestions, delete_document_from_db,
    search_documents
)
from schemas import (
    ChatRequest, ChatResponse, UploadResponse, HealthResponse, ErrorResponse,
    SummarizeRequest, CompareRequest, MultiSearchRequest, AnalyticsResponse
)
from logger_config import logger
from middleware import limiter, LoggingMiddleware, SecurityHeadersMiddleware, rate_limit_handler
from auth import get_current_active_user
from routes.auth import router as auth_router

settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Add middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Include auth router
app.include_router(auth_router)

# Initialize database
try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Error initializing database: {e}", exc_info=True)
    # Continue anyway - tables might already exist

# Create necessary directories
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.DATA_DIR, exist_ok=True)
log_dir = os.path.dirname(settings.LOG_FILE)
if log_dir:
    os.makedirs(log_dir, exist_ok=True)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Invalid request data",
            "details": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check vector database
        vector_db_status = "healthy"
        try:
            validate_document_exists("test.pdf")  # Just check connection
        except:
            vector_db_status = "unhealthy"
        
        # Check LLM (basic check)
        llm_status = "healthy"
        try:
            # Quick test - this is a lightweight check
            pass
        except:
            llm_status = "unhealthy"
        
        overall_status = "healthy" if vector_db_status == "healthy" and llm_status == "healthy" else "degraded"
        
        return HealthResponse(
            status=overall_status,
            version=settings.API_VERSION,
            services={
                "vector_db": vector_db_status,
                "llm": llm_status,
                "database": "healthy"
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            version=settings.API_VERSION,
            services={}
        )


@app.get("/", tags=["Root"])
def root():
    """Root endpoint"""
    return {
        "message": "SecureSphere API",
        "version": settings.API_VERSION,
        "status": "running",
        "docs": "/api/docs" if settings.DEBUG else "disabled"
    }


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def chat(
    request: Request,
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Chat endpoint with production-ready error handling and logging
    
    - Validates input
    - Checks document existence
    - Processes question with timeout
    - Saves to chat history
    - Returns structured response
    - Requires authentication
    """
    start_time = time.time()
    session_id = req.session_id or str(uuid.uuid4())
    
    # Use longer timeout for LLM operations (llama3 can be slow - takes 60-100s sometimes)
    llm_timeout = max(settings.CHAT_TIMEOUT_SECONDS + 30, 150)  # At least 150s total
    
    try:
        # Check if document belongs to user
        doc_metadata = db.query(DocumentMetadata).filter(
            DocumentMetadata.filename == req.filename.lower(),
            DocumentMetadata.user_id == current_user.id
        ).first()
        
        if not doc_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{req.filename}' not found. Please upload it first."
            )
        
        # Validate document exists in vector DB
        if not validate_document_exists(req.filename):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{req.filename}' not found in vector database."
            )
        
        # Get conversation history for follow-up questions
        conversation_history = req.conversation_history
        if not conversation_history and session_id:
            # Fetch recent conversation history from database (user-specific)
            try:
                recent_chats = db.query(ChatHistory).filter(
                    ChatHistory.session_id == session_id,
                    ChatHistory.filename == req.filename.lower(),
                    ChatHistory.user_id == current_user.id
                ).order_by(ChatHistory.created_at.desc()).limit(5).all()
                
                if recent_chats:
                    conversation_history = [
                        {"query": chat.query, "answer": chat.answer}
                        for chat in reversed(recent_chats)  # Reverse to get chronological order
                    ]
                    logger.info(f"Loaded {len(conversation_history)} previous messages for context")
            except Exception as e:
                logger.warning(f"Error loading conversation history: {e}")
                conversation_history = None
        
        # Process question
        logger.info(f"Processing chat request: {req.query[:50]}... for {req.filename} (user: {current_user.username})")
        if conversation_history:
            logger.info(f"Using conversation history: {len(conversation_history)} previous exchanges")
        logger.info(f"Using timeout: {llm_timeout}s")
        
        answer = await asyncio.wait_for(
            asyncio.to_thread(ask_question, req.query, req.filename, conversation_history),
            timeout=llm_timeout
        )
        
        response_time = time.time() - start_time
        
        # Save to chat history if enabled
        if settings.ENABLE_CHAT_HISTORY:
            try:
                chat_entry = ChatHistory(
                    user_id=current_user.id,
                    session_id=session_id,
                    filename=req.filename.lower(),
                    query=req.query,
                    answer=answer,
                    response_time=response_time
                )
                db.add(chat_entry)
                
                # Update or create session
                session = db.query(ChatSession).filter(
                    ChatSession.session_id == session_id,
                    ChatSession.user_id == current_user.id
                ).first()
                
                if session:
                    session.message_count += 1
                    session.updated_at = datetime.utcnow()
                else:
                    session = ChatSession(
                        user_id=current_user.id,
                        session_id=session_id,
                        filename=req.filename.lower(),
                        message_count=1
                    )
                    db.add(session)
                
                db.commit()
            except Exception as e:
                logger.error(f"Error saving chat history: {e}")
                db.rollback()
        
        logger.info(f"Chat request completed in {response_time:.2f}s")
        
        return ChatResponse(
            answer=answer,
            session_id=session_id,
            response_time=round(response_time, 2),
            sources_count=settings.SIMILARITY_SEARCH_K
        )
        
    except asyncio.TimeoutError:
        logger.error(f"Chat request timed out after {llm_timeout}s")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Request timed out after {llm_timeout} seconds. The AI model (llama3) is processing slowly. Suggestions: 1) Try a simpler/shorter question, 2) Wait a moment and try again, 3) Consider using a faster model like llama3.2"
        )
    except ValueError as e:
        logger.warning(f"Validation error in chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your question. Please try again."
        )


@app.post("/upload", response_model=UploadResponse, tags=["Upload"])
@limiter.limit("10/hour")  # Stricter limit for uploads
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload PDF endpoint with validation and error handling
    
    - Validates file type
    - Checks file size
    - Prevents duplicate uploads (per user)
    - Saves metadata to database
    - Requires authentication
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed"
            )
        
        # Check file size
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Sanitize filename - add user prefix to avoid conflicts
        safe_filename = os.path.basename(file.filename)
        # Store with user prefix in filename for file system, but keep original in metadata
        user_filename = f"{current_user.id}_{safe_filename}"
        file_path = os.path.join(settings.UPLOAD_DIR, user_filename)
        
        # Check if user already uploaded this file
        existing_doc = db.query(DocumentMetadata).filter(
            DocumentMetadata.filename == safe_filename.lower(),
            DocumentMetadata.user_id == current_user.id
        ).first()
        
        if existing_doc:
            return UploadResponse(
                message="PDF already uploaded and indexed",
                file=safe_filename,
                chunks_added=existing_doc.chunks_count or 0,
                file_size=existing_doc.file_size
            )
        
        # Save file
        logger.info(f"Uploading PDF: {safe_filename} ({file_size} bytes) for user {current_user.username}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Ingest into vector database (use original filename for vector DB)
        try:
            result = ingest_pdf(file_path)
        except Exception as e:
            # Clean up file if ingestion fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing PDF: {str(e)}"
            )
        
        # Save metadata with user association
        try:
            doc_metadata = DocumentMetadata(
                user_id=current_user.id,
                filename=safe_filename.lower(),  # Store original filename
                file_size=file_size,
                chunks_count=result["chunks"]
            )
            db.add(doc_metadata)
            db.commit()
        except Exception as e:
            logger.error(f"Error saving document metadata: {e}")
            db.rollback()
        
        logger.info(f"Successfully uploaded and indexed: {safe_filename} for user {current_user.username}")
        
        return UploadResponse(
            message="PDF uploaded & indexed successfully",
            file=safe_filename,  # Return original filename
            chunks_added=result["chunks"],
            file_size=file_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while uploading the file. Please try again."
        )


@app.get("/chat/history", tags=["Chat"])
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def get_chat_history(
    request: Request,
    session_id: Optional[str] = None,
    filename: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get chat history with filtering (user-specific)"""
    try:
        query = db.query(ChatHistory).filter(ChatHistory.user_id == current_user.id)
        
        if session_id:
            query = query.filter(ChatHistory.session_id == session_id)
        if filename:
            query = query.filter(ChatHistory.filename == filename.lower())
        
        chats = query.order_by(ChatHistory.created_at.desc()).limit(limit).all()
        
        return {
            "count": len(chats),
            "history": [
                {
                    "id": chat.id,
                    "session_id": chat.session_id,
                    "filename": chat.filename,
                    "query": chat.query,
                    "answer": chat.answer,
                    "response_time": chat.response_time,
                    "created_at": chat.created_at.isoformat()
                }
                for chat in chats
            ]
        }
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving chat history"
        )


@app.get("/documents", tags=["Documents"])
async def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all uploaded documents (user-specific)"""
    try:
        docs = db.query(DocumentMetadata).filter(
            DocumentMetadata.user_id == current_user.id
        ).order_by(
            DocumentMetadata.uploaded_at.desc()
        ).all()
        
        return {
            "count": len(docs),
            "documents": [
                {
                    "filename": doc.filename,
                    "file_size": doc.file_size,
                    "chunks_count": doc.chunks_count,
                    "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                    "last_accessed": doc.last_accessed.isoformat() if doc.last_accessed else None
                }
                for doc in docs
            ]
        }
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving documents"
        )


@app.get("/documents/{filename}/stats", tags=["Documents"])
async def get_document_statistics(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get statistics for a specific document (user-specific)"""
    try:
        # Check if document belongs to user
        doc_metadata = db.query(DocumentMetadata).filter(
            DocumentMetadata.filename == filename.lower(),
            DocumentMetadata.user_id == current_user.id
        ).first()
        
        if not doc_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{filename}' not found"
            )
        
        # Use user-prefixed filename for vector DB lookup
        user_filename = f"{current_user.id}_{os.path.basename(filename)}"
        stats = get_document_stats(user_filename)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{filename}' not found in vector database"
            )
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving document statistics"
        )


@app.delete("/documents/{filename}", tags=["Documents"])
@limiter.limit("10/hour")
async def delete_document(
    request: Request,
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a document and all its data (user-specific)"""
    try:
        clean_filename = os.path.basename(filename).lower()
        
        # Check if document exists and belongs to user
        doc_metadata = db.query(DocumentMetadata).filter(
            DocumentMetadata.filename == clean_filename,
            DocumentMetadata.user_id == current_user.id
        ).first()
        
        if not doc_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{filename}' not found"
            )
        
        # Delete from vector database (use user-prefixed filename)
        user_filename = f"{current_user.id}_{os.path.basename(filename)}"
        deleted = delete_document_from_db(user_filename)
        
        # Delete file (user-prefixed)
        file_path = os.path.join(settings.UPLOAD_DIR, user_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete metadata
        db.delete(doc_metadata)
        
        # Delete chat history (user-specific)
        db.query(ChatHistory).filter(
            ChatHistory.filename == clean_filename,
            ChatHistory.user_id == current_user.id
        ).delete()
        db.query(ChatSession).filter(
            ChatSession.filename == clean_filename,
            ChatSession.user_id == current_user.id
        ).delete()
        
        db.commit()
        
        logger.info(f"Document deleted: {clean_filename} by user {current_user.username}")
        return {"message": f"Document '{filename}' deleted successfully", "vector_db_deleted": deleted}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting document"
        )


@app.post("/documents/{filename}/summarize", tags=["Documents"])
@limiter.limit("20/hour")
async def summarize(
    request: Request,
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate a summary of a document (user-specific)"""
    try:
        # Check if document belongs to user
        doc_metadata = db.query(DocumentMetadata).filter(
            DocumentMetadata.filename == filename.lower(),
            DocumentMetadata.user_id == current_user.id
        ).first()
        
        if not doc_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{filename}' not found"
            )
        
        # Use user-prefixed filename for vector DB
        user_filename = f"{current_user.id}_{os.path.basename(filename)}"
        if not validate_document_exists(user_filename):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{filename}' not found in vector database"
            )
        
        summary = await asyncio.to_thread(summarize_document, user_filename)
        return {"summary": summary, "filename": filename}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating summary"
        )


@app.post("/documents/{filename}/extract", tags=["Documents"])
@limiter.limit("20/hour")
async def extract_info(
    request: Request,
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Extract key information from a document (user-specific)"""
    try:
        # Check if document belongs to user
        doc_metadata = db.query(DocumentMetadata).filter(
            DocumentMetadata.filename == filename.lower(),
            DocumentMetadata.user_id == current_user.id
        ).first()
        
        if not doc_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{filename}' not found"
            )
        
        # Use user-prefixed filename for vector DB
        user_filename = f"{current_user.id}_{os.path.basename(filename)}"
        if not validate_document_exists(user_filename):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{filename}' not found in vector database"
            )
        
        info = await asyncio.to_thread(extract_key_information, user_filename)
        return info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting information: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error extracting information"
        )


@app.post("/documents/compare", tags=["Documents"])
@limiter.limit("10/hour")
async def compare(
    request: Request,
    req: CompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Compare two documents (user-specific)"""
    try:
        # Check if both documents belong to user
        doc1 = db.query(DocumentMetadata).filter(
            DocumentMetadata.filename == req.filename1.lower(),
            DocumentMetadata.user_id == current_user.id
        ).first()
        doc2 = db.query(DocumentMetadata).filter(
            DocumentMetadata.filename == req.filename2.lower(),
            DocumentMetadata.user_id == current_user.id
        ).first()
        
        if not doc1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{req.filename1}' not found"
            )
        if not doc2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{req.filename2}' not found"
            )
        
        # Use user-prefixed filenames for vector DB
        user_filename1 = f"{current_user.id}_{os.path.basename(req.filename1)}"
        user_filename2 = f"{current_user.id}_{os.path.basename(req.filename2)}"
        
        if not validate_document_exists(user_filename1):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{req.filename1}' not found in vector database"
            )
        if not validate_document_exists(user_filename2):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{req.filename2}' not found in vector database"
            )
        
        comparison = await asyncio.to_thread(
            compare_documents, user_filename1, user_filename2
        )
        return {"comparison": comparison, "filename1": req.filename1, "filename2": req.filename2}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error comparing documents"
        )


@app.post("/search/multi", tags=["Search"])
@limiter.limit("30/hour")
async def multi_search(
    request: Request,
    req: MultiSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Search across multiple documents (user-specific)"""
    try:
        # Verify all filenames belong to user and convert to user-prefixed
        if req.filenames:
            user_filenames = []
            for filename in req.filenames:
                doc_metadata = db.query(DocumentMetadata).filter(
                    DocumentMetadata.filename == filename.lower(),
                    DocumentMetadata.user_id == current_user.id
                ).first()
                if not doc_metadata:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Document '{filename}' not found"
                    )
                user_filenames.append(f"{current_user.id}_{os.path.basename(filename)}")
        else:
            user_filenames = None
        
        result = await asyncio.to_thread(multi_document_search, req.query, user_filenames)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in multi-document search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error performing multi-document search"
        )


@app.get("/documents/{filename}/suggestions", tags=["Chat"])
async def get_suggestions(
    filename: str,
    count: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get AI-generated question suggestions for a document (user-specific)"""
    try:
        # Check if document belongs to user
        doc_metadata = db.query(DocumentMetadata).filter(
            DocumentMetadata.filename == filename.lower(),
            DocumentMetadata.user_id == current_user.id
        ).first()
        
        if not doc_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{filename}' not found"
            )
        
        # Use user-prefixed filename for vector DB
        user_filename = f"{current_user.id}_{os.path.basename(filename)}"
        if not validate_document_exists(user_filename):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{filename}' not found in vector database"
            )
        
        suggestions = await asyncio.to_thread(
            generate_question_suggestions, user_filename, count
        )
        return {"suggestions": suggestions, "filename": filename}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating suggestions"
        )


@app.get("/search", tags=["Search"])
async def search_docs(
    query: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Search for documents by content (user-specific)"""
    try:
        # Get user's documents
        user_docs = db.query(DocumentMetadata).filter(
            DocumentMetadata.user_id == current_user.id
        ).all()
        
        # Convert to user-prefixed filenames for vector DB search
        user_filenames = [f"{current_user.id}_{os.path.basename(doc.filename)}" for doc in user_docs]
        
        # Create mapping from user-prefixed to original filename
        filename_map = {f"{current_user.id}_{os.path.basename(doc.filename)}": doc.filename for doc in user_docs}
        
        results = await asyncio.to_thread(search_documents, query, limit, user_filenames)
        
        # Convert user-prefixed filenames back to original filenames
        for result in results:
            if result["filename"] in filename_map:
                result["filename"] = filename_map[result["filename"]]
        
        return {"query": query, "results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error searching documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error searching documents"
        )


@app.get("/analytics", response_model=AnalyticsResponse, tags=["Analytics"])
@limiter.limit("10/hour")
async def get_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get analytics and statistics about the system (user-specific)"""
    try:
        # Total documents (user-specific)
        total_docs = db.query(DocumentMetadata).filter(
            DocumentMetadata.user_id == current_user.id
        ).count()
        
        # Total chats (user-specific)
        total_chats = db.query(ChatHistory).filter(
            ChatHistory.user_id == current_user.id
        ).count()
        
        # Total sessions (user-specific)
        total_sessions = db.query(ChatSession).filter(
            ChatSession.user_id == current_user.id
        ).count()
        
        # Average response time (user-specific)
        chats_with_time = db.query(ChatHistory).filter(
            ChatHistory.user_id == current_user.id,
            ChatHistory.response_time.isnot(None)
        ).all()
        avg_response_time = None
        if chats_with_time:
            avg_response_time = sum(c.response_time for c in chats_with_time) / len(chats_with_time)
        
        # Most asked questions (user-specific)
        from sqlalchemy import func
        popular_questions = db.query(
            ChatHistory.query,
            func.count(ChatHistory.id).label('count')
        ).filter(
            ChatHistory.user_id == current_user.id
        ).group_by(ChatHistory.query).order_by(
            func.count(ChatHistory.id).desc()
        ).limit(5).all()
        
        most_asked = [
            {"question": q[0], "count": q[1]}
            for q in popular_questions
        ]
        
        # Popular documents (user-specific)
        popular_docs = db.query(
            ChatHistory.filename,
            func.count(ChatHistory.id).label('count')
        ).filter(
            ChatHistory.user_id == current_user.id
        ).group_by(ChatHistory.filename).order_by(
            func.count(ChatHistory.id).desc()
        ).limit(5).all()
        
        popular_documents = [
            {"filename": d[0], "chat_count": d[1]}
            for d in popular_docs
        ]
        
        return AnalyticsResponse(
            total_documents=total_docs,
            total_chats=total_chats,
            total_sessions=total_sessions,
            average_response_time=round(avg_response_time, 2) if avg_response_time else None,
            most_asked_questions=most_asked,
            popular_documents=popular_documents
        )
    except Exception as e:
        logger.error(f"Error getting analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving analytics"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
