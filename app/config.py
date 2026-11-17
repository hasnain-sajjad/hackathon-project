import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def load_env():
    """Load simple key=value pairs from .env if present without external dependencies."""
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
        except Exception as e:
            print(f"[Config] Notice: Could not read .env file: {e}")

load_env()

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
DB_PATH = os.environ.get("DB_PATH", str(BASE_DIR / "novaworks.db"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "novaworks-super-secret-key-2026")
COOKIE_NAME = "novaworks_session"
