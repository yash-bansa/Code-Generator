import requests
import json
from typing import Dict, List, Any, Optional

class LMStudioClient:
    """Client for interacting with LM Studio API"""
    
    def __init__(self, base_url: str = "http://localhost:1234"):
        self.base_url = base_url.rstrip('/')
        self.chat_endpoint = f"{self.base_url}/v1/chat/completions"
        self.models_endpoint = f"{self.base_url}/v1/models"
        
        # Default parameters
        self.default_params = {
            "temperature": 0.1,
            "max_tokens": 2000,
            "top_p": 0.9,
            "stream": False
        }
    
    def chat_completion(self, messages: List[Dict[str, Any]], **kwargs) -> Optional[Dict[str, Any]]:
        """Send chat completion request to LM Studio"""
        try:
            # Prepare request payload
            payload = {
                "messages": messages,
                **self.default_params,
                **kwargs
            }
            
            # Make API request
            response = requests.post(
                self.chat_endpoint,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"LM Studio API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse LM Studio response: {e}")
            return None
    
    def get_available_models(self) -> List[str]:
        """Get list of available models from LM Studio"""
        try:
            response = requests.get(self.models_endpoint, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'data' in data:
                return [model['id'] for model in data['data']]
            return []
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to get models from LM Studio: {e}")
            return []
    
    def health_check(self) -> bool:
        """Check if LM Studio is running and accessible"""
        try:
            response = requests.get(self.models_endpoint, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def test_vision_capability(self) -> bool:
        """Test if the current model supports vision/image inputs"""
        try:
            test_messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Can you see images?"
                        }
                    ]
                }
            ]
            
            response = self.chat_completion(test_messages, max_tokens=50)
            return response is not None and 'choices' in response
            
        except Exception as e:
            print(f"Vision capability test failed: {e}")
            return False
    
    def set_default_params(self, **params):
        """Update default parameters for requests"""
        self.default_params.update(params)