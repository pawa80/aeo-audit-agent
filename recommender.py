"""
AEO Audit Agent - Recommendations Engine

Uses OpenAI GPT-4o-mini to generate actionable recommendations for improving
a page's chances of being cited by AI search engines.
"""

from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class RecommendationResult:
    """Result of recommendation generation."""
    recommendations: list[str]
    success: bool
    error: Optional[str] = None


def generate_recommendations(
    title: str,
    first_paragraph: str,
    first_500_words: str,
    direct_answer_score: int,
    citation_results: Optional[list] = None,
    api_key: str = "",
    model: str = "gpt-4o-mini",
    max_tokens: int = 300,
    temperature: float = 0.7
) -> RecommendationResult:
    """
    Generate AEO recommendations using OpenAI GPT-4o-mini.

    Args:
        title: Page title
        first_paragraph: First paragraph of content
        first_500_words: First 500 words of content
        direct_answer_score: Score from direct answer analysis (0-100)
        citation_results: Optional list of citation check results
        api_key: OpenAI API key
        model: Model to use (default: gpt-4o-mini)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature

    Returns:
        RecommendationResult with recommendations and status
    """
    if not api_key:
        return RecommendationResult(
            recommendations=[],
            success=False,
            error="OpenAI API key not provided"
        )

    endpoint = "https://api.openai.com/v1/chat/completions"

    # Build citation context
    citation_context = ""
    if citation_results:
        cited_queries = [r.query for r in citation_results if r.cited]
        not_cited_queries = [r.query for r in citation_results if not r.cited and not r.error]

        if cited_queries:
            citation_context += f"\nQueries where page WAS cited: {', '.join(cited_queries)}"
        if not_cited_queries:
            citation_context += f"\nQueries where page was NOT cited: {', '.join(not_cited_queries)}"

    # Build content context
    content_context = f"""Page Title: {title}

First Paragraph: {first_paragraph}

Content Excerpt (first 500 words): {first_500_words[:1500]}

Direct Answer Score: {direct_answer_score}/100
{citation_context}"""

    prompt = """You are an AEO (Answer Engine Optimization) expert. Based on this content analysis, provide exactly 3 specific, actionable recommendations to improve this page's chances of being cited by AI search engines like ChatGPT, Perplexity, and Google AI Overviews.

Be specific - reference actual content from the page. Focus on:
- How to make the opening more "answer-ready"
- Structural improvements for AI parsing
- Content gaps that would help AI cite this page

Format: one recommendation per line, no numbering or bullet points. Each should be 1-2 sentences max."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content_context}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        return RecommendationResult(
            recommendations=[],
            success=False,
            error="Request timed out"
        )
    except requests.exceptions.HTTPError as e:
        error_msg = f"API error: {e.response.status_code}"
        if e.response.status_code == 401:
            error_msg = "Invalid API key"
        elif e.response.status_code == 429:
            error_msg = "Rate limit exceeded"
        return RecommendationResult(
            recommendations=[],
            success=False,
            error=error_msg
        )
    except requests.exceptions.RequestException as e:
        return RecommendationResult(
            recommendations=[],
            success=False,
            error=f"Request failed: {str(e)}"
        )

    # Parse response
    try:
        content = data["choices"][0]["message"]["content"].strip()
        # Split by newlines and clean up
        recommendations = [r.strip() for r in content.split("\n") if r.strip()]

        # Remove any numbering or bullet points
        cleaned = []
        for rec in recommendations:
            # Remove common prefixes
            cleaned_rec = rec.lstrip("0123456789.-)*•→ ").strip()
            if cleaned_rec and len(cleaned_rec) > 10:
                cleaned.append(cleaned_rec)

        if len(cleaned) >= 3:
            return RecommendationResult(
                recommendations=cleaned[:3],
                success=True
            )
        elif cleaned:
            # Return what we have even if fewer than 3
            return RecommendationResult(
                recommendations=cleaned,
                success=True
            )
        else:
            return RecommendationResult(
                recommendations=[],
                success=False,
                error="Could not parse recommendations from response"
            )

    except (KeyError, IndexError) as e:
        return RecommendationResult(
            recommendations=[],
            success=False,
            error=f"Failed to parse response: {str(e)}"
        )
