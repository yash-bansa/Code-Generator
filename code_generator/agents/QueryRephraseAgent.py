import logging
from typing import Optional
import json
from pydantic import ValidationError
from utils.llm_client import llm_client
from config.agents_io import QueryEnhancerInput, QueryEnhancerOutput

logger = logging.getLogger(__name__)

class QueryRephraserAgent:
    def __init__(self):
        self.system_prompt = """You are a Query Rephraser Agent in a multi-agent system for developer task generation.

ROLE:
- Refine the user's intent into a clear developer task (one line).
- Assess if it contains enough information for configuration parsing.
- Suggest 1–3 improvements if information is vague or missing.

SATISFACTION CHECKLIST:
✓ Is the input source clear? (e.g., CSV, API, Database)
✓ Is the output destination defined? (e.g., Excel, API response, dashboard)
✓ Is the task meaningful? (e.g., extract, transform, visualize, serve, monitor)

BAD EXAMPLES:
- "Do something with logs" → Suggest: what source? what to extract? output format?
- "Make a report" → Suggest: report on what? from where? in what format?

GOOD EXAMPLES:
- "Extract data from MongoDB and store as a cleaned CSV file"
- "Build an API to return customer orders from PostgreSQL"
- "Generate a dashboard from JSON files to visualize sales trends"

ONLY RETURN JSON in this format:
{
  "developer_task": "clarified one-line task",
  "is_satisfied": true or false,
  "suggestions": ["...", "..."]
}
"""

    async def enhance_query(self, input_data: QueryEnhancerInput) -> QueryEnhancerOutput:
        try:
            prompt = f"""User Intent:
{input_data.core_intent}

Conversation Context:
{input_data.context_notes or 'None'}

Return JSON with rephrased developer task, satisfaction flag, and any suggestions.
"""

            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=self.system_prompt
            )

            if response:
                cleaned = self._extract_json(response)
                parsed = QueryEnhancerOutput.model_validate_json(cleaned)
                return parsed

        except (ValidationError, json.JSONDecodeError) as e:
            logger.warning(f"[QueryRephraserAgent] Validation or JSON error: {e}")
            return QueryEnhancerOutput(
                developer_task=input_data.core_intent.strip(),
                is_satisfied=False,
                suggestions=["LLM returned invalid format."],
                success=False,
                message="Validation or JSON parsing error"
            )
        except Exception as e:
            logger.error(f"[QueryRephraserAgent] Unexpected LLM error: {e}")
            return QueryEnhancerOutput(
                developer_task=input_data.core_intent.strip(),
                is_satisfied=False,
                suggestions=["Unexpected system error."],
                success=False,
                message="Unexpected LLM error"
            )

    def _fallback_response(self, user_query: str) -> QueryEnhancerOutput:
        """Return a default response when LLM fails or input is unclear"""
        return QueryEnhancerOutput(
            developer_task=user_query.strip() or "Unclear task",
            is_satisfied=False,
            suggestions=[
                "Please include a clear goal (e.g., extract, visualize, automate)",
                "Mention input format/source (CSV, API, DB, etc.)",
                "Specify what output/result you expect (report, transformed file, dashboard)"
            ],
            success=False,
            message="Fallback used due to LLM failure"
        )

    def _extract_json(self, response: str) -> str:
        """Extract JSON block from LLM response if inside triple backticks"""
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            return response[start:end].strip()
        return response.strip()
