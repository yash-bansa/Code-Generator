import logging
from typing import Optional
from utils.llm_client import llm_client
from config.agents_io import CommunicationInput, CommunicationOutput  

logger = logging.getLogger(__name__)

class CommunicationAgent:
    def __init__(self):
        self.system_prompt = """You are a Communication Agent in a multi-agent code generation system.

Your job is to extract the user's core development intent from a conversation, including vague or incomplete instructions.

Instructions:
- Consider the entire conversation history as context.
- Identify what the user is trying to accomplish (their intent).
- Return two fields: 
    - 'core_intent' = the main dev task in one sentence
    - 'context_notes' = relevant prior conversation details that shaped this intent

Do not return implementation details or full solutions. Just clarify what the user *wants to do*.
"""

    async def extract_intent(self, input_data: CommunicationInput) -> CommunicationOutput:
        try:
            full_context = "\n".join(input_data.conversation_history + [input_data.user_query])

            prompt = f"""Conversation History:
{full_context}

Extract:
1. core_intent: (1-line clear dev goal)
2. context_notes: relevant hints from earlier turns
Return as JSON object.
"""

            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt
            )

            if response:
                cleaned = self._extract_json(response)
                parsed = CommunicationOutput.model_validate_json(cleaned)
                return parsed

        except Exception as e:
            logger.warning(f"[CommunicationAgent] Error extracting intent: {e}")

        # fallback
        return CommunicationOutput(
            core_intent=input_data.user_query.strip(),
            context_notes="",
            success=False,
            message="Failed to extract intent from conversation"
        )

    def _extract_json(self, response: str) -> str:
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            return response[start:end].strip()
        return response.strip()
