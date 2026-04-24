"""Check if all dependencies are installed and services are available"""
import sys
import subprocess

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"[X] Python 3.8+ required. Found: {version.major}.{version.minor}")
        return False
    print(f"[OK] Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_import(module_name, package_name=None):
    """Check if a module can be imported"""
    try:
        __import__(module_name)
        print(f"[OK] {package_name or module_name}")
        return True
    except ImportError:
        print(f"[X] {package_name or module_name} - Not installed")
        return False

def check_ollama():
    """Check if Ollama is running"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("[OK] Ollama is running")
            return True
    except:
        pass
    print("[!] Ollama is not running (required for AI features)")
    print("   Start it with: ollama serve")
    return False

def main():
    print("=" * 50)
    print("SecureSphere Dependency Check")
    print("=" * 50)
    print()
    
    all_ok = True
    
    # Check Python
    print("Python Version:")
    all_ok = check_python_version() and all_ok
    print()
    
    # Check dependencies
    print("Python Dependencies:")
    dependencies = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("langchain", "LangChain"),
        ("langchain_ollama", "LangChain Ollama"),
        ("langchain_chroma", "LangChain Chroma"),
        ("chromadb", "ChromaDB"),
        ("pypdf", "PyPDF"),
        ("sqlalchemy", "SQLAlchemy"),
        ("slowapi", "SlowAPI"),
        ("pydantic", "Pydantic"),
    ]
    
    for module, name in dependencies:
        all_ok = check_import(module, name) and all_ok
    print()
    
    # Check Ollama
    print("External Services:")
    ollama_ok = check_ollama()
    print()
    
    print("=" * 50)
    if all_ok:
        if ollama_ok:
            print("[OK] All checks passed! Ready to start.")
        else:
            print("[!] Dependencies OK, but Ollama is not running.")
            print("   The server will start, but AI features won't work.")
    else:
        print("[X] Some dependencies are missing.")
        print("   Install with: pip install -r req.txt")
    print("=" * 50)
    
    return all_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
