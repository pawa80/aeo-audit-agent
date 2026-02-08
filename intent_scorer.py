"""
AEO Audit Agent - Intent-Based Scorer

Calculates how well a page answers the user's selected intents using GPT-4o-mini.
"""

import json
from openai import OpenAI


def calculate_intent_score(
    full_content: str,
    title: str,
    first_paragraph: str,
    selected_intents: list[str],
    api_key: str
) -> dict:
    """
    Calculate how well a page answers the user's selected intents.

    Args:
        full_content: Full page content
        title: Page title
        first_paragraph: First paragraph of content
        selected_intents: List of user-selected intents to evaluate
        api_key: OpenAI API key

    Returns:
        {
            "total_score": 0-100,
            "content_presence_score": 0-60,
            "position_score": 0-20,
            "structure_score": 0-20,
            "intent_breakdown": [
                {"intent": "...", "present": True/False, "position": "first_paragraph|early|buried|missing", "has_structure": True/False}
            ]
        }
    """
    if not api_key:
        return {
            "total_score": 0,
            "content_presence_score": 0,
            "position_score": 0,
            "structure_score": 0,
            "intent_breakdown": [],
            "error": "OpenAI API key required"
        }

    if not selected_intents:
        return {
            "total_score": 0,
            "content_presence_score": 0,
            "position_score": 0,
            "structure_score": 0,
            "intent_breakdown": [],
            "error": "No intents selected"
        }

    client = OpenAI(api_key=api_key)

    # Truncate content to prevent token overflow
    content_for_analysis = full_content[:8000] if full_content else ""

    # Format intents as numbered list
    intents_list = "\n".join(f"{i+1}. {intent}" for i, intent in enumerate(selected_intents))

    prompt = f"""You are an AEO (Answer Engine Optimization) content analyst.

Evaluate how well this page content answers each of the following user intents.

PAGE TITLE: {title}

FIRST PARAGRAPH: {first_paragraph}

FULL CONTENT: {content_for_analysis}

INTENTS TO EVALUATE:
{intents_list}

For each intent, provide:
1. present: Is there a clear answer to this intent in the content? (true/false)
2. position: Where does the answer appear? ("first_paragraph", "early" (first 500 words), "buried" (after 500 words), "missing")
3. has_structure: Does the page have structural elements supporting this intent? (relevant heading, definition format, list, or clear statement) (true/false)

Return JSON only, no markdown code blocks:
{{
    "evaluations": [
        {{"intent": "exact intent text", "present": true, "position": "first_paragraph", "has_structure": true}},
        ...
    ]
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.3
        )

        result_text = response.choices[0].message.content.strip()

        # Clean up JSON if wrapped in markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()

        evaluations_data = json.loads(result_text)
        evaluations = evaluations_data.get("evaluations", [])

        # Calculate scores
        total_intents = len(selected_intents)

        # Content Presence Score (60%): (intents with present=true / total) * 60
        present_count = sum(1 for e in evaluations if e.get("present", False))
        content_presence_score = round((present_count / total_intents) * 60) if total_intents > 0 else 0

        # Position Score (20%): Average position score * 20
        position_scores = {
            "first_paragraph": 1.0,
            "early": 0.7,
            "buried": 0.3,
            "missing": 0.0
        }
        position_values = [position_scores.get(e.get("position", "missing"), 0) for e in evaluations]
        avg_position = sum(position_values) / len(position_values) if position_values else 0
        position_score = round(avg_position * 20)

        # Structure Score (20%): (intents with has_structure=true / total) * 20
        structure_count = sum(1 for e in evaluations if e.get("has_structure", False))
        structure_score = round((structure_count / total_intents) * 20) if total_intents > 0 else 0

        total_score = content_presence_score + position_score + structure_score

        return {
            "total_score": total_score,
            "content_presence_score": content_presence_score,
            "position_score": position_score,
            "structure_score": structure_score,
            "intent_breakdown": evaluations
        }

    except json.JSONDecodeError as e:
        return {
            "total_score": 0,
            "content_presence_score": 0,
            "position_score": 0,
            "structure_score": 0,
            "intent_breakdown": [],
            "error": f"Failed to parse LLM response: {str(e)}"
        }
    except Exception as e:
        return {
            "total_score": 0,
            "content_presence_score": 0,
            "position_score": 0,
            "structure_score": 0,
            "intent_breakdown": [],
            "error": f"Error calculating score: {str(e)}"
        }
