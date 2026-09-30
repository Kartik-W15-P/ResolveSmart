import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:
    # ... existing configs ...
    BASE_DIR = Path(__file__).resolve().parent.parent
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "complaints")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # Enforce 5 MB maximum file payload
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "complaints")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "resolvesmart-super-secret-key-2026")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-resolvesmart-2026")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'resolvesmart.db')}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Media Storage Configuration
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", UPLOAD_DIR)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max payload
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

class Config:
    # ... existing configs ...
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)

    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "resolvesmart")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False