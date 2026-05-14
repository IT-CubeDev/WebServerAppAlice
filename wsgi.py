import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from config import get_config

config_name = os.environ.get("FLASK_ENV", "production")
app = create_app(get_config(config_name))
