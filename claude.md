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

## Key Design Decisions
- Separate buttons for Analyze vs Citation Check (controls API costs)
- Session state preserves results between interactions
- Graceful fallbacks when API keys unavailable
- Headings extracted for structure-aware recommendations
