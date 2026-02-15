"""
AEO Audit Agent - Streamlit Application

A tool to analyze web pages for Answer Engine Optimization.
"""

import streamlit as st
from fpdf import FPDF
import base64
from datetime import datetime
from urllib.parse import urlparse
from analyzer import analyze_url, AnalysisResult
from perplexity_checker import check_all_queries, get_citation_summary, CitationResult
from recommender import generate_recommendations
from intent_extractor import extract_intents
from query_generator import generate_queries_from_intents
from intent_scorer import calculate_intent_score
from intelligence_feed import get_feed_metadata


def build_competitor_profile(citation_results, target_url):
    """Group cited URLs by domain, excluding the user's own domain.

    Returns sorted list: [{domain, count, urls, queries}]
    where count = number of queries the domain appeared in.
    """
    target_domain = urlparse(target_url).netloc.lower().replace('www.', '')
    domain_data = {}

    for result in citation_results:
        if not result.sources_found:
            continue
        for source_url in result.sources_found:
            try:
                parsed = urlparse(source_url)
                domain = parsed.netloc.lower().replace('www.', '')
            except Exception:
                continue
            if not domain or domain == target_domain:
                continue
            if domain not in domain_data:
                domain_data[domain] = {'domain': domain, 'urls': set(), 'queries': set()}
            domain_data[domain]['urls'].add(source_url)
            domain_data[domain]['queries'].add(result.query)

    profile = []
    for d in domain_data.values():
        profile.append({
            'domain': d['domain'],
            'count': len(d['queries']),
            'urls': sorted(d['urls']),
            'queries': sorted(d['queries']),
        })

    profile.sort(key=lambda x: x['count'], reverse=True)
    return profile


def generate_claude_prompt(url, title, recommendations):
    """Generate a prompt for Claude Extension to implement changes."""
    prompt_parts = [
        "I need you to help me improve this page for AI search engines (AEO optimization).",
        "",
        f"Page: {title}",
        f"URL: {url}",
        "",
        "## Changes to Make",
        ""
    ]

    if recommendations.get('action_plan'):
        for i, item in enumerate(recommendations['action_plan'], 1):
            prompt_parts.append(f"### Change {i}: {item.get('action', 'Update content')}")
            prompt_parts.append(f"**Reason:** {item.get('reason', 'Improve AEO')}")
            prompt_parts.append("")
            prompt_parts.append("**Find this text:**")
            prompt_parts.append("```")
            prompt_parts.append(item.get('current_text', '[text to find]'))
            prompt_parts.append("```")
            prompt_parts.append("")
            prompt_parts.append("**Replace with:**")
            prompt_parts.append("```")
            prompt_parts.append(item.get('suggested_text', '[replacement text]'))
            prompt_parts.append("```")
            prompt_parts.append("")

    if recommendations.get('quick_wins'):
        prompt_parts.append("## Additional Quick Improvements")
        for win in recommendations['quick_wins']:
            prompt_parts.append(f"- {win}")
        prompt_parts.append("")

    prompt_parts.append("Please make these changes to the page content. Show me the updated sections when done.")

    return "\n".join(prompt_parts)


def sanitize_for_pdf(text):
    """Remove or replace characters that fpdf can't handle."""
    if not text:
        return ""
    # Replace common problematic characters
    replacements = {
        'ø': 'o', 'Ø': 'O',
        'å': 'a', 'Å': 'A',
        'æ': 'ae', 'Æ': 'AE',
        'ö': 'o', 'Ö': 'O',
        'ä': 'a', 'Ä': 'A',
        'ü': 'u', 'Ü': 'U',
        'ß': 'ss',
        '\u201c': '"', '\u201d': '"',
        '\u2018': "'", '\u2019': "'",
        '\u2013': '-', '\u2014': '-',
        '\u2026': '...',
        '\u2022': '*',
        '\u2192': '->',
        '\u2713': '[Y]', '\u2714': '[Y]',
        '\u2717': '[N]', '\u2718': '[N]',
        '\u2705': '[Y]', '\u274c': '[N]',
        '\u26a0': '[!]',
        '\U0001f4e1': '[INTEL]',
        '\U0001f6a8': '[!]',
        '\U0001f4cb': '[PLAN]',
        '\u26a1': '[QUICK]',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Remove any remaining non-Latin-1 characters
    return text.encode('latin-1', errors='replace').decode('latin-1')


def break_long_words(text, max_chars=80):
    """Insert zero-width spaces or hyphens into very long unbreakable words (like URLs)."""
    if not text:
        return ""
    words = text.split(' ')
    result = []
    for word in words:
        if len(word) > max_chars:
            # Break long words (typically URLs) with spaces every max_chars
            chunks = [word[i:i+max_chars] for i in range(0, len(word), max_chars)]
            result.append(' '.join(chunks))
        else:
            result.append(word)
    return ' '.join(result)


def safe_multi_cell(pdf, w, h, text):
    """Write text via multi_cell with long-word breaking to prevent fpdf overflow."""
    pdf.multi_cell(w, h, break_long_words(sanitize_for_pdf(text)))


def generate_pdf_report(url, title, recommendations, citation_results=None):
    """Generate a PDF report of the AEO audit."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font('Helvetica', 'B', 20)
    pdf.cell(0, 10, 'AEO Audit Report', ln=True, align='C')
    pdf.ln(5)

    # Meta info
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', ln=True)
    pdf.cell(0, 6, f'URL: {sanitize_for_pdf(url)}', ln=True)
    pdf.cell(0, 6, f'Page Title: {sanitize_for_pdf(title)}', ln=True)
    pdf.ln(10)

    # Reset text color
    pdf.set_text_color(0, 0, 0)

    # Citation Results (if available)
    if citation_results:
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Citation Check Results', ln=True)
        pdf.set_font('Helvetica', '', 11)
        cited = sum(1 for r in citation_results if r.get('cited'))
        total = len(citation_results)
        pdf.cell(0, 6, f'Citation Rate: {cited}/{total} queries ({int(cited/total*100) if total > 0 else 0}%)', ln=True)
        pdf.ln(5)

        # Top Competing Domains
        # Build competitor profile from citation_results dicts
        domain_counts = {}
        for r in citation_results:
            for source_url in r.get('sources_found', []):
                try:
                    domain = urlparse(source_url).netloc.lower().replace('www.', '')
                except Exception:
                    continue
                if domain:
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
        if domain_counts:
            top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 8, 'Top Competing Domains', ln=True)
            pdf.set_font('Helvetica', '', 10)
            for domain, count in top_domains:
                domain_display = domain[:60] if len(domain) > 60 else domain
                safe_multi_cell(pdf, 0, 5, f'- {domain_display} (cited {count} time{"s" if count != 1 else ""})')
            pdf.ln(5)

    # Summary
    if recommendations.get('summary'):
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Summary', ln=True)
        pdf.set_font('Helvetica', '', 11)
        safe_multi_cell(pdf, 0, 6, recommendations['summary'])
        pdf.ln(5)

    # Intelligence Analysis
    intel_items = recommendations.get('intelligence_applied', [])
    if intel_items:
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Intelligence Analysis', ln=True)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, 'Based on 30 weeks of curated AI search industry data', ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

        for item in intel_items:
            verdict = item.get('verdict', 'UNKNOWN')
            item_type = item.get('type', '').replace('_', ' ').upper()
            item_name = sanitize_for_pdf(item.get('item', ''))
            impact = sanitize_for_pdf(item.get('impact', ''))

            if verdict == 'APPLIES':
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(200, 50, 50)
                safe_multi_cell(pdf, 0, 5, f'APPLIES [{item_type}]: {item_name}')
            elif verdict == 'RESPECTED':
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(50, 150, 50)
                safe_multi_cell(pdf, 0, 5, f'RESPECTED [COUNTER-SIGNAL]: {item_name}')
            else:
                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(150, 150, 150)
                safe_multi_cell(pdf, 0, 5, f'N/A [{item_type}]: {item_name}')

            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Helvetica', '', 9)
            safe_multi_cell(pdf, 0, 4, f'  {impact}')
            pdf.ln(2)

        pdf.ln(3)

    # Critical Issues
    if recommendations.get('critical_issues'):
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Critical Issues', ln=True)
        pdf.set_font('Helvetica', '', 11)
        for issue in recommendations['critical_issues']:
            safe_multi_cell(pdf, 0, 6, f'* {issue}')
        pdf.ln(5)

    # Action Plan
    if recommendations.get('action_plan'):
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Action Plan', ln=True)

        for item in recommendations['action_plan']:
            pdf.set_font('Helvetica', 'B', 12)
            safe_multi_cell(pdf, 0, 6, f"Priority {item.get('priority', '?')}: {item.get('action', '')}")

            if item.get('intelligence_source'):
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(100, 100, 100)
                safe_multi_cell(pdf, 0, 4, f"Intelligence source: {item['intelligence_source']}")
                pdf.set_text_color(0, 0, 0)

            pdf.set_font('Helvetica', 'I', 10)
            safe_multi_cell(pdf, 0, 5, f"Why: {item.get('reason', '')}")

            if item.get('current_text'):
                pdf.set_font('Helvetica', 'B', 10)
                pdf.cell(0, 6, 'Current:', ln=True)
                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(150, 50, 50)
                safe_multi_cell(pdf, 0, 5, item.get('current_text', ''))
                pdf.set_text_color(0, 0, 0)

            if item.get('suggested_text'):
                pdf.set_font('Helvetica', 'B', 10)
                pdf.cell(0, 6, 'Suggested:', ln=True)
                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(50, 150, 50)
                safe_multi_cell(pdf, 0, 5, item.get('suggested_text', ''))
                pdf.set_text_color(0, 0, 0)

            pdf.ln(5)

    # Quick Wins
    if recommendations.get('quick_wins'):
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Quick Wins', ln=True)
        pdf.set_font('Helvetica', '', 11)
        for win in recommendations['quick_wins']:
            safe_multi_cell(pdf, 0, 6, f'* {win}')

    return pdf.output()


def display_score_gauge(score: int) -> None:
    """Display a visual score indicator with amber styling."""
    if score >= 70:
        status = "Good"
    elif score >= 40:
        status = "Needs Work"
    else:
        status = "Poor"

    # Always use amber for the score, status color varies
    status_color = "#2E8B8B" if score >= 70 else "#F5A623" if score >= 40 else "#E74C3C"

    st.markdown(f"""
    <div style="text-align: center; padding: 20px;">
        <div style="font-size: 56px; font-weight: 700; color: #F5A623;">{score}/100</div>
        <div style="font-size: 18px; font-weight: 600; color: {status_color};">{status}</div>
    </div>
    """, unsafe_allow_html=True)


def display_results(result: AnalysisResult) -> None:
    """Display analysis results in a visual format."""
    if not result.extraction_success:
        st.error(f"Failed to analyze URL: {result.error_message}")
        return

    # Title section
    st.markdown("---")
    st.subheader("Page Information")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Page Title", result.title[:50] + "..." if len(result.title) > 50 else result.title or "No title found")
    with col2:
        st.metric("Total Word Count", f"{result.total_word_count:,}")

    # First paragraph preview
    st.markdown("---")
    st.subheader("First Paragraph")

    if result.first_paragraph:
        st.info(result.first_paragraph)
    else:
        st.warning("No substantial first paragraph found.")

    # Content preview
    st.markdown("---")
    st.subheader("Content Preview (First 500 Words)")

    with st.expander("Show content preview", expanded=False):
        st.text(result.first_500_words)


def display_citation_results(results: list[CitationResult], summary: dict) -> None:
    """Display citation check results."""
    # Summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Queries Checked", summary["total_queries"])
    with col2:
        cited_color = "green" if summary["cited_count"] > 0 else "red"
        st.metric("Times Cited", summary["cited_count"])
    with col3:
        rate = summary["citation_rate"]
        st.metric("Citation Rate", f"{rate:.0f}%")

    # Individual query results
    st.markdown("**Query Results:**")

    for result in results:
        if result.error:
            st.error(f"**{result.query}**\n\nError: {result.error}")
        elif result.cited:
            st.success(f"**{result.query}**\n\n:white_check_mark: Your page was cited!")
            if result.citation_snippet:
                with st.expander("View response snippet"):
                    st.write(result.citation_snippet)
        else:
            st.warning(f"**{result.query}**\n\n:x: Your page was not cited")
            if result.sources_found:
                with st.expander(f"View sources cited instead ({len(result.sources_found)})"):
                    for source in result.sources_found[:5]:
                        st.write(f"- {source}")

    # All sources found
    if summary["all_sources"]:
        with st.expander(f"All unique sources found ({len(summary['all_sources'])})"):
            for source in summary["all_sources"]:
                st.write(f"- {source}")


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="AEO Audit Agent",
        page_icon="🔍",
        layout="wide"
    )

    # Custom CSS for brand styling
    st.markdown("""
<style>
    /* Import Inter font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global font */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main background */
    .stApp {
        background-color: #FFFFFF;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1A1A2E;
        padding: 24px;
    }

    [data-testid="stSidebar"] * {
        color: #FFFFFF;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
    }

    /* Sidebar input fields */
    [data-testid="stSidebar"] .stTextInput > div > div > input {
        background-color: #FFFFFF;
        color: #1A1A2E;
        border: 1px solid #CCCCCC;
        border-radius: 8px;
    }

    /* Primary button styling */
    .stButton > button {
        background-color: #F5A623;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .stButton > button:hover {
        background-color: #E09620;
        color: #FFFFFF;
        border: none;
    }

    .stButton > button:focus {
        background-color: #E09620;
        color: #FFFFFF;
        border: none;
        box-shadow: none;
    }

    /* Secondary button styling */
    .stButton > button[kind="secondary"] {
        background-color: transparent;
        color: #F5A623;
        border: 2px solid #F5A623;
    }

    .stButton > button[kind="secondary"]:hover {
        background-color: rgba(245, 166, 35, 0.1);
        color: #F5A623;
        border: 2px solid #F5A623;
    }

    /* Input fields */
    .stTextInput > div > div > input {
        background-color: #FFFFFF;
        border: 1px solid #CCCCCC;
        border-radius: 8px;
        padding: 12px;
        color: #1A1A2E;
    }

    .stTextInput > div > div > input:focus {
        border-color: #F5A623;
        box-shadow: 0 0 0 1px #F5A623;
    }

    /* Section headers */
    h1 {
        color: #1A1A2E !important;
        font-weight: 700;
        font-size: 32px;
    }

    h2, h3 {
        color: #1A1A2E !important;
        font-weight: 600;
    }

    /* Metric styling for scores */
    [data-testid="stMetricValue"] {
        color: #F5A623;
        font-size: 48px;
        font-weight: 700;
    }

    [data-testid="stMetricLabel"] {
        color: #333333;
    }

    /* Checkbox styling */
    .stCheckbox label span {
        color: #333333;
    }

    /* Success messages - teal accent */
    .stSuccess {
        background-color: rgba(46, 139, 139, 0.1);
        border-left: 4px solid #2E8B8B;
        color: #1A1A2E;
    }

    /* Warning messages - amber accent */
    .stWarning {
        background-color: rgba(245, 166, 35, 0.1);
        border-left: 4px solid #F5A623;
        color: #1A1A2E;
    }

    /* Info messages - amber accent */
    .stInfo {
        background-color: rgba(245, 166, 35, 0.1);
        border-left: 4px solid #F5A623;
        color: #1A1A2E;
    }

    /* Error messages - red accent */
    .stError {
        background-color: rgba(231, 76, 60, 0.1);
        border-left: 4px solid #E74C3C;
        color: #1A1A2E;
    }

    /* Expander styling */
    div[data-testid="stExpander"] {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
    }

    div[data-testid="stExpander"] details summary {
        color: #1A1A2E;
        font-weight: 600;
    }

    /* Cards/containers */
    .element-container {
        background-color: #FFFFFF;
    }

    /* Spinner */
    .stSpinner > div {
        border-top-color: #F5A623 !important;
    }

    /* Links */
    a {
        color: #F5A623;
    }

    a:hover {
        color: #E09620;
    }

    /* Caption/secondary text */
    .stCaption {
        color: #666666;
    }

    /* Dividers */
    hr {
        border-color: #E5E5E5;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

    # Initialize session state
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "citation_results" not in st.session_state:
        st.session_state.citation_results = None
    if "recommendations" not in st.session_state:
        st.session_state.recommendations = None
    # New session state for intent validation
    if "extracted_intents" not in st.session_state:
        st.session_state.extracted_intents = []
    if "selected_intents" not in st.session_state:
        st.session_state.selected_intents = []
    if "intent_validated" not in st.session_state:
        st.session_state.intent_validated = False
    if "regenerated_queries" not in st.session_state:
        st.session_state.regenerated_queries = []
    # Intent-based scoring (calculated after intent selection)
    if "intent_score" not in st.session_state:
        st.session_state.intent_score = None
    if "intent_score_breakdown" not in st.session_state:
        st.session_state.intent_score_breakdown = None
    # Query review (before citation check)
    if "selected_queries" not in st.session_state:
        st.session_state.selected_queries = []
    if "queries_confirmed" not in st.session_state:
        st.session_state.queries_confirmed = False

    st.title("AEO AUDIT AGENT")

    # Intelligence feed indicator
    feed_meta = get_feed_metadata()
    if feed_meta:
        st.caption(f"v0.9 | Intelligence-First AEO | Feed: {feed_meta.get('version', 'N/A')} ({feed_meta.get('last_updated', 'N/A')}) — {feed_meta.get('weeks_of_data', 0)} weeks of data")
    else:
        st.caption("v0.9 | Answer Engine Optimization")

    st.markdown("""
    Analyze web pages to see how well they're optimized for AI answer engines
    like ChatGPT, Perplexity, and Google's AI Overviews.
    """)

    # URL Input
    url = st.text_input(
        "Enter URL to analyze",
        placeholder="https://example.com/your-page",
        help="Enter the full URL of the page you want to analyze"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        analyze_button = st.button("Analyze", type="primary", use_container_width=True)

    # Get OpenAI API key if available
    openai_api_key = None
    try:
        openai_api_key = st.secrets.get("OPENAI_API_KEY", "")
        if not openai_api_key:
            openai_api_key = None
    except Exception:
        openai_api_key = None

    # Analysis
    if analyze_button:
        if not url:
            st.warning("Please enter a URL to analyze.")
        else:
            with st.spinner("Analyzing page content..."):
                result = analyze_url(url, openai_api_key=openai_api_key)
                st.session_state.analysis_result = result
                # Reset all downstream state on new analysis
                st.session_state.citation_results = None
                st.session_state.recommendations = None
                st.session_state.extracted_intents = []
                st.session_state.selected_intents = []
                st.session_state.intent_validated = False
                st.session_state.regenerated_queries = []
                st.session_state.intent_score = None
                st.session_state.intent_score_breakdown = None
                st.session_state.selected_queries = []
                st.session_state.queries_confirmed = False

                # Extract intents if we have an API key and analysis succeeded
                if result.extraction_success and openai_api_key:
                    with st.spinner("Extracting user intents..."):
                        intent_result = extract_intents(
                            title=result.title,
                            first_paragraph=result.first_paragraph,
                            first_500_words=result.first_500_words,
                            headings=result.headings or [],
                            api_key=openai_api_key
                        )
                        if intent_result.success:
                            st.session_state.extracted_intents = intent_result.intents

    # Display analysis results if available
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result
        display_results(result)

        # Intent Validation Section (only if intents were extracted)
        if result.extraction_success and st.session_state.extracted_intents:
            st.markdown("---")
            st.subheader("Validate User Intents")
            st.markdown("""
            These are the phrases we detected that your page could be optimized for.
            **Select 3-6 intents** that best match what you want your page to rank for.

            *If none of these intents match your page's purpose, this may indicate a positioning problem — your page may not clearly communicate what it's about.*
            """)

            # Display checkboxes for each intent
            selected = []
            for i, intent in enumerate(st.session_state.extracted_intents):
                # Check if this intent is currently selected
                is_selected = intent in st.session_state.selected_intents
                if st.checkbox(intent, value=is_selected, key=f"intent_{i}"):
                    selected.append(intent)

            # Update selected intents
            st.session_state.selected_intents = selected

            # Show selection count and validation
            num_selected = len(st.session_state.selected_intents)
            if num_selected < 3:
                st.warning(f"Please select at least 3 intents. Currently selected: {num_selected}")
            elif num_selected > 6:
                st.warning(f"Please select at most 6 intents. Currently selected: {num_selected}")
            else:
                st.success(f"Selected {num_selected} intents - ready to confirm!")

            # Confirm Intents button
            col1, col2 = st.columns([1, 4])
            with col1:
                confirm_button = st.button(
                    "Confirm Intents",
                    type="primary",
                    use_container_width=True,
                    disabled=num_selected < 3 or num_selected > 6
                )

            if confirm_button and 3 <= num_selected <= 6:
                # Calculate intent-based relevance score
                with st.spinner("Calculating relevance score for your selected intents..."):
                    score_result = calculate_intent_score(
                        full_content=result.full_content,
                        title=result.title,
                        first_paragraph=result.first_paragraph,
                        selected_intents=st.session_state.selected_intents,
                        api_key=openai_api_key
                    )
                    st.session_state.intent_score = score_result.get("total_score", 0)
                    st.session_state.intent_score_breakdown = score_result

                # Regenerate queries based on selected intents
                with st.spinner("Generating queries based on your selected intents..."):
                    query_result = generate_queries_from_intents(
                        title=result.title,
                        first_paragraph=result.first_paragraph,
                        selected_intents=st.session_state.selected_intents,
                        api_key=openai_api_key
                    )
                    if query_result.is_ai_generated and query_result.queries:
                        st.session_state.regenerated_queries = query_result.queries
                        st.session_state.intent_validated = True
                    else:
                        # Fallback to original queries if regeneration fails
                        st.session_state.regenerated_queries = result.generated_queries
                        st.session_state.intent_validated = True
                        if query_result.error:
                            st.warning(f"Query regeneration failed: {query_result.error}. Using original queries.")
                st.rerun()

        # Show message if no intents extracted (no API key)
        elif result.extraction_success and not st.session_state.extracted_intents and not st.session_state.intent_validated:
            st.markdown("---")
            st.subheader("Validate User Intents")
            if not openai_api_key:
                st.info(
                    "To extract and validate user intents, add your OpenAI API key to "
                    "`.streamlit/secrets.toml`:\n\n"
                    "```\nOPENAI_API_KEY = \"sk-...\"\n```"
                )
            else:
                st.info("No intents could be extracted from this page.")

            # Allow skipping intent validation
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("Skip Intent Validation", use_container_width=True):
                    st.session_state.intent_validated = True
                    st.session_state.regenerated_queries = result.generated_queries
                    st.rerun()

        # Intent Relevance Score (shown after intent validation)
        if result.extraction_success and st.session_state.intent_validated and st.session_state.intent_score is not None:
            st.markdown("---")
            breakdown = st.session_state.intent_score_breakdown or {}
            total_score = st.session_state.intent_score

            st.subheader(f"Intent Relevance Score: {total_score}/100")

            # Score breakdown
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Content Answers", f"{breakdown.get('content_presence_score', 0)}/60")
            with col2:
                st.metric("Answer Positioning", f"{breakdown.get('position_score', 0)}/20")
            with col3:
                st.metric("Supporting Structure", f"{breakdown.get('structure_score', 0)}/20")

            # Intent-by-intent breakdown (expandable)
            intent_breakdown = breakdown.get('intent_breakdown', [])
            if intent_breakdown:
                with st.expander("Intent-by-intent breakdown", expanded=False):
                    for item in intent_breakdown:
                        intent_text = item.get('intent', 'Unknown')
                        present = item.get('present', False)
                        position = item.get('position', 'missing')
                        has_structure = item.get('has_structure', False)

                        status_icon = "✅" if present else "❌"
                        position_label = {
                            'first_paragraph': '📍 First paragraph',
                            'early': '📄 Early (first 500 words)',
                            'buried': '📦 Buried (after 500 words)',
                            'missing': '❓ Not found'
                        }.get(position, position)
                        structure_icon = "✅" if has_structure else "❌"

                        st.markdown(f"**{status_icon} {intent_text}**")
                        st.caption(f"Position: {position_label} | Structure: {structure_icon}")

            if breakdown.get('error'):
                st.warning(f"Scoring note: {breakdown['error']}")

        # Citation Check Section (only after intent validation)
        if result.extraction_success and st.session_state.intent_validated:
            # Use regenerated queries if available, otherwise use original
            queries_to_use = st.session_state.regenerated_queries or result.generated_queries

            # Query Review Section (before citation check)
            if queries_to_use and not st.session_state.queries_confirmed:
                st.markdown("---")
                st.subheader("Review Generated Queries")
                st.markdown("These queries were generated from your selected intents. **Deselect any that aren't relevant** to your optimization goals.")

                # Show selected intents if any
                if st.session_state.selected_intents:
                    with st.expander("Selected intents", expanded=False):
                        for intent in st.session_state.selected_intents:
                            st.markdown(f"- {intent}")

                # Show query source
                if st.session_state.regenerated_queries and st.session_state.selected_intents:
                    st.caption("*Queries generated based on your selected intents*")
                elif result.queries_ai_generated:
                    st.caption("*AI-generated using GPT-4o-mini*")
                else:
                    st.caption("*Rule-based fallback queries*")

                # Display checkboxes for each query (all selected by default)
                selected_queries = []
                for i, query in enumerate(queries_to_use):
                    if st.checkbox(query, value=True, key=f"query_checkbox_{i}"):
                        selected_queries.append(query)

                num_queries_selected = len(selected_queries)

                # Validation message
                if num_queries_selected == 0:
                    st.warning("Select at least 1 query to check citations. If none fit, go back and adjust your intent selection.")
                else:
                    st.success(f"Selected {num_queries_selected} queries for citation check")

                # Confirm Queries button
                col1, col2 = st.columns([1, 4])
                with col1:
                    confirm_queries_btn = st.button(
                        f"Confirm {num_queries_selected} Queries",
                        type="primary",
                        disabled=num_queries_selected == 0,
                        use_container_width=True
                    )

                if confirm_queries_btn and num_queries_selected > 0:
                    st.session_state.selected_queries = selected_queries
                    st.session_state.queries_confirmed = True
                    st.rerun()

            # Citation Check Section (only after queries confirmed)
            if st.session_state.queries_confirmed and st.session_state.selected_queries:
                st.markdown("---")
                st.subheader("Citation Check")
                st.markdown(f"Testing {len(st.session_state.selected_queries)} queries with AI search engines.")

                # Show confirmed queries
                with st.expander("Confirmed queries", expanded=False):
                    for i, query in enumerate(st.session_state.selected_queries, 1):
                        st.markdown(f"{i}. {query}")

                # Check if API key is configured
                api_key_available = False
                try:
                    api_key = st.secrets.get("PERPLEXITY_API_KEY", "")
                    api_key_available = bool(api_key)
                except Exception:
                    api_key_available = False

                if not api_key_available:
                    st.info(
                        "To check citations, add your Perplexity API key to "
                        "`.streamlit/secrets.toml`:\n\n"
                        "```\nPERPLEXITY_API_KEY = \"your-api-key-here\"\n```"
                    )

                # Citation check button
                col1, col2 = st.columns([1, 4])
                with col1:
                    check_button = st.button(
                        "Check Citations",
                        type="secondary",
                        use_container_width=True,
                        disabled=not api_key_available
                    )

                if check_button and api_key_available:
                    with st.spinner("Checking citations with AI search engines..."):
                        api_key = st.secrets["PERPLEXITY_API_KEY"]
                        citation_results = check_all_queries(
                            st.session_state.selected_queries,
                            result.url,
                            api_key
                        )
                        st.session_state.citation_results = citation_results

                # Display citation results if available
                if st.session_state.citation_results:
                    st.markdown("---")
                    st.subheader("Citation Results")
                    summary = get_citation_summary(st.session_state.citation_results)
                    display_citation_results(st.session_state.citation_results, summary)

                    # Competitor Analysis Section
                    competitor_profile = build_competitor_profile(
                        st.session_state.citation_results,
                        result.url
                    )
                    if competitor_profile:
                        st.markdown("---")
                        st.subheader("Competitor Analysis")
                        st.markdown(f"**{len(competitor_profile)} domains** are being cited instead of your page.")

                        for comp in competitor_profile[:10]:
                            with st.expander(f"{comp['domain']} — cited in {comp['count']}/{summary['total_queries']} queries"):
                                st.markdown(f"**Queries where this domain was cited:** {', '.join(comp['queries'])}")
                                st.markdown("**URLs cited:**")
                                for u in comp['urls'][:10]:
                                    st.markdown(f"- {u}")

                    # Recommendations Section (only after citation check)
                    st.markdown("---")
                    st.subheader("Recommendations")
                    st.markdown("Get AI-powered suggestions to improve your page's chances of being cited.")

                    # Check if OpenAI API key is available
                    openai_key_available = False
                    try:
                        openai_key = st.secrets.get("OPENAI_API_KEY", "")
                        openai_key_available = bool(openai_key)
                    except Exception:
                        openai_key_available = False

                    if not openai_key_available:
                        st.info(
                            "To get recommendations, add your OpenAI API key to "
                            "`.streamlit/secrets.toml`:\n\n"
                            "```\nOPENAI_API_KEY = \"sk-...\"\n```"
                        )

                    col1, col2 = st.columns([1, 4])
                    with col1:
                        recommend_button = st.button(
                            "Get Recommendations",
                            type="secondary",
                            use_container_width=True,
                            disabled=not openai_key_available
                        )

                    if recommend_button and openai_key_available:
                        with st.spinner("Generating recommendations..."):
                            openai_key = st.secrets["OPENAI_API_KEY"]
                            # Convert CitationResult objects to dicts for recommender
                            citation_dicts = [
                                {'query': r.query, 'cited': r.cited, 'sources_found': r.sources_found}
                                for r in st.session_state.citation_results
                            ] if st.session_state.citation_results else []

                            rec_result = generate_recommendations(
                                title=result.title,
                                full_content=result.full_content,
                                first_paragraph=result.first_paragraph,
                                direct_answer_score=st.session_state.intent_score or 0,
                                citation_results=citation_dicts,
                                selected_intents=st.session_state.get('selected_intents', []),
                                api_key=openai_key
                            )
                            st.session_state.recommendations = rec_result

                    # Display structured recommendations
                    if st.session_state.recommendations:
                        if isinstance(st.session_state.recommendations, dict):
                            recommendations = st.session_state.recommendations

                            # Summary
                            if recommendations.get('summary'):
                                st.info(f"**Assessment:** {recommendations['summary']}")

                            # Intelligence Analysis Panel
                            intel_items = recommendations.get('intelligence_applied', [])
                            if intel_items:
                                st.subheader("📡 Intelligence Analysis")
                                feed_meta_display = get_feed_metadata()
                                weeks = feed_meta_display.get('weeks_of_data', 0)
                                st.caption(f"Based on {weeks} weeks of curated AI search industry data")

                                applies_items = [i for i in intel_items if i.get('verdict') == 'APPLIES']
                                respected_items = [i for i in intel_items if i.get('verdict') == 'RESPECTED']
                                na_items = [i for i in intel_items if i.get('verdict') == 'NOT_APPLICABLE']

                                if applies_items:
                                    for item in applies_items:
                                        item_type = item.get('type', '').replace('_', ' ').upper()
                                        st.error(f"**APPLIES** [{item_type}]: {item.get('item', '')}\n\n{item.get('impact', '')}")

                                if respected_items:
                                    for item in respected_items:
                                        st.success(f"**RESPECTED** [COUNTER-SIGNAL]: {item.get('item', '')}\n\n{item.get('impact', '')}")

                                if na_items:
                                    with st.expander(f"{len(na_items)} intelligence items not applicable to this page"):
                                        for item in na_items:
                                            item_type = item.get('type', '').replace('_', ' ').upper()
                                            st.caption(f"[{item_type}] {item.get('item', '')} — {item.get('impact', '')}")

                            # Critical Issues
                            if recommendations.get('critical_issues'):
                                st.subheader("🚨 Critical Issues")
                                for issue in recommendations['critical_issues']:
                                    st.error(issue)

                            # Action Plan
                            if recommendations.get('action_plan'):
                                st.subheader("📋 Action Plan")
                                for item in recommendations['action_plan']:
                                    with st.expander(f"Priority {item.get('priority', '?')}: {item.get('action', 'Action')}", expanded=True):
                                        if item.get('intelligence_source'):
                                            st.markdown(f"**Intelligence source:** {item['intelligence_source']}")
                                        st.markdown(f"**Why:** {item.get('reason', '')}")

                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.markdown("**Current:**")
                                            if item.get('current_text'):
                                                st.code(item['current_text'], language=None)
                                            else:
                                                st.caption("No specific text identified")

                                        with col2:
                                            st.markdown("**Suggested:**")
                                            if item.get('suggested_text'):
                                                st.code(item['suggested_text'], language=None)
                                            else:
                                                st.caption("No suggestion provided")

                            # Quick Wins
                            if recommendations.get('quick_wins'):
                                st.subheader("⚡ Quick Wins")
                                for win in recommendations['quick_wins']:
                                    st.success(f"✓ {win}")

                            # Divider before export options
                            st.divider()

                            # Export Section
                            st.subheader("📤 Export Options")

                            # Claude Extension Prompt
                            st.markdown("### Use with Claude Extension")
                            st.warning("⚠️ **For best results:** Log in to your CMS as admin and navigate to this page before running the prompt.")

                            claude_prompt = generate_claude_prompt(
                                url=st.session_state.analysis_result.url,
                                title=st.session_state.analysis_result.title,
                                recommendations=recommendations
                            )

                            st.text_area(
                                "Prompt for Claude Extension",
                                value=claude_prompt,
                                height=300,
                                help="Copy this prompt and paste it into Claude Extension while viewing your page in the CMS"
                            )

                            # Copy button (using Streamlit's built-in)
                            st.download_button(
                                label="📋 Download Prompt as Text",
                                data=claude_prompt,
                                file_name=f"aeo-prompt-{datetime.now().strftime('%Y%m%d-%H%M')}.txt",
                                mime="text/plain"
                            )

                            # PDF Report
                            st.markdown("### Download Full Report")

                            citation_dicts = None
                            if st.session_state.get('citation_results'):
                                citation_dicts = [
                                    {'query': r.query, 'cited': r.cited, 'sources_found': r.sources_found}
                                    for r in st.session_state.citation_results
                                ]

                            try:
                                pdf_bytes = generate_pdf_report(
                                    url=st.session_state.analysis_result.url,
                                    title=st.session_state.analysis_result.title,
                                    recommendations=recommendations,
                                    citation_results=citation_dicts
                                )

                                st.download_button(
                                    label="📄 Download PDF Report",
                                    data=pdf_bytes,
                                    file_name=f"aeo-audit-{datetime.now().strftime('%Y%m%d-%H%M')}.pdf",
                                    mime="application/pdf"
                                )
                            except Exception as e:
                                st.warning(f"PDF generation failed: {e}. Use 'Download Prompt as Text' instead.")

                        else:
                            # Fallback for old format (list of strings)
                            for rec in st.session_state.recommendations:
                                st.write(f"• {rec}")

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666666; font-size: 12px; padding: 16px 0;'>"
        "AEO Audit Agent v0.9 | Intelligence-First Answer Engine Optimization"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
