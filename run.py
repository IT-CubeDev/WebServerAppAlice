import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from config import get_config

config_name = os.environ.get("FLASK_ENV", "development")
app = create_app(get_config(config_name))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=app.debug)
