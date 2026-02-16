# Project: AEO Audit Agent

## Overview
A Streamlit-based tool that analyzes web pages for **Answer Engine Optimization (AEO)** - helping content rank better in AI search engines like ChatGPT, Perplexity, and Google AI Overviews.

## Current Version
v0.9.1 - Competitor CSV Export ✅ DEPLOYED

## Ongoing Instructions
- **Output style**: Start each output declaring what you're working on, e.g. "I'm [something] chat"
- **State transfer**: Keep this local claude.md updated as the primary state transfer file. Also update global CLAUDE.md for cross-chat awareness.
- **Notion master index**: Update the AEO entry (PRCS008) in [Pal's Software & Tools Index](https://www.notion.so/All-of-Pals-Software-App-Tools-Automations-and-Functions-Across-All-Tools-3079fa1ce4f580e28a9fcf10743b2584) when significant features ship.
- **Product spec**: No separate product spec file — all product details live in this claude.md.

## What Changed in v0.9.1
- **CSV export for competitor analysis**: "Download Competitor Report (CSV)" button in Competitor Analysis section
- **`extract_base_domain()` helper**: Collapses subdomains (blog.example.com -> example.com) for cleaner grouping
- **`create_competitor_csv()` function**: Aggregates non-cited query sources by base domain, top 50, semicolon-separated for Excel
- **PDF fix**: `break_long_words()` + `safe_multi_cell()` prevent fpdf overflow on long URLs

## What Changed in v0.9
- **Competitor URL display**: New "Competitor Analysis" UI section between Citation Results and Recommendations
- **`build_competitor_profile()` helper**: Groups cited URLs by domain (using `urlparse`), filters out user's own domain, returns sorted by frequency
- **Domain-grouped UI**: Shows each competing domain, how many queries it appeared in, expandable list of specific URLs
- **Recommender enhanced**: Top-5 competitor domains injected into GPT prompt as "Top Competing Sources" section — enables differentiation strategy recommendations
- **PDF report updated**: "Top Competing Domains" section added after citation rate summary
- **`citation_dicts` enriched**: Both recommender and PDF paths now include `sources_found` per citation result
- **Version bump**: v0.8 → v0.9 in header (2 places) and footer

## What Changed in v0.8
- **Intelligence-first architecture**: Intelligence items are now an explicit evaluation checklist — the model MUST evaluate every item against the page and return a verdict (APPLIES/NOT_APPLICABLE/RESPECTED)
- **New `intelligence_applied` output**: JSON response includes top-level array showing which intelligence items were used and how
- **`intelligence_source` per action**: Every action plan item must cite which intelligence item or AEO principle drives it
- **UI: Intelligence Analysis panel**: Visible section showing applied intelligence (red), respected counter-signals (green), and non-applicable items (collapsed)
- **`get_checklist_prompt()`**: New function in `intelligence_feed.py` formats intelligence items as evaluatable checklist
- **max_tokens 3000→4000**: Accommodates richer structured output

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
├── intelligence_feed.py   # Loads curated intelligence from JSON feed
├── intelligence/
│   └── current_feed.json  # Curated intelligence data (updated weekly)
├── intent_extractor.py    # User intent extraction using GPT-4o-mini
├── query_generator.py     # LLM-based query generation (1-3 per intent)
├── perplexity_checker.py  # Citation checking via Perplexia API
├── recommender.py         # AI-powered recommendations (intelligence-fed)
└── requirements.txt       # Dependencies
```

## Intelligence Feed
The intelligence feed (`intelligence/current_feed.json`) contains:
- **trend_alerts**: Current AI search trends with confidence levels
- **evolving_patterns**: Multi-week patterns with first_seen/latest_signal dates
- **counter_signals**: Things NOT to recommend (conventional wisdom that's now outdated)
- **citation_patterns**: Evidence-based patterns from GEO Tracker data (745 records)

To update: Edit `intelligence/current_feed.json` with new insights after each newsletter analysis. The feed version and date display in the UI header.

## UX Flow (v0.9)

1. **URL Input** → User enters URL and clicks "Analyze"
2. **Analysis Results** → Shows: Page info, first paragraph, content preview
3. **Intent Validation** → Shows 10 extracted intents as checkboxes
   - User selects 3-6 intents
   - Help text: if no intents match, may indicate positioning problem
   - "Confirm Intents" button to proceed
4. **Intent Relevance Score** → 0-100 with breakdown (Content /60, Position /20, Structure /20)
5. **Query Review** → User can deselect irrelevant queries before citation check
6. **Citation Check** → Queries checked against AI search engines (Perplexia API)
7. **Competitor Analysis** → Domain-grouped view of what's being cited instead (top 10 domains, expandable URLs per domain)
8. **Intelligence Analysis** → Panel showing which intelligence items apply, counter-signals respected, N/A items
9. **Recommendations** → Intelligence-driven recommendations with competitor context and explicit intelligence sources per action

## Key Modules

### intelligence_feed.py
- `load_feed()` - Loads JSON feed, returns None if missing
- `get_feed_metadata()` - Returns version/date/weeks for UI display
- `get_current_feed()` - Formats feed as prompt-ready markdown string (v0.7, still used as fallback)
- `get_checklist_prompt()` - **v0.8**: Formats intelligence items as evaluatable checklist with verdicts
- `get_aeo_guide()` - Loads Notion-synced AEO Guide from markdown file

### recommender.py
- Intelligence-first prompt: model must evaluate every intelligence item with APPLIES/NOT_APPLICABLE/RESPECTED verdict
- Output JSON includes `intelligence_applied` array + `intelligence_source` per action plan item
- **v0.9**: Top-5 competitor domains injected into prompt as "Top Competing Sources" section
- max_tokens=4000, temperature=0.3
- Falls back to hardcoded AEO_GUIDE if Notion-synced file missing

### app.py
- **v0.9.1**: `extract_base_domain()` + `create_competitor_csv()` — CSV export for competitor data
- **v0.9.1**: `break_long_words()` + `safe_multi_cell()` — PDF hardening for long URLs
- **v0.9**: `build_competitor_profile()` helper — groups sources by domain, excludes user's own domain
- **v0.9**: Competitor Analysis UI section with domain-grouped expandable view + CSV download button
- Intelligence Analysis panel: shows applied items (red), respected counter-signals (green), N/A items (collapsed)
- Action plan items display `intelligence_source` field
- Header shows feed version + weeks of data
- v0.9.1, "AI search engines" copy, intent help text

## Configuration
`.streamlit/secrets.toml`:
```toml
OPENAI_API_KEY = "sk-..."        # For query generation, intent extraction & recommendations
PERPLEXITY_API_KEY = "pplx-..."  # For citation checking
```

## Git Workflow
Commit and push to main branch. Pushes to main auto-deploy to Streamlit Cloud.

## Safety
- `v0.8-stable` tag on commit `69def97` (before v0.9 competitor URL changes)
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
**Last session:** 16 Feb 2026

### Deployed to main
1. **v0.7 Intelligence-fed recommendations** (commit 98cb774) — 14 Feb
2. **Dynamic AEO Guide from Notion** (commit b36d1aa) — 14 Feb
3. **v0.8 Intelligence-first architecture** (commit 499baee) — 15 Feb
   - `intelligence_feed.py` added `get_checklist_prompt()` — 13 items as evaluatable checklist
   - `recommender.py` restructured: intelligence-first prompt, `intelligence_applied` array, `intelligence_source` per action
   - `app.py` Intelligence Analysis panel, version v0.8
4. **PDF report download fixed** (commit 612609b) — 15 Feb
   - Uncommented PDF download button (disabled since v0.3)
   - Added intelligence sections to PDF (verdicts, sources)
   - Hardened `sanitize_for_pdf` for GPT output (arrows, emoji, checkmarks)
   - Wrapped in try/except — degrades gracefully if exotic chars slip through
5. **v0.9 Competitor URL display** (commit 7515644) — 15 Feb
   - `build_competitor_profile()` helper in `app.py` — groups sources by domain via `urlparse`
   - Competitor Analysis UI section between citation results and recommendations
   - Top-5 competitor domains injected into GPT prompt for differentiation strategies
   - PDF report includes "Top Competing Domains" section
   - `citation_dicts` enriched with `sources_found` in both recommender and PDF paths
6. **PDF fix — long word overflow** (commit 49e4a99) — 15 Feb
   - `break_long_words()` + `safe_multi_cell()` helpers prevent fpdf "not enough horizontal space" error
7. **v0.9.1 CSV export** (commit d3d9b14) — 16 Feb
   - "Download Competitor Report (CSV)" button in Competitor Analysis section
   - `extract_base_domain()` collapses subdomains for cleaner grouping
   - `create_competitor_csv()` — top 50 domains, semicolon-separated for Excel compatibility

### This Session (16 Feb 2026)
- Implemented v0.9 competitor URL display (plan from previous session)
- Created safety tag `v0.8-stable` on `69def97` before deploying
- Hit PDF generation bug — long unbreakable URLs caused fpdf "not enough horizontal space" error
- Fixed with `break_long_words()` + `safe_multi_cell()` wrappers on all `multi_cell` calls
- Implemented v0.9.1 CSV export per Pal's spec (extract_base_domain, create_competitor_csv)
- Updated Notion PRCS008 entry (was outdated at v0.7, now shows v0.9)
- **Not yet tested by Pal**: v0.9/v0.9.1 competitor features need testing on a page with <100% citation rate

### Validation
- **Morten feedback (v0.8):** Brilliant. Used on 20+ pages for Fyresign client work. Production-ready for client-facing reports.
- **v0.9/v0.9.1 needs testing:** Competitor analysis + CSV export on a page with <100% citation rate

### Backlogged
- **Suite-level escalation signal**: When 0% citation rate, flag domain-level problem. Requires suite data. Noted in AEO Roadmap on Notion.

### Sequencing Plan (Posted to Unified Dev Comms)
- AEO to v1.0 (Supabase) → GEO to v3.0 (dynamic keywords) → Suite MVP (shared auth + handoff)

### To Update AEO Guide
1. Edit Notion page: https://www.notion.so/2f49fa1ce4f5805dac3edce68f48be61
2. Run `python sync_aeo_guide.py` (needs NOTION_API_KEY in env or .streamlit/secrets.toml)
3. Commit + push to main

### Next Priority
**v1.0:** Supabase persistence (suite integration - enables historical tracking, user workspaces)