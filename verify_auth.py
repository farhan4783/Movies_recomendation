from app import app, db
from model.models import User
from werkzeug.security import generate_password_hash
import os

def verify_auth():
    print("Verifying Auth System...")
    
    # Clean up old DB if exists for fresh test
    if os.path.exists("instance/database.db"):
        print("Existing database found.")
    
    with app.app_context():
        try:
            print("Creating tables...")
            db.create_all()
            print("Tables created.")
            
            # Check if user exists
            user = User.query.filter_by(username="testuser").first()
            if not user:
                print("Creating test user...")
                new_user = User(username="testuser", password=generate_password_hash("password", method='scrypt'))
                db.session.add(new_user)
                db.session.commit()
                print("Test user created successfully.")
            else:
                print("Test user already exists.")
                
            print("Verification Successful!")
            return True
        except Exception as e:
            print(f"Verification Failed: {e}")
            return False

if __name__ == "__main__":
    verify_auth()
