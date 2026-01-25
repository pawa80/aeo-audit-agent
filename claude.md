# Project: AEO Audit Agent

## Overview
A Streamlit-based tool that analyzes web pages for **Answer Engine Optimization (AEO)** - helping content rank better in AI search engines like ChatGPT, Perplexity, and Google AI Overviews.

## Architecture

```
├── app.py                 # Streamlit UI
├── analyzer.py            # Content extraction & analysis
├── query_generator.py     # LLM-based query generation
├── perplexity_checker.py  # Citation checking via Perplexity API
├── recommender.py         # AI-powered recommendations
└── requirements.txt       # Dependencies
```

## Features

### 1. Content Analysis (`analyzer.py`)
- Fetches page HTML with proper error handling
- Extracts: title, paragraphs, headings (H1/H2/H3), full text
- Calculates total word count, first 500 words
- **Direct Answer Score** (0-100) based on:
  - First paragraph length (20-100 words ideal)
  - Starts with definitive statement
  - Contains defining language ("is", "are", "means")
  - Avoids weak/promotional phrases
  - Contains specific data/numbers

### 2. Smart Query Generation (`query_generator.py`)
- Uses **GPT-4o-mini** to generate 3 realistic search queries
- Falls back to rule-based generation if no API key
- Extracts topic from title (strips "My take on...", site suffixes, etc.)
- UI shows whether queries are "AI-generated" or "rule-based fallback"

### 3. Citation Checking (`perplexity_checker.py`)
- Sends queries to **Perplexity API** (sonar model)
- Checks if target URL appears in citations
- Returns: cited (bool), sources found, response snippet
- Displays citation rate and competing sources

### 4. AI Recommendations (`recommender.py`)
- Uses **GPT-4o-mini** with full context:
  - Page title, first paragraph, first 500 words
  - Direct answer score
  - Heading structure (H1/H2/H3 counts + actual headings)
  - Citation results (which queries were/weren't cited)
- Returns 3 specific, actionable recommendations

## UI Flow
1. **URL Input** → Enter page to analyze
2. **Analyze** → Extracts content, scores direct answer quality
3. **Citation Check** → Tests if Perplexity cites the page (requires API key)
4. **Get Recommendations** → AI suggestions for improvement (requires API key)

## Tech Stack

- Streamlit for UI
- Python 3.11+
- OpenAI GPT-4o-mini for query generation, intent extraction, and recommendations
- Perplexity API for citation checking
- BeautifulSoup for content extraction
=======
- **Streamlit** - UI framework
- **Python 3.11+**
- **OpenAI API** (GPT-4o-mini) - Query generation & recommendations
- **Perplexity API** (sonar model) - Citation checking
- **BeautifulSoup + lxml** - HTML parsing
- **requests** - HTTP client

## Configuration
`.streamlit/secrets.toml`:
```toml
OPENAI_API_KEY = "sk-..."        # For query generation & recommendations
PERPLEXITY_API_KEY = "pplx-..."  # For citation checking
```

## Git Workflow
Commit and push to main branch. Pushes to main auto-deploy to Streamlit Cloud.

## API Keys
API keys are stored in Streamlit secrets, not in code. Never commit API keys.
- `OPENAI_API_KEY` - Required for smart query generation, intent extraction, and recommendations
- `PERPLEXITY_API_KEY` - Required for citation checking


## Deployment
App is deployed on Streamlit Cloud. Pushes to main auto-deploy.

## Current Version
v0.3 - Intent Validation

## Architecture
```
├── app.py                 # Streamlit UI and main application flow
├── analyzer.py            # Content extraction & analysis (BeautifulSoup)
├── intent_extractor.py    # User intent extraction using GPT-4o-mini
├── query_generator.py     # LLM-based query generation
├── perplexity_checker.py  # Citation checking via Perplexity API
├── recommender.py         # AI-powered recommendations
└── requirements.txt       # Dependencies
```

## UX Flow (v0.3)

1. **URL Input** → User enters URL and clicks "Analyze"
2. **Analysis Results** → Shows: Page info, Direct Answer Score (0-100), first paragraph, content preview
3. **Intent Validation** → Shows 10 extracted intents as checkboxes
   - User selects 3-6 intents
   - "Select All" / "Select None" buttons available
   - Validation prevents <3 or >6 selections
   - "Confirm Intents" button to proceed
4. **Citation Check** → Queries regenerated based on selected intents
   - "Check Citations" button → Perplexity API call
   - Shows citation rate and competing sources
5. **Recommendations** → "Get Recommendations" button → 3 actionable improvement suggestions

## Key Modules

### analyzer.py
- `AnalysisResult` dataclass with all analysis data
- `fetch_page_content()` - HTTP fetch with User-Agent
- `extract_text_content()` - Returns (full_text, title, paragraphs, headings)
- `check_direct_answer()` - Scores first paragraph (0-100)
- `smart_generate_queries()` - LLM with rule-based fallback
- `analyze_url()` - Main entry point

### intent_extractor.py
- `IntentExtractionResult` dataclass
- `extract_intents()` - Returns 10 user intents using GPT-4o-mini
- Prompt focuses on business intent + user intent phrases
- Extra weight on title, first paragraph, first 200 words

### query_generator.py
- `QueryGenerationResult` dataclass
- `generate_queries_with_llm()` - General query generation
- `generate_queries_from_intents()` - Generates 3 queries based on selected intents
- `get_fallback_queries()` - Rule-based fallback

### perplexity_checker.py
- `CitationResult` dataclass
- `check_citation()` - Single query check
- `check_all_queries()` - Batch check
- `get_citation_summary()` - Aggregated stats

### recommender.py
- `RecommendationResult` dataclass
- `generate_recommendations()` - Returns 3 actionable recommendations
- Accepts headings for structure-aware recommendations
- Context includes citation results

## Session State Variables
- `analysis_result` - AnalysisResult from analyzer
- `extracted_intents` - List of 10 intents from GPT
- `selected_intents` - List of 3-6 user-confirmed intents
- `intent_validated` - Boolean flag
- `regenerated_queries` - Queries based on selected intents
- `citation_results` - List of CitationResult
- `recommendations` - RecommendationResult

## Direct Answer Score Criteria
- Length check (20-100 words ideal)
- Starts with definitive statement
- Contains defining language (is, are, means)
- No weak/promotional phrases
- Contains specific numbers/data
- Not overly promotional

## Intent Extraction Prompt
```
This is agentic search (AEO) optimisation. Your job is to detect what the business intent and the user intent is on this page, and find the key phrases that:
a) the current content indicates
b) the business looks to be wanting

Review the entire text context, but put extra weight on title, first paragraph and first 200 words. Look for question-answer format patterns.

Output exactly 10 phrases to optimise for. These phrases represent user intents - what users would search for that this page should answer.

Return as a numbered list, one phrase per line, no explanations.
```

## Graceful Fallbacks
- No OpenAI key: Skip intent extraction, show "Skip Intent Validation" button
- Intent extraction fails: Allow skipping, use original queries
- Query regeneration fails: Use original queries with warning
- No Perplexity key: Disable citation check button with info message

## Key Design Decisions
- Separate buttons for Analyze vs Citation Check (controls API costs)
- Session state preserves results between interactions
- Graceful fallbacks when API keys unavailable
- Headings extracted for structure-aware recommendations
