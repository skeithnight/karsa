import json
import re

def parse_review(response_text: str) -> dict:
    fallback = {
        "decision": "ESCALATED",
        "convergence_score": 0.0,
        "blocking_issues": ["Failed to parse review JSON"],
        "non_blocking_issues": []
    }
    
    text = response_text.strip()
    
    # Try direct parse
    try:
        data = json.loads(text)
        return _validate(data, fallback)
    except json.JSONDecodeError:
        pass
        
    # Try regex repair (extract between first { and last })
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return _validate(data, fallback)
        except json.JSONDecodeError:
            pass
            
    return fallback

def _validate(data: dict, fallback: dict) -> dict:
    if "decision" not in data or "convergence_score" not in data:
        return fallback
    
    decision = data["decision"]
    if decision not in ["APPROVED", "REVISE", "ESCALATED"]:
        data["decision"] = "REVISE"
        
    data["blocking_issues"] = data.get("blocking_issues", [])
    data["non_blocking_issues"] = data.get("non_blocking_issues", [])
    
    return data
