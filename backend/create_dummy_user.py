"""
Create a dummy user for testing SecureSphere.

Run from the backend directory (with your venv activated and deps installed):
  python create_dummy_user.py
Or:  py create_dummy_user.py

If you get ModuleNotFoundError, run first: pip install -r req.txt

Dummy user credentials (use these to log in at the app):
  Username: testuser
  Email:    test@example.com
  Password: test1234
"""
import sys
import os

# Ensure we can import from backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, SessionLocal, User
from auth import get_password_hash


DUMMY_USER = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "test1234",
}


def main():
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == DUMMY_USER["username"]).first()
        if existing:
            print(f"Dummy user already exists: {DUMMY_USER['username']}")
            print(f"  Login with password: {DUMMY_USER['password']}")
            return
        user = User(
            username=DUMMY_USER["username"],
            email=DUMMY_USER["email"],
            hashed_password=get_password_hash(DUMMY_USER["password"]),
            is_active=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print("Dummy user created successfully!")
        print()
        print("Use these credentials to log in:")
        print(f"  Username: {DUMMY_USER['username']}")
        print(f"  Email:    {DUMMY_USER['email']}")
        print(f"  Password: {DUMMY_USER['password']}")
        print()
        print("Then start the app and test: upload a PDF, ask questions, check Analytics.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
