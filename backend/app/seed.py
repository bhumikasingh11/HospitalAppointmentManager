import sys
import argparse
from app.database import SessionLocal, engine, Base
from app.models import User, RoleEnum
from app.auth import hash_password
import app.models

def seed_admin(name: str = "Admin User", email: str = "admin@hospital.com", password: str = "admin123"):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.email == email).first()
        if existing_admin:
            print(f"Admin account with email '{email}' already exists.")
            return existing_admin

        admin_user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=RoleEnum.ADMIN
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"Successfully created ADMIN account:")
        print(f"  Name: {admin_user.name}")
        print(f"  Email: {admin_user.email}")
        print(f"  Password: {password}")
        return admin_user
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed initial Admin account")
    parser.add_argument("--name", default="Admin User", help="Admin display name")
    parser.add_argument("--email", default="admin@hospital.com", help="Admin email address")
    parser.add_argument("--password", default="admin123", help="Admin password")
    args = parser.parse_args()

    seed_admin(name=args.name, email=args.email, password=args.password)
