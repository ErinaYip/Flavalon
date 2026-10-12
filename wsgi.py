"""WSGI 入口，供 gunicorn 使用：gunicorn -w 1 -b :5000 wsgi:app。"""

from app import create_app

app = create_app()
