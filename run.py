"""
Application entry point.

Usage:
    python run.py

For production, use a WSGI server such as gunicorn:
    gunicorn "run:app"
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
