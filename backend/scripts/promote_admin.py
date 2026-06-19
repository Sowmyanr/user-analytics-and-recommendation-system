"""
Utility: Promote an existing user to admin (development convenience)

Usage:
  python backend/scripts/promote_admin.py --email you@example.com

This uses the backend's configured database (via app.core.config), so it
will update the correct SQLite/Postgres DB for the current ENVIRONMENT.
"""

import argparse
import sys
import os
from datetime import datetime

# Ensure backend root is on sys.path so 'app' package is importable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.core.database import SessionLocal
from app.models.user import User, UserRole


def promote(email: str) -> bool:
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == email).one_or_none()
        if not user:
            print(f"❌ No user found with email: {email}")
            return False

        if user.role == UserRole.ADMIN:
            print(f"ℹ️  User is already an admin: {email} (user_id={user.user_id})")
            return True

        user.role = UserRole.ADMIN
        user.updated_at = datetime.utcnow()
        session.commit()
        print(f"✅ Promoted to admin: {email} (user_id={user.user_id})")
        return True
    except Exception as e:
        session.rollback()
        print(f"❌ Failed to promote user: {e}")
        return False
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Promote a user to admin")
    parser.add_argument("--email", required=True, help="User email to promote")
    args = parser.parse_args()

    ok = promote(args.email)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
