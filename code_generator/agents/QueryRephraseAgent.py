import json
from typing import Dict, Any, List, Optional
from utils.llm_client import llm_client

class QueryRephraseAgent:
    def __init__(self):
        self.system_prompt = """You are a Query Rephrase Agent in a multi-agent code generation system.

Your job:
1. Rephrase the user's input into a one-line developer task.
2. Check if the request is clear enough to move forward with **configuration parsing**, not full code generation.
3. Do not require file names, field names, or detailed paths — just clear intent and basic direction.
4. If basic intent is unclear, suggest 1-3 specific improvements.

Return valid JSON in this format:
{
  "developer_task": "<one-line task>",
  "is_satisfied": true | false,
  "suggestions": ["<suggestion 1>", "..."]  // only include if is_satisfied is false
}

What counts as 'satisfied':
- Clear development goal (ETL, report, dashboard, automation, etc.)
- Input/output types (API, DB, file, etc.)
- Basic processing need (if relevant)

Examples of insufficient info:
- Vague like 'do something with data'
- No clue where data comes from or goes to
"""


    def rephrase_query(
        self,
        user_query: str,
        conversation_history: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Rephrase query and return satisfaction status"""
        
        context = "\n".join(conversation_history) if conversation_history else "No prior context provided."
        
        prompt = f"""
User Query:
{user_query}

Previous Conversation Context:
{context}

Return a single-line developer task, a satisfaction flag (is_satisfied), and suggestions if the query is incomplete.
"""

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt
            )
            if response:
                cleaned = self._clean_json_response(response)
                return json.loads(cleaned)
            return None
        except Exception as e:
            print(f"Error in rephrasing query: {e}")
            return None

    def _clean_json_response(self, response: str) -> str:
        """Clean LLM response to extract valid JSON"""
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()
        return response.strip()
