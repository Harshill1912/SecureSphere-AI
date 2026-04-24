# Performance Optimization Tips

## Current Issue: Slow LLM Responses

The LLM (llama3) is taking 60-100+ seconds to answer questions, which is causing timeouts.

## Solutions

### 1. Increase Timeout (Already Applied)
- Changed from 60s to 120s
- This gives the LLM more time to respond

### 2. Use a Faster Model
Consider using a smaller/faster model:
```bash
ollama pull llama3.2  # Smaller, faster version
ollama pull mistral   # Alternative fast model
```

Then update `backend/config.py` or `.env`:
```
LLM_MODEL=llama3.2
```

### 3. Reduce Context Size
In `backend/config.py`:
```python
LLM_CONTEXT_SIZE=1024  # Reduce from 2048
SIMILARITY_SEARCH_K=3  # Reduce from 5
```

### 4. Optimize Prompts
Shorter prompts = faster responses

### 5. Check System Resources
- Make sure you have enough RAM
- Close other applications
- Check CPU usage

### 6. Use GPU (if available)
Ollama can use GPU for faster inference:
- Install CUDA drivers
- Ollama will automatically use GPU if available

## Quick Fix Applied

✅ Increased timeout to 120 seconds
✅ Added better error messages
✅ Added logging for slow responses

## Test After Changes

1. Restart the backend server
2. Try asking a simple question
3. Check response time in logs

## Expected Response Times

- Simple questions: 5-15 seconds
- Complex questions: 15-60 seconds
- Very complex: 60-120 seconds

If consistently > 120 seconds, consider using a faster model.
