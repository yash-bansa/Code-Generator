import requests
import json
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class LMStudioClient:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
        self.api_key = api_key or os.getenv("LM_STUDIO_API_KEY", "lm-studio")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def generate_response(self, prompt: str, temperature: float = 0.1, max_tokens: int = 1000) -> str:
        """Generate response from LM Studio model"""
        try:
            payload = {
                "model": "local-model",  # LM Studio uses this as default
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result['choices'][0]['message']['content'].strip()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error connecting to LM Studio: {str(e)}")
        except KeyError as e:
            raise Exception(f"Unexpected response format: {str(e)}")
    
    def check_connection(self) -> bool:
        """Check if LM Studio server is accessible"""
        try:
            response = requests.get(f"{self.base_url}/models", headers=self.headers, timeout=5)
            return response.status_code == 200
        except:
            return False