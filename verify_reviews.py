from app import app, db
from model.models import User, Review
from werkzeug.security import generate_password_hash

def test_reviews():
    with app.app_context():
        # Setup
        db.create_all()
        
        # Create test user if not exists
        username = "testuser_reviewer"
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, password=generate_password_hash("password", method='scrypt'))
            db.session.add(user)
            db.session.commit()
            print(f"Created user: {user.username}")
        else:
            print(f"Using existing user: {user.username}")

        # Create a Review
        print("Submitting review...")
        review = Review(
            user_id=user.id,
            movie_title="Inception",
            rating=5,
            comment="Mind blowing movie!"
        )
        db.session.add(review)
        db.session.commit()
        print("Review submitted.")

        # Verify Review
        saved_review = Review.query.filter_by(user_id=user.id, movie_title="Inception").order_by(Review.id.desc()).first()
        if saved_review and saved_review.comment == "Mind blowing movie!":
            print(f"SUCCESS: Review found! Rating: {saved_review.rating}, Comment: {saved_review.comment}")
        else:
            print("FAILURE: Review not found or mismatched.")

        # Cleanup (Optional, but good for repeatability)
        db.session.delete(saved_review)
        db.session.commit()
        print("Cleanup done.")

if __name__ == "__main__":
    test_reviews()
