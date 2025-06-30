import httpx
import json
from typing import Dict, Any, Optional, List
from config.settings import settings

class LMStudioClient:
    def __init__(self):
        self.provider = settings.LM_CLIENT_PROVIDER.lower()

        if self.provider == "groq":
            self.base_url = settings.GROQ_BASE_URL
            self.api_key = settings.GROQ_API_KEY
            self.model_name = settings.GROQ_MODEL_NAME
        elif self.provider == "lmstudio":
            self.base_url = settings.LM_STUDIO_BASE_URL
            self.api_key = settings.LM_STUDIO_API_KEY
            self.model_name = settings.LM_STUDIO_MODEL_NAME
        else:
            raise ValueError(f"Unsupported LM provider: {self.provider}")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None,
        system_prompt: str = None
    ) -> Optional[str]:
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature or settings.TEMPERATURE,
            "max_tokens": max_tokens or settings.MAX_TOKENS,
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=settings.TIMEOUT_SECONDS) as client:
                print(f"[LLMClient] Requesting {self.provider} model: {self.model_name}")
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]

        except httpx.HTTPError as e:
            print(f"HTTP error with {self.provider}: {e}")
        except (KeyError, IndexError) as e:
            print(f"Parsing error: {e}")
        return None

    async def simple_completion(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        messages = [{"role": "user", "content": prompt}]
        return await self.chat_completion(messages, system_prompt=system_prompt)

    async def test_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                test_url = f"{self.base_url}/models"
                response = await client.get(test_url, headers=self.headers)
                return response.status_code == 200
        except Exception as e:
            print(f"[LLMClient] Async connection test failed: {e}")
            return False


# Global async instance
llm_client = LMStudioClient()
