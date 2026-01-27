from app import app, db
from model.models import User
from werkzeug.security import generate_password_hash

def test_profile_update():
    with app.app_context():
        # Setup
        username = "testuser_profile"
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, password=generate_password_hash("password", method='scrypt'))
            db.session.add(user)
            db.session.commit()
            print(f"Created user: {user.username}")
        else:
            print(f"Using existing user: {user.username}")
            
        # Update Bio and Avatar
        print("Updating profile...")
        new_bio = "I love sci-fi and action movies!"
        new_avatar = "https://example.com/avatar.png"
        
        user.bio = new_bio
        user.avatar_url = new_avatar
        db.session.commit()
        
        # Verify
        updated_user = User.query.filter_by(username=username).first()
        if updated_user.bio == new_bio and updated_user.avatar_url == new_avatar:
            print(f"SUCCESS: Profile updated. Bio: {updated_user.bio}")
        else:
            print("FAILURE: Profile update failed.")

if __name__ == "__main__":
    test_profile_update()
