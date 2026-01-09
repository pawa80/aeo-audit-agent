"""
AEO Audit Agent - Content Analyzer Module

Functions for extracting and analyzing web page content for AEO optimization.
"""

import re
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup


@dataclass
class AnalysisResult:
    """Container for page analysis results."""
    url: str
    title: str
    total_word_count: int
    first_500_words: str
    first_paragraph: str
    has_direct_answer: bool
    direct_answer_score: int  # 0-100 score
    direct_answer_reasons: list[str]
    extraction_success: bool
    error_message: Optional[str] = None


def fetch_page_content(url: str, timeout: int = 10) -> tuple[str, Optional[str]]:
    """
    Fetch HTML content from a URL.

    Returns:
        Tuple of (html_content, error_message)
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AEOAuditBot/1.0)"
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text, None
    except requests.exceptions.Timeout:
        return "", "Request timed out. The page took too long to respond."
    except requests.exceptions.ConnectionError:
        return "", "Could not connect to the URL. Please check if it's valid."
    except requests.exceptions.HTTPError as e:
        return "", f"HTTP error: {e.response.status_code}"
    except requests.exceptions.RequestException as e:
        return "", f"Error fetching page: {str(e)}"


def extract_text_content(html: str) -> tuple[str, str, list[str]]:
    """
    Extract readable text content from HTML.

    Returns:
        Tuple of (full_text, title, paragraphs)
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove script, style, nav, footer, and other non-content elements
    for element in soup(["script", "style", "nav", "footer", "header",
                         "aside", "noscript", "iframe", "svg"]):
        element.decompose()

    # Get title
    title = ""
    if soup.title:
        title = soup.title.get_text(strip=True)

    # Try to find main content area
    main_content = (
        soup.find("main") or
        soup.find("article") or
        soup.find(attrs={"role": "main"}) or
        soup.find("div", class_=re.compile(r"content|article|post", re.I)) or
        soup.body or
        soup
    )

    # Extract paragraphs
    paragraphs = []
    for p in main_content.find_all(["p", "h1", "h2", "h3", "li"]):
        text = p.get_text(strip=True)
        if text and len(text) > 20:  # Filter out very short text
            paragraphs.append(text)

    # Get full text
    full_text = main_content.get_text(separator=" ", strip=True)
    # Clean up whitespace
    full_text = re.sub(r"\s+", " ", full_text)

    return full_text, title, paragraphs


def count_words(text: str) -> int:
    """Count words in text."""
    words = text.split()
    return len(words)


def get_first_n_words(text: str, n: int = 500) -> str:
    """Extract first N words from text."""
    words = text.split()
    return " ".join(words[:n])


def check_direct_answer(first_paragraph: str) -> tuple[bool, int, list[str]]:
    """
    Check if the first paragraph appears to be a direct answer.

    Returns:
        Tuple of (is_direct_answer, score, reasons)
    """
    if not first_paragraph:
        return False, 0, ["No first paragraph found"]

    score = 0
    reasons = []

    # Check 1: Length is appropriate (not too short, not too long)
    word_count = count_words(first_paragraph)
    if 20 <= word_count <= 100:
        score += 25
        reasons.append(f"Good length ({word_count} words) - concise but informative")
    elif word_count < 20:
        reasons.append(f"Too short ({word_count} words) - may lack detail")
    else:
        reasons.append(f"Long first paragraph ({word_count} words) - consider being more concise")
        score += 10

    # Check 2: Starts with a definitive statement (not a question)
    first_paragraph_lower = first_paragraph.lower()
    if not first_paragraph.strip().endswith("?"):
        if any(first_paragraph_lower.startswith(word) for word in
               ["the ", "a ", "an ", "it ", "this ", "there "]):
            score += 20
            reasons.append("Starts with a definitive statement")
    else:
        reasons.append("First paragraph is a question, not an answer")

    # Check 3: Contains defining language
    defining_patterns = [
        r"\bis\b", r"\bare\b", r"\bmeans\b", r"\brefers to\b",
        r"\bdefined as\b", r"\bknown as\b", r"\bcalled\b"
    ]
    if any(re.search(pattern, first_paragraph_lower) for pattern in defining_patterns):
        score += 20
        reasons.append("Contains defining language (is, are, means, etc.)")

    # Check 4: Doesn't start with weak phrases
    weak_starts = ["in this article", "in this post", "welcome to",
                   "today we", "let's", "click here", "subscribe"]
    if not any(first_paragraph_lower.startswith(phrase) for phrase in weak_starts):
        score += 15
        reasons.append("Doesn't start with weak/promotional phrases")
    else:
        reasons.append("Starts with weak/promotional phrase - get to the answer faster")

    # Check 5: Contains substantive information (numbers, specific terms)
    if re.search(r"\d+", first_paragraph):
        score += 10
        reasons.append("Contains specific numbers/data")

    # Check 6: Not overly promotional
    promo_words = ["buy", "purchase", "discount", "sale", "offer", "deal", "subscribe"]
    promo_count = sum(1 for word in promo_words if word in first_paragraph_lower)
    if promo_count == 0:
        score += 10
        reasons.append("Not promotional - focused on information")
    else:
        reasons.append("Contains promotional language")

    is_direct_answer = score >= 50

    return is_direct_answer, min(score, 100), reasons


def analyze_url(url: str) -> AnalysisResult:
    """
    Main analysis function - fetches and analyzes a URL.

    Returns:
        AnalysisResult with all analysis data
    """
    # Ensure URL has scheme
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Fetch content
    html, error = fetch_page_content(url)

    if error:
        return AnalysisResult(
            url=url,
            title="",
            total_word_count=0,
            first_500_words="",
            first_paragraph="",
            has_direct_answer=False,
            direct_answer_score=0,
            direct_answer_reasons=[],
            extraction_success=False,
            error_message=error
        )

    # Extract text
    full_text, title, paragraphs = extract_text_content(html)

    # Get metrics
    total_words = count_words(full_text)
    first_500 = get_first_n_words(full_text, 500)
    first_paragraph = paragraphs[0] if paragraphs else ""

    # Check for direct answer
    has_answer, answer_score, answer_reasons = check_direct_answer(first_paragraph)

    return AnalysisResult(
        url=url,
        title=title,
        total_word_count=total_words,
        first_500_words=first_500,
        first_paragraph=first_paragraph,
        has_direct_answer=has_answer,
        direct_answer_score=answer_score,
        direct_answer_reasons=answer_reasons,
        extraction_success=True
    )
