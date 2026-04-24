# Production Deployment Guide

## What Makes This Production-Ready

### ✅ Error Handling
- Comprehensive try-catch blocks
- Proper HTTP status codes
- User-friendly error messages
- Detailed error logging with stack traces
- Timeout handling for long-running operations

### ✅ Security
- Input validation and sanitization
- File size limits
- Path traversal protection
- Security headers middleware
- Rate limiting to prevent abuse
- CORS configuration

### ✅ Logging & Monitoring
- Structured logging to file and console
- Log rotation (10MB max, 5 backups)
- Request/response time tracking
- Error tracking with context
- Health check endpoint

### ✅ Database
- SQLite for development (easily switchable to PostgreSQL)
- Automatic table creation
- Connection pooling
- Transaction management
- Indexed queries for performance

### ✅ Configuration Management
- Environment variable support
- .env file for local development
- Type-safe configuration
- Cached settings for performance

### ✅ Rate Limiting
- Per-endpoint rate limits
- IP-based limiting
- Configurable limits
- Proper error responses

### ✅ API Documentation
- Auto-generated OpenAPI docs
- Request/response schemas
- Validation error details

## Key Production Features

1. **Chat Endpoint** (`POST /chat`)
   - Input validation (min/max length)
   - Document existence check
   - Timeout protection (60s)
   - Response time tracking
   - Chat history persistence
   - Session management

2. **Upload Endpoint** (`POST /upload`)
   - File type validation
   - File size limits
   - Duplicate detection
   - Metadata tracking
   - Error recovery

3. **Health Check** (`GET /health`)
   - Service status monitoring
   - Component health checks
   - Version information

4. **Chat History** (`GET /chat/history`)
   - Filterable by session or document
   - Pagination support
   - Response time tracking

## Deployment Steps

1. **Environment Setup**
   ```bash
   # Install dependencies
   pip install -r req.txt
   
   # Create .env file
   cp .env.example .env
   
   # Edit .env with production values
   nano .env
   ```

2. **Configuration**
   - Set `DEBUG=False`
   - Change `SECRET_KEY` to a secure random string
   - Configure `CORS_ORIGINS` for your frontend
   - Adjust rate limits as needed
   - Set up proper database URL (PostgreSQL recommended)

3. **Database Setup**
   ```bash
   # Database is auto-created on first run
   # For PostgreSQL, create database first:
   # createdb securesphere
   ```

4. **Run Application**
   ```bash
   # Development
   python start.py
   
   # Production with multiple workers
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

5. **Reverse Proxy (nginx)**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
   }
   ```

6. **SSL/HTTPS**
   - Use Let's Encrypt with certbot
   - Configure nginx for SSL
   - Redirect HTTP to HTTPS

## Monitoring

- Check `/health` endpoint regularly
- Monitor log files: `logs/app.log`
- Set up alerts for error rates
- Track response times
- Monitor database size

## Performance Tuning

- Adjust `CHAT_TIMEOUT_SECONDS` based on LLM response times
- Tune `SIMILARITY_SEARCH_K` for better results
- Adjust `CHUNK_SIZE` and `CHUNK_OVERLAP` for document processing
- Use connection pooling for database
- Consider caching for frequently accessed documents

## Security Checklist

- [ ] Change `SECRET_KEY` in production
- [ ] Set `DEBUG=False`
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Use HTTPS in production
- [ ] Set up firewall rules
- [ ] Regular security updates
- [ ] Monitor for suspicious activity
- [ ] Backup database regularly

## Backup Strategy

1. **Database Backups**
   ```bash
   # SQLite
   cp secureSphere.db backups/secureSphere_$(date +%Y%m%d).db
   
   # PostgreSQL
   pg_dump securesphere > backups/securesphere_$(date +%Y%m%d).sql
   ```

2. **File Backups**
   - Backup `uploads/` directory
   - Backup `data/` directory (vector database)

3. **Automated Backups**
   - Set up cron job for daily backups
   - Keep last 30 days of backups
   - Test restore procedures

## Scaling Considerations

- Use PostgreSQL instead of SQLite for production
- Consider Redis for rate limiting at scale
- Use object storage (S3) for file uploads
- Implement caching layer
- Use load balancer for multiple workers
- Consider message queue for async processing

## Troubleshooting

### Common Issues

1. **Timeout Errors**
   - Increase `CHAT_TIMEOUT_SECONDS`
   - Check LLM service availability
   - Monitor system resources

2. **Rate Limit Errors**
   - Adjust rate limits in `.env`
   - Check for abuse patterns
   - Consider per-user limits

3. **Database Errors**
   - Check database connection
   - Verify permissions
   - Check disk space

4. **File Upload Errors**
   - Check file size limits
   - Verify disk space
   - Check file permissions

## Support

For issues or questions:
- Check logs: `logs/app.log`
- Review health endpoint: `/health`
- Check API docs: `/api/docs` (if DEBUG=True)
