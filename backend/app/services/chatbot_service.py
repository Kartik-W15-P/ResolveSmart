import os
import time
from typing import Dict, List, Optional
from google import genai
from google.genai import types

DEPARTMENT_SLA_MAP = {
    "Electricity & Power": 24,
    "Water Supply": 48,
    "Roads & Infrastructure": 168,  # 7 days
    "Sanitation & Waste": 48,
    "General Civic Issue": 72
}

MODEL_CANDIDATES = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash"
]


class ComplaintChatbot:
    """
    In-context grounded AI assistant bounded strictly to a single complaint's
    lifecycle state, status timeline, and department SLA policy.
    """

    @classmethod
    def get_client(cls) -> Optional[genai.Client]:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        return genai.Client(api_key=api_key)

    @classmethod
    def generate_response(
        cls,
        complaint_data: Dict,
        timeline_events: List[Dict],
        user_message: str
    ) -> Dict[str, str]:
        client = cls.get_client()
        if not client:
            return {
                "status": "error",
                "message": "AI Assistant is temporarily unconfigured (GEMINI_API_KEY missing)."
            }

        category = complaint_data.get("category") or "General Civic Issue"
        sla_hours = DEPARTMENT_SLA_MAP.get(category, 72)

        timeline_summary = []
        for e in timeline_events:
            ts = e.get("created_at", "Unknown time")
            st = e.get("status", "unknown")
            rm = e.get("remarks") or "No remarks provided"
            timeline_summary.append(f"- [{ts}] Status: {st} | Remarks: {rm}")

        timeline_text = "\n".join(timeline_summary) if timeline_summary else "No historical events recorded."

        system_instruction = f"""You are the ResolveSmart Municipal Redressal Assistant.
Your sole job is to answer questions for citizens and officers regarding THIS SPECIFIC COMPLAINT.

GROUNDING RULES:
1. You may ONLY answer questions using the provided COMPLAINT RECORD, STATUS TIMELINE, and SLA POLICY below.
2. If the user asks about anything unrelated to this specific complaint, civic grievance rules, or municipal resolution procedures (e.g. general coding, jokes, politics, weather, recipes, trivia), you MUST decline politely with:
   "I can only assist with questions regarding this specific grievance (#{complaint_data.get('complaint_number')}) and official municipal redressal procedures."
3. Do NOT hallucinate names, contact numbers, or dates not provided in the data.
4. Keep answers concise, factual, professional, and empathetic.

CURRENT COMPLAINT RECORD:
- Tracking Number: {complaint_data.get('complaint_number')}
- Title: {complaint_data.get('title')}
- Description: {complaint_data.get('description')}
- Category: {category}
- Priority: {complaint_data.get('priority')}
- Current Status: {complaint_data.get('status')}
- Location / Address: {complaint_data.get('address') or 'Coordinates on file'}
- Is Flagged as Duplicate: {complaint_data.get('is_duplicate')}
- Filed Date: {complaint_data.get('created_at')}
- Standard Resolution SLA: Within {sla_hours} hours from filing.

STATUS TIMELINE & OFFICER REMARKS:
{timeline_text}
"""

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
            max_output_tokens=300
        )

        last_error = None
        for model_name in MODEL_CANDIDATES:
            try:
                chat = client.chats.create(
                    model=model_name,
                    config=config
                )
                response = chat.send_message(user_message)
                if response and response.text:
                    return {
                        "status": "success",
                        "reply": response.text.strip(),
                        "model_used": model_name
                    }
            except Exception as exc:
                last_error = str(exc)
                time.sleep(0.5)
                continue

        return {
            "status": "error",
            "message": f"AI service error: {last_error}"
        }