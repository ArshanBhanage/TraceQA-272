import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: str = ""
    default_model: str = ""
    pinecone_api_key: str = ""
    pinecone_environment: str = ""
    pinecone_index_name: str = ""
    landingai_api_key: str = ""
    landingai_base_url: str = "https://api.va.landing.ai/v1/ade"
    postman_api_key: str = ""
    
    # Application Settings
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

# Define the base directory for the entire project
# This is the directory containing the 'backend' folder
BASE_DIR = Path(__file__).resolve().parent.parent
# Directory where documents are stored
DOCUMENTS_DIR = BASE_DIR / "documents"
# Backend directory
BACKEND_DIR = BASE_DIR / "backend"
