# SecureSphere - Production-Ready AI Document Q&A System

A production-ready FastAPI application for AI-powered document question answering with comprehensive error handling, logging, rate limiting, and database persistence.

## Features

✅ **Production-Ready Chat System**
- Comprehensive error handling and validation
- Request/response logging
- Rate limiting (30 requests/minute, 200/hour)
- Timeout handling (60s default)
- Chat history persistence
- Session management

✅ **Security**
- Input validation and sanitization
- Security headers middleware
- File size limits (10MB default)
- Path traversal protection

✅ **Monitoring & Health Checks**
- Health check endpoint (`/health`)
- Request/response time tracking
- Error logging with stack traces
- Service status monitoring

✅ **Database**
- SQLite database for chat history
- Document metadata tracking
- Session management
- Automatic table creation

## Installation

1. Install dependencies:
```bash
pip install -r req.txt
```

2. Create `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
```

3. Update `.env` with your settings (especially `SECRET_KEY` for production)

4. Initialize the database (automatic on first run)

## Running the Application

### Development Mode:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Health Check
- `GET /health` - Check service health and status

### Chat
- `POST /chat` - Ask questions about documents
  - Rate limit: 30/minute
  - Request body: `{ "query": "your question", "filename": "document.pdf", "session_id": "optional" }`

### Upload
- `POST /upload` - Upload PDF documents
  - Rate limit: 10/hour
  - Max file size: 10MB (configurable)

### Chat History
- `GET /chat/history` - Get chat history
  - Query params: `session_id`, `filename`, `limit`

### Documents
- `GET /documents` - List all uploaded documents
- `GET /documents/{filename}/stats` - Get document statistics

## Configuration

All settings are configurable via environment variables in `.env`:

- `RATE_LIMIT_PER_MINUTE` - Chat rate limit (default: 30)
- `RATE_LIMIT_PER_HOUR` - Upload rate limit (default: 200)
- `CHAT_TIMEOUT_SECONDS` - Request timeout (default: 60)
- `MAX_FILE_SIZE` - Max upload size in bytes (default: 10MB)
- `LOG_LEVEL` - Logging level (INFO, DEBUG, WARNING, ERROR)

## Production Checklist

- [ ] Change `SECRET_KEY` in `.env`
- [ ] Set `DEBUG=False` in production
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Set up proper database (PostgreSQL for production)
- [ ] Configure logging rotation
- [ ] Set up monitoring/alerting
- [ ] Use reverse proxy (nginx) with SSL
- [ ] Configure proper file storage (S3, etc.)
- [ ] Set up backup strategy for database

## Logging

Logs are written to:
- Console (stdout)
- File: `logs/app.log` (with rotation, max 10MB, 5 backups)

## Error Handling

All endpoints include:
- Input validation
- Error logging
- Proper HTTP status codes
- User-friendly error messages
- Timeout handling

## Rate Limiting

Rate limits are enforced per IP address:
- Chat: 30 requests per minute
- Upload: 10 requests per hour
- History: 200 requests per hour

## Database Schema

- `chat_history` - Stores all chat interactions
- `chat_sessions` - Tracks conversation sessions
- `document_metadata` - Stores document information

## License

MIT
