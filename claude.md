# Project: AEO Audit Agent

## Git Workflow
Always commit and push directly to the main branch. Do not create feature branches.

## Tech Stack
- Streamlit for UI
- Python 3.11+
- Perplexity API for citation checking
- BeautifulSoup for content extraction

## API Keys
API keys are stored in Streamlit secrets, not in code. Never commit API keys.

## Deployment
App is deployed on Streamlit Cloud. Pushes to main auto-deploy.
```
