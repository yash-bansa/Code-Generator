import json
import logging
from typing import Dict, Any, List, Optional
from utils.llm_client import llm_client
import jsonschema

logger = logging.getLogger(__name__)

class QueryRephraseAgent:
    def __init__(self):
        self.system_prompt = """You are a Query Rephrase Agent in a multi-agent code generation system.

ROLE: Transform user queries into actionable developer tasks and assess readiness for configuration parsing.

PROCESS:
1. Extract core intent from user query and conversation history
2. Rephrase into a single, clear developer task (one sentence)
3. Evaluate if sufficient information exists for configuration parsing (NOT full code generation)
4. Provide 1-3 specific, actionable suggestions if incomplete

SATISFACTION CRITERIA (for configuration parsing):
✓ Clear development goal (ETL, API integration, dashboard, data analysis, automation, report generation)
✓ Defined input source (database, API, CSV file, JSON, manual input, etc.)
✓ Defined output target (database, file, dashboard, API response, email, etc.)
✓ Basic processing requirements (if applicable: filtering, aggregation, transformation)

Note: Do NOT require specific file names, field names, or detailed paths - just clear intent and direction.

RESPONSE FORMAT (return ONLY valid JSON):
{
  "developer_task": "Single clear sentence describing the task",
  "is_satisfied": true | false,
  "suggestions": ["specific improvement 1", "specific improvement 2"]
}

EXAMPLES:
✓ Good (satisfied): 
- "Create ETL pipeline to extract customer data from PostgreSQL and generate daily sales reports in Excel"
- "Build API endpoint to fetch user data from database and return JSON response"
- "Develop dashboard to visualize sales metrics from CSV files"

✗ Poor (not satisfied):
- "Do something with data" → suggest: specify data source, processing type, output format
- "Make a report" → suggest: specify data source, report content, output format
- "Process files" → suggest: specify file type, processing requirements, output destination

Focus on clarity of intent rather than technical implementation details."""

        self.schema = {
            "type": "object",
            "properties": {
                "developer_task": {"type": "string"},
                "is_satisfied": {"type": "boolean"},
                "suggestions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": []
                }
            },
            "required": ["developer_task", "is_satisfied"]
        }

    async def rephrase_query(
        self,
        user_query: str,
        conversation_history: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        if not user_query or not user_query.strip():
            return self._create_fallback_response(user_query)

        context = "\n".join(conversation_history) if conversation_history else "No prior context provided."

        prompt = f"""
User Query:
{user_query}

Previous Conversation Context:
{context}

Return a single-line developer task, a satisfaction flag (is_satisfied), and suggestions if the query is incomplete.
"""

        try:
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt
            )

            if response:
                cleaned = self._clean_json_response(response)
                parsed = json.loads(cleaned)
                jsonschema.validate(instance=parsed, schema=self.schema)
                return parsed

        except (json.JSONDecodeError, jsonschema.ValidationError) as err:
            logger.warning(f"[QueryRephraseAgent] Parse or validation error: {err}")
        except Exception as e:
            logger.error(f"[QueryRephraseAgent] Unexpected error: {e}")

        return self._create_fallback_response(user_query)

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

    def _create_fallback_response(self, user_query: str) -> Dict[str, Any]:
        """Create consistent fallback response"""
        return {
            "developer_task": user_query.strip() if user_query else "",
            "is_satisfied": False,
            "suggestions": [
                "Please specify your task clearly, including input source and output format.",
                "Example: 'Extract data from MySQL database and create Excel reports'"
            ]
        }
