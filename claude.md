# Project: AEO Audit Agent

## Overview
A Streamlit-based tool that analyzes web pages for **Answer Engine Optimization (AEO)** - helping content rank better in AI search engines like ChatGPT, Perplexity, and Google AI Overviews.

## Current Version
v0.7 - Intelligence-Fed Recommendations

## What Changed in v0.7
- **Intelligence Feed**: New `intelligence_feed.py` module loads curated insights from `intelligence/current_feed.json`
- **Recommender upgraded**: `recommender.py` now injects 30 weeks of curated intelligence (trend alerts, counter-signals, citation patterns) into the GPT-4o-mini prompt alongside the static AEO_GUIDE
- **Voice preservation**: Prompt explicitly instructs NOT to flatten distinctive voice into corporate speak
- **Counter-signals**: Feed includes "DO NOT recommend" items (e.g., don't recommend FAQ schema as primary fix)
- **UI fixes**: Version updated to v0.7, "Perplexity" removed from UI copy, help text added for intent mismatch
- **Graceful fallback**: If `intelligence/current_feed.json` is missing, agent works exactly as v0.6

## Architecture
```
├── app.py                 # Streamlit UI and main application flow
├── analyzer.py            # Content extraction & analysis (BeautifulSoup)
├── intelligence_feed.py   # NEW: Loads curated intelligence from JSON feed
├── intelligence/
│   └── current_feed.json  # NEW: Curated intelligence data (updated weekly)
├── intent_extractor.py    # User intent extraction using GPT-4o-mini
├── query_generator.py     # LLM-based query generation (1-3 per intent)
├── perplexity_checker.py  # Citation checking via Perplexity API
├── recommender.py         # AI-powered recommendations (now intelligence-fed)
└── requirements.txt       # Dependencies
```

## Intelligence Feed
The intelligence feed (`intelligence/current_feed.json`) contains:
- **trend_alerts**: Current AI search trends with confidence levels
- **evolving_patterns**: Multi-week patterns with first_seen/latest_signal dates
- **counter_signals**: Things NOT to recommend (conventional wisdom that's now outdated)
- **citation_patterns**: Evidence-based patterns from GEO Tracker data (745 records)

To update: Edit `intelligence/current_feed.json` with new insights after each newsletter analysis. The feed version and date display in the UI header.

## UX Flow (v0.7)

1. **URL Input** → User enters URL and clicks "Analyze"
2. **Analysis Results** → Shows: Page info, first paragraph, content preview
3. **Intent Validation** → Shows 10 extracted intents as checkboxes
   - User selects 3-6 intents
   - Help text: if no intents match, may indicate positioning problem
   - "Confirm Intents" button to proceed
4. **Intent Relevance Score** → 0-100 with breakdown (Content /60, Position /20, Structure /20)
5. **Query Review** → User can deselect irrelevant queries before citation check
6. **Citation Check** → Queries checked against AI search engines (Perplexity API)
7. **Recommendations** → Intelligence-fed recommendations with trend references, voice preservation

## Key Modules

### intelligence_feed.py (NEW)
- `load_feed()` - Loads JSON feed, returns None if missing
- `get_feed_metadata()` - Returns version/date/weeks for UI display
- `get_current_feed()` - Formats feed as prompt-ready markdown string

### recommender.py (MODIFIED)
- Now imports `intelligence_feed`
- `generate_recommendations()` injects intelligence context after AEO_GUIDE
- max_tokens increased to 3000 to accommodate larger prompt
- Prompt instructs to reference intelligence, preserve voice, avoid generic advice

### app.py (MODIFIED)
- Imports `get_feed_metadata` for UI indicator
- Header shows intelligence feed version and date
- Version bumped to v0.7
- "Perplexity" removed from UI copy → "AI search engines"
- Help text added for intent validation

## Configuration
`.streamlit/secrets.toml`:
```toml
OPENAI_API_KEY = "sk-..."        # For query generation, intent extraction & recommendations
PERPLEXITY_API_KEY = "pplx-..."  # For citation checking
```

## Git Workflow
Commit and push to main branch. Pushes to main auto-deploy to Streamlit Cloud.

## Safety
- `v0.6-stable` tag on the commit before intelligence feed changes
- Intelligence feed is additive — removing the JSON file reverts to v0.6 behaviour

## Suite Context
- Part of Search Intelligence Suite (AEO Agent + GEO Tracker + Crawler)
- Supabase project exists: `dxduneaizaxnynsmsvbx.supabase.co`
- Identity layer already built by GEO Tracker
- When AEO Agent adds persistence (~v1.0): add `aeo_scores`, `aeo_recommendations` tables
- See Unified Dev Comms Notion page for cross-tool coordination

## Session State Variables
- `analysis_result` - AnalysisResult from analyzer
- `extracted_intents` - List of 10 intents from GPT
- `selected_intents` - List of 3-6 user-confirmed intents
- `intent_validated` - Boolean flag
- `intent_score` - 0-100 relevance score
- `intent_score_breakdown` - Detailed scoring breakdown
- `regenerated_queries` - Queries based on selected intents (1-3 per intent)
- `selected_queries` - User-confirmed queries for citation check
- `queries_confirmed` - Boolean flag
- `citation_results` - List of CitationResult
- `recommendations` - Recommendation dict

## Rolling Handover
**Last session:** 14 Feb 2026 (pal-ops chat)
- Implemented IDEA 1 from Three Power Ideas plan
- Created intelligence feed module + data
- Modified recommender to inject intelligence context
- Applied v0.7 UI fixes (version, Perplexity copy, intent help text)
- Safety: v0.6-stable tag pushed to remote
- **Next:** Deploy (push to main), test on a page, compare v0.6 vs v0.7 recommendations
