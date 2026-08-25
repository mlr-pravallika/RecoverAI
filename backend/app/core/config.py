import os
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))

    @property
    def db_url(self) -> str:
        # Fall back to sqlite if not provided or empty
        if not self.DATABASE_URL.strip():
            return "sqlite:///./recoverai.db"
        return self.DATABASE_URL

    class Config:
        case_sensitive = True

settings = Settings()
