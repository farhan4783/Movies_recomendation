from flask import Flask, render_template, request
from model.knn_model import recommend_movies, movies

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    recommendations = []
    selected_movie = None
    error = None

    if request.method == "POST":
        selected_movie = request.form["movie"]
        try:
            recommendations = recommend_movies(selected_movie)
        except Exception as e:
            error = "An error occurred while generating recommendations. Please try again."
            recommendations = []

    movie_list = movies.to_dict('records')  # list of {'movieId':, 'title':, 'genre':}

    return render_template(
        "index.html",
        movies=movie_list,
        recommendations=recommendations,
        selected_movie=selected_movie,
        error=error
    )

if __name__ == "__main__":
    app.run(debug=True)
