import os
import sys

# Tell Python where your app is
sys.path.insert(0, os.path.dirname(__file__))

# Import the FastAPI app from api.py
from api import app as fastapi_app

# Convert the ASGI app to WSGI so cPanel/Passenger can read it
from a2wsgi import ASGIMiddleware
application = ASGIMiddleware(fastapi_app)
