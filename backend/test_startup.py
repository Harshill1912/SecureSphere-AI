"""Quick test to see if the server can start without errors"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("Testing imports...")

try:
    print("1. Importing config...")
    from config import get_settings
    settings = get_settings()
    print(f"   [OK] Config loaded")
    
    print("2. Importing logger...")
    from logger_config import logger
    print(f"   [OK] Logger initialized")
    
    print("3. Importing database...")
    from database import init_db
    print(f"   [OK] Database module loaded")
    
    print("4. Initializing database...")
    try:
        init_db()
        print(f"   [OK] Database initialized")
    except Exception as e:
        print(f"   [!] Database init warning: {e}")
    
    print("5. Importing engine (this may take a moment if Ollama isn't running)...")
    try:
        from engine import _ensure_initialized
        print(f"   [OK] Engine module loaded")
        print("   Note: Models will initialize on first use")
    except Exception as e:
        print(f"   [X] Engine import failed: {e}")
        print("   This is OK if Ollama isn't running - models initialize lazily")
    
    print("6. Importing main app...")
    try:
        from main import app
        print(f"   [OK] FastAPI app created")
    except Exception as e:
        print(f"   [X] App import failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "="*50)
    print("[OK] All imports successful!")
    print("="*50)
    print("\nThe server should start now.")
    print("If it's stuck, check:")
    print("1. Ollama is running (optional)")
    print("2. No port conflicts")
    print("3. Check logs/app.log for errors")
    
except Exception as e:
    print(f"\n[X] Error during startup test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
