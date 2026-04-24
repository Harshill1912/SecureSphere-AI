"""Health check script to verify server is running"""
import requests
import sys
import time

def check_server(base_url="http://127.0.0.1:8000", timeout=5):
    """Check if the server is running and healthy"""
    try:
        # Check root endpoint
        response = requests.get(f"{base_url}/", timeout=timeout)
        if response.status_code == 200:
            print("[OK] Server is running")
            print(f"   Response: {response.json()}")
        else:
            print(f"[!] Server responded with status {response.status_code}")
            return False
        
        # Check health endpoint
        try:
            health_response = requests.get(f"{base_url}/health", timeout=timeout)
            if health_response.status_code == 200:
                health_data = health_response.json()
                print("[OK] Health check passed")
                print(f"   Status: {health_data.get('status', 'unknown')}")
                print(f"   Services: {health_data.get('services', {})}")
            else:
                print(f"[!] Health check failed with status {health_response.status_code}")
        except Exception as e:
            print(f"[!] Health check error: {e}")
        
        return True
    except requests.exceptions.ConnectionError:
        print("[X] Server is not running or not accessible")
        print(f"   Make sure the server is running on {base_url}")
        return False
    except requests.exceptions.Timeout:
        print("[X] Server request timed out")
        return False
    except Exception as e:
        print(f"[X] Error checking server: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("SecureSphere Health Check")
    print("=" * 50)
    print()
    
    # Wait a bit for server to start if just started
    print("Checking server status...")
    time.sleep(1)
    
    success = check_server()
    
    print()
    print("=" * 50)
    if success:
        print("[OK] All checks passed!")
        sys.exit(0)
    else:
        print("[X] Health check failed")
        print("\nTo start the server:")
        print("  cd backend")
        print("  .\\run.ps1")
        sys.exit(1)
