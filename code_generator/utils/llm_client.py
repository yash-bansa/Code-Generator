import openai
import logging
from typing import Dict, Any, Optional, List
from config.settings import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        # Get current provider configuration
        self.config = settings.get_current_provider_config()
        self.provider = self.config["provider"]
        self.base_url = self.config["base_url"]
        self.api_key = self.config["api_key"]
        self.model_name = self.config["model_name"]
        
        # Validate configuration
        validation = settings.validate_configuration()
        if not validation["valid"]:
            raise ValueError(f"Configuration errors: {validation['errors']}")
        
        # Initialize OpenAI client
        if self.provider in ["tiger", "lmstudio"]:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        elif self.provider == "groq":
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
        
        logger.info(f"✅ {self.provider.upper()} client initialized")
        logger.info(f"   Model: {self.model_name}")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]], 
        temperature: float = None,
        max_tokens: int = None,
        system_prompt: str = None
    ) -> Optional[str]:
        """Make chat completion request"""
        
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature or settings.TEMPERATURE,
                max_tokens=max_tokens or settings.MAX_TOKENS
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"❌ {self.provider.upper()} API error: {e}")
            return None

    async def test_connection(self) -> bool:
        """Test connection"""
        try:
            result = await self.simple_completion("Hello", "You are a test assistant.")
            return bool(result)
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    async def simple_completion(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """Simple completion"""
        messages = [{"role": "user", "content": prompt}]
        return await self.chat_completion(messages, system_prompt=system_prompt)

# Global instance
llm_client = LLMClient()