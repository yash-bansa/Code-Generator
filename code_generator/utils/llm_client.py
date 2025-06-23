# import requests
# import json
# from typing import Dict, Any, Optional, List
# from config.settings import settings

# class LMStudioClient:
#     def __init__(self):
#         self.base_url = settings.LM_STUDIO_BASE_URL
#         self.api_key = settings.LM_STUDIO_API_KEY
#         self.model_name = settings.MODEL_NAME
#         self.headers = {
#             "Authorization": f"Bearer {self.api_key}",
#             "Content-Type": "application/json"
#         }
    
#     def chat_completion(
#         self, 
#         messages: List[Dict[str, str]], 
#         temperature: float = None,
#         max_tokens: int = None,
#         system_prompt: str = None
#     ) -> Optional[str]:
#         """
#         Send a chat completion request to LM Studio
#         """
#         if system_prompt:
#             messages = [{"role": "system", "content": system_prompt}] + messages
        
#         payload = {
#             "model": self.model_name,
#             "messages": messages,
#             "temperature": temperature or settings.TEMPERATURE,
#             "max_tokens": max_tokens or settings.MAX_TOKENS,
#             "stream": False
#         }
        
#         try:
#             print(settings.TIMEOUT_SECONDS)
#             response = requests.post(
#                 f"{self.base_url}/chat/completions",
#                 headers=self.headers,
#                 json=payload,
#                 timeout=settings.TIMEOUT_SECONDS
#             )
#             response.raise_for_status()
            
#             result = response.json()
#             return result["choices"][0]["message"]["content"]
            
#         except requests.exceptions.RequestException as e:
#             print(f"Error communicating with LM Studio: {e}")
#             return None
#         except (KeyError, IndexError) as e:
#             print(f"Error parsing LM Studio response: {e}")
#             return None
    
#     def simple_completion(self, prompt: str, system_prompt: str = None) -> Optional[str]:
#         """
#         Simple completion wrapper
#         """
#         messages = [{"role": "user", "content": prompt}]
#         return self.chat_completion(messages, system_prompt=system_prompt)
    
#     def test_connection(self) -> bool:
#         """
#         Test connection to LM Studio
#         """
#         try:
#             response = requests.get(f"{self.base_url}/models", headers=self.headers, timeout=5)
#             return response.status_code == 200
#         except:
#             return False

# # Global client instance
# llm_client = LMStudioClient()

import requests
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

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None,
        system_prompt: str = None
    ) -> Optional[str]:
        """
        Sends a chat completion request to the configured LLM provider.
        """
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
            print(f"[LLMClient] Requesting {self.provider} model: {self.model_name}")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=settings.TIMEOUT_SECONDS
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            print(f"Error communicating with {self.provider}: {e}")
            return None
        except (KeyError, IndexError) as e:
            print(f"Error parsing {self.provider} response: {e}")
            return None

    def simple_completion(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """
        Simple wrapper to make a single-prompt request.
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat_completion(messages, system_prompt=system_prompt)

    def test_connection(self) -> bool:
        """
        Test if the model server is reachable.
        """
        try:
            test_url = f"{self.base_url}/models" if self.provider == "lmstudio" else f"{self.base_url}/models"
            response = requests.get(test_url, headers=self.headers, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"[LLMClient] Connection test failed: {e}")
            return False


# Global instance
llm_client = LMStudioClient()
