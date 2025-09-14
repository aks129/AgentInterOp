"""Claude integration for Banterop UI - narrative synthesis and analysis"""
import os
from typing import Dict, Any, Optional, List
from anthropic import Anthropic
import json

# Check if API key is available
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_ENABLED = bool(ANTHROPIC_API_KEY)

# Initialize client if key is available
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if CLAUDE_ENABLED else None


def is_claude_available() -> bool:
    """Check if Claude integration is available"""
    return CLAUDE_ENABLED


def synthesize_narrative(
    role: str,
    transcript: List[Dict[str, Any]],
    patient_facts: Optional[Dict[str, Any]] = None,
    guidelines: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Synthesize a narrative summary from conversation transcript

    Args:
        role: "applicant" or "administrator" - perspective to synthesize from
        transcript: List of message exchanges
        patient_facts: Optional patient facts/data
        guidelines: Optional guideline evaluation results

    Returns:
        Dict with narrative and analysis
    """
    if not CLAUDE_ENABLED:
        return {
            "disabled": True,
            "message": "Claude integration disabled - ANTHROPIC_API_KEY not configured"
        }

    try:
        # Build context for Claude
        context_parts = []

        # Add transcript
        context_parts.append("## Conversation Transcript\n")
        for msg in transcript:
            sender = msg.get("sender", "Unknown")
            text = msg.get("text", "")
            context_parts.append(f"**{sender}**: {text}")

        # Add patient facts if available
        if patient_facts:
            context_parts.append("\n## Patient Facts")
            context_parts.append(json.dumps(patient_facts, indent=2))

        # Add guidelines if available
        if guidelines:
            context_parts.append("\n## Guideline Evaluation")
            context_parts.append(json.dumps(guidelines, indent=2))

        context = "\n".join(context_parts)

        # Role-specific prompts
        if role == "applicant":
            prompt = f"""You are synthesizing a patient's perspective on their healthcare screening conversation.

{context}

Please provide:
1. A brief narrative summary (2-3 sentences) of what the patient learned
2. Key takeaways from the patient's perspective
3. Any recommended next steps for the patient

Format as JSON with keys: narrative, takeaways (list), next_steps (list)"""

        else:  # administrator
            prompt = f"""You are synthesizing a healthcare administrator's assessment of a screening conversation.

{context}

Please provide:
1. A clinical summary (2-3 sentences) of the screening outcome
2. Guideline compliance assessment
3. Recommended clinical actions

Format as JSON with keys: summary, compliance, recommendations (list)"""

        # Call Claude
        response = anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse response
        content = response.content[0].text
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # If not valid JSON, return as narrative
            result = {"narrative": content}

        return {
            "success": True,
            "role": role,
            "analysis": result
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def evaluate_guideline_rationale(
    patient_facts: Dict[str, Any],
    evaluation: Dict[str, Any],
    guidelines: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate detailed rationale for guideline evaluation

    Args:
        patient_facts: Patient demographic and clinical data
        evaluation: BCS evaluation result
        guidelines: Current guideline rules

    Returns:
        Dict with detailed rationale
    """
    if not CLAUDE_ENABLED:
        return {
            "disabled": True,
            "message": "Claude integration disabled - ANTHROPIC_API_KEY not configured"
        }

    try:
        prompt = f"""Analyze this breast cancer screening eligibility decision:

Patient Facts:
{json.dumps(patient_facts, indent=2)}

Evaluation Result:
{json.dumps(evaluation, indent=2)}

Guidelines Used:
{json.dumps(guidelines, indent=2)}

Provide a clear, patient-friendly explanation of:
1. Why this recommendation was made
2. Which specific guideline criteria were considered
3. What factors influenced the decision
4. Any caveats or exceptions to note

Format as JSON with keys: rationale, criteria_met (list), key_factors (list), caveats (list)"""

        response = anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=600,
            temperature=0.2,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        content = response.content[0].text
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            result = {"rationale": content}

        return {
            "success": True,
            "analysis": result
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def complete_conversation(
    messages: List[Dict[str, Any]],
    system_prompt: Optional[str] = None,
    max_tokens: int = 500
) -> Dict[str, Any]:
    """
    General-purpose Claude completion for conversation

    Args:
        messages: Conversation history
        system_prompt: Optional system prompt
        max_tokens: Maximum response tokens

    Returns:
        Dict with Claude's response
    """
    if not CLAUDE_ENABLED:
        return {
            "disabled": True,
            "message": "Claude integration disabled - ANTHROPIC_API_KEY not configured"
        }

    try:
        # Convert to Claude message format
        claude_messages = []
        for msg in messages:
            role = "user" if msg.get("role") == "user" else "assistant"
            content = msg.get("content", msg.get("text", ""))
            claude_messages.append({"role": role, "content": content})

        # Add system prompt if provided
        kwargs = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": max_tokens,
            "temperature": 0.5,
            "messages": claude_messages
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = anthropic_client.messages.create(**kwargs)

        return {
            "success": True,
            "content": response.content[0].text,
            "model": response.model,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }