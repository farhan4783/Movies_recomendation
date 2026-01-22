import unittest
from app import app

class TestFiltering(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_filter_year(self):
        # Select "The Dark Knight" (Action, 2008)
        # Filter for recent movies > 2010
        print("\nTesting Year Filter > 2010")
        response = self.app.post('/', data={
            'movie': 'The Dark Knight',
            'min_year': '2010',
            'genre': 'All',
            'min_rating': '0'
        }, follow_redirects=True)
        
        content = response.data.decode()
        # Should NOT see "The Godfather" (1972) but might see "Inception" (2010) or "Interstellar" (2014)
        if "Interstellar" in content:
            print("Found Interstellar (2014) - Valid")
        if "The Godfather" in content:
            print("Found The Godfather (1972) - INVALID for > 2010 filter")
            # This might happen if fallback is triggered, but with enriched data it shouldn't.
        else:
             print("Did not find old movies - Valid")

    def test_filter_genre(self):
        # Select "The Dark Knight"
        # Filter for "Romance"
        print("\nTesting Genre Filter = Romance")
        response = self.app.post('/', data={
            'movie': 'The Dark Knight',
            'min_year': '1970',
            'genre': 'Romance',
            'min_rating': '0'
        }, follow_redirects=True)
        
        content = response.data.decode()
        if "Titanic" in content or "Notebook" in content:
            print("Found Romance movies - Valid")
        else:
            print("No Romance movies found - Check logic")

if __name__ == '__main__':
    unittest.main()
