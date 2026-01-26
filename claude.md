# Project: AEO Audit Agent

## Overview
A Streamlit-based tool that analyzes web pages for **Answer Engine Optimization (AEO)** - helping content rank better in AI search engines like ChatGPT, Perplexity, and Google AI Overviews.

## Current Version
v0.3 - Intent Validation (with variable query generation fix)

## Architecture
```
├── app.py                 # Streamlit UI and main application flow
├── analyzer.py            # Content extraction & analysis (BeautifulSoup)
├── intent_extractor.py    # User intent extraction using GPT-4o-mini
├── query_generator.py     # LLM-based query generation (1-3 per intent)
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
4. **Citation Check** → Queries generated based on selected intents (1-3 per intent)
   - "Check Citations" button → Perplexity API call
   - Shows citation rate and competing sources
5. **Recommendations** → "Get Recommendations" button → 3 actionable improvement suggestions

## Key Modules

### analyzer.py
- `AnalysisResult` dataclass with all analysis data including headings
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
- `generate_queries_with_llm()` - General query generation (3 queries)
- `generate_queries_from_intents()` - Generates 1-3 queries per selected intent
  - 3 intents → 3-9 queries
  - 6 intents → 6-18 queries
  - max_tokens=300 to accommodate larger output
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

## Configuration
`.streamlit/secrets.toml`:
```toml
OPENAI_API_KEY = "sk-..."        # For query generation, intent extraction & recommendations
PERPLEXITY_API_KEY = "pplx-..."  # For citation checking
```

## Git Workflow
Commit and push to main branch. Pushes to main auto-deploy to Streamlit Cloud.

## Session State Variables
- `analysis_result` - AnalysisResult from analyzer
- `extracted_intents` - List of 10 intents from GPT
- `selected_intents` - List of 3-6 user-confirmed intents
- `intent_validated` - Boolean flag
- `regenerated_queries` - Queries based on selected intents (1-3 per intent)
- `citation_results` - List of CitationResult
- `recommendations` - RecommendationResult

## Query Generation from Intents Prompt
```
Generate search queries based on these user intents.
Generate 1-3 queries per intent depending on the intent's complexity and search variations.
Each query should be a realistic phrase someone would type into an AI search engine.
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
- Variable query count (1-3 per intent) instead of fixed 3 total
