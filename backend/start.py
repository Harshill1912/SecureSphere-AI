"""Startup script for SecureSphere API"""
import sys
import uvicorn
from config import get_settings

settings = get_settings()

def main():
    """Main entry point with error handling"""
    try:
        print("=" * 60)
        print("🔐 SecureSphere API Server")
        print("=" * 60)
        print(f"Version: {settings.API_VERSION}")
        print(f"Host: {settings.HOST}")
        print(f"Port: {settings.PORT}")
        print(f"Debug: {settings.DEBUG}")
        print(f"API Docs: http://{settings.HOST}:{settings.PORT}/api/docs" if settings.DEBUG else "API Docs: Disabled")
        print("=" * 60)
        print()
        print("Loading application...")
        
        # Import app first to catch any import errors
        try:
            from main import app
            print("[OK] Application loaded successfully")
        except Exception as e:
            print(f"[X] Failed to load application: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        print("Starting Uvicorn server...")
        print()
        
        # Run the server
        uvicorn.run(
            app,  # Pass app directly instead of string
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure all dependencies are installed: pip install -r req.txt")
        print("2. Check if port 8000 is available")
        print("3. Verify virtual environment is activated")
        sys.exit(1)

if __name__ == "__main__":
    main()
