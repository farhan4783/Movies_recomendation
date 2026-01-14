from app import app
import sys

def test_index_route():
    print("Testing index route (GET)...")
    with app.test_client() as client:
        try:
            response = client.get('/')
            if response.status_code == 200:
                print("SUCCESS: Index route returned 200 OK")
                return True
            else:
                print(f"FAILURE: Index route returned {response.status_code}")
                return False
        except Exception as e:
            print(f"CRASH: {e}")
            return False

if __name__ == "__main__":
    if test_index_route():
        sys.exit(0)
    else:
        sys.exit(1)
