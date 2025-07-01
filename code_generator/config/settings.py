import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

class Settings:
    # ==============================================
    # PROVIDER SELECTION
    # ==============================================
    LM_CLIENT_PROVIDER = os.getenv("LM_CLIENT_PROVIDER", "tiger")
    
    # ==============================================
    # LM STUDIO CONFIGURATION
    # ==============================================
    LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "lm-studio")
    LM_STUDIO_MODEL_NAME = os.getenv("LM_STUDIO_MODEL_NAME", "mistral-7b-instruct-v0.1")
    
    # ==============================================
    # GROQ CONFIGURATION
    # ==============================================
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama3-70b-8192")
    
    # ==============================================
    # TIGER ANALYTICS CONFIGURATION
    # ==============================================
    TIGER_BASE_URL = os.getenv("TIGER_BASE_URL", "https://api.ai-gateway.tigeranalytics.com")
    TIGER_API_KEY = os.getenv("TIGER_API_KEY", "")
    TIGER_MODEL_NAME = os.getenv("TIGER_MODEL_NAME", "gpt-4o")
    
    # ==============================================
    # BACKWARD COMPATIBILITY
    # ==============================================
    # Keep MODEL_NAME for backward compatibility
    MODEL_NAME = os.getenv("MODEL_NAME", "claude-3.7-sonnet")
    
    # ==============================================
    # PROJECT SETTINGS
    # ==============================================
    PROJECT_ROOT_PATH = Path(os.getenv("PROJECT_ROOT_PATH", "./examples/sample_project"))
    OUTPUT_PATH = Path(os.getenv("OUTPUT_PATH", "./output/generated_code"))
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 1048576))  # 1MB
    SUPPORTED_EXTENSIONS = os.getenv("SUPPORTED_EXTENSIONS", ".py,.json,.yaml,.yml,.txt,.md").split(",")
    
    # ==============================================
    # AGENT SETTINGS
    # ==============================================
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
    TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", 180))
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.1))
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 4000))
    
    # ==============================================
    # ADDITIONAL TIGER ANALYTICS SETTINGS
    # ==============================================
    TIGER_ORGANIZATION_ID = os.getenv("TIGER_ORGANIZATION_ID", "")
    TIGER_USER_ID = os.getenv("TIGER_USER_ID", "")
    
    # ==============================================
    # UTILITY METHODS
    # ==============================================
    @classmethod
    def ensure_output_directory(cls):
        """Ensure output directory exists"""
        cls.OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
        return cls.OUTPUT_PATH
    
    @classmethod
    def get_current_provider_config(cls):
        """Get configuration for currently selected provider"""
        provider = cls.LM_CLIENT_PROVIDER.lower()
        
        if provider == "tiger":
            return {
                "provider": "tiger",
                "base_url": cls.TIGER_BASE_URL,
                "api_key": cls.TIGER_API_KEY,
                "model_name": cls.TIGER_MODEL_NAME,
                "requires_auth": True
            }
        elif provider == "groq":
            return {
                "provider": "groq", 
                "base_url": cls.GROQ_BASE_URL,
                "api_key": cls.GROQ_API_KEY,
                "model_name": cls.GROQ_MODEL_NAME,
                "requires_auth": True
            }
        elif provider == "lmstudio":
            return {
                "provider": "lmstudio",
                "base_url": cls.LM_STUDIO_BASE_URL,
                "api_key": cls.LM_STUDIO_API_KEY,
                "model_name": cls.LM_STUDIO_MODEL_NAME,
                "requires_auth": False
            }
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    @classmethod
    def validate_configuration(cls):
        """Validate current configuration"""
        errors = []
        warnings = []
        
        provider = cls.LM_CLIENT_PROVIDER.lower()
        
        if provider == "tiger":
            if not cls.TIGER_API_KEY:
                errors.append("TIGER_API_KEY is required for Tiger Analytics provider")
            elif not cls.TIGER_API_KEY.startswith("sk-"):
                warnings.append("Tiger Analytics API key should start with 'sk-'")
            
            if not cls.TIGER_BASE_URL:
                errors.append("TIGER_BASE_URL is required for Tiger Analytics provider")
                
        elif provider == "groq":
            if not cls.GROQ_API_KEY:
                errors.append("GROQ_API_KEY is required for Groq provider")
            elif not cls.GROQ_API_KEY.startswith("gsk_"):
                warnings.append("Groq API key should start with 'gsk_'")
                
        elif provider == "lmstudio":
            if not cls.LM_STUDIO_BASE_URL.startswith("http://localhost"):
                warnings.append("LM Studio typically runs on localhost")
        
        else:
            errors.append(f"Unsupported provider: {provider}")
        
        # Validate paths
        if not cls.PROJECT_ROOT_PATH.exists():
            warnings.append(f"Project root path does not exist: {cls.PROJECT_ROOT_PATH}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    @classmethod
    def get_model_name_for_provider(cls):
        """Get the correct model name for current provider"""
        provider = cls.LM_CLIENT_PROVIDER.lower()
        
        if provider == "tiger":
            return cls.TIGER_MODEL_NAME
        elif provider == "groq":
            return cls.GROQ_MODEL_NAME
        elif provider == "lmstudio":
            return cls.LM_STUDIO_MODEL_NAME
        else:
            return cls.MODEL_NAME  # Fallback
    
    @classmethod
    def print_configuration(cls):
        """Print current configuration (for debugging)"""
        print("🔧 Current Configuration:")
        print(f"   Provider: {cls.LM_CLIENT_PROVIDER}")
        
        config = cls.get_current_provider_config()
        print(f"   Base URL: {config['base_url']}")
        print(f"   Model: {config['model_name']}")
        
        if config['api_key']:
            masked_key = f"{config['api_key'][:8]}...{config['api_key'][-4:]}" if len(config['api_key']) > 8 else "****"
            print(f"   API Key: {masked_key}")
        else:
            print(f"   API Key: Not set")
        
        print(f"   Project Path: {cls.PROJECT_ROOT_PATH}")
        print(f"   Output Path: {cls.OUTPUT_PATH}")
        print(f"   Temperature: {cls.TEMPERATURE}")
        print(f"   Max Tokens: {cls.MAX_TOKENS}")
        print(f"   Timeout: {cls.TIMEOUT_SECONDS}s")

# Create global settings instance
settings = Settings()

# Validate configuration on import
if __name__ == "__main__":
    validation = settings.validate_configuration()
    
    if validation["errors"]:
        print("❌ Configuration Errors:")
        for error in validation["errors"]:
            print(f"   - {error}")
    
    if validation["warnings"]:
        print("⚠️ Configuration Warnings:")
        for warning in validation["warnings"]:
            print(f"   - {warning}")
    
    if validation["valid"]:
        print("✅ Configuration is valid!")
        settings.print_configuration()
    else:
        print("❌ Please fix configuration errors before proceeding.")