import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Settings:

    # Provider selection
    LM_CLIENT_PROVIDER = os.getenv("LM_CLIENT_PROVIDER", "lmstudio")
    
    # LM Studio Configuration
    LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "lm-studio")
    MODEL_NAME = os.getenv("MODEL_NAME", "mistral-7b-instruct-v0.1")

    # Groq
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama3-70b-8192")
    
    # Project Settings
    PROJECT_ROOT_PATH = Path(os.getenv("PROJECT_ROOT_PATH", "./examples/sample_project"))
    OUTPUT_PATH = Path(os.getenv("OUTPUT_PATH", "./output/generated_code"))
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 1048576))
    SUPPORTED_EXTENSIONS = os.getenv("SUPPORTED_EXTENSIONS", ".py,.json,.yaml,.yml,.txt,.md").split(",")
    
    # Agent Settings
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
    TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", 180))
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.1))
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 4000))
    
    @classmethod
    def ensure_output_directory(cls):
        cls.OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
        return cls.OUTPUT_PATH

settings = Settings()