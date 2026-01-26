"""
AEO Audit Agent - Streamlit Application

A tool to analyze web pages for Answer Engine Optimization.
"""

import streamlit as st
from analyzer import analyze_url, AnalysisResult
from perplexity_checker import check_all_queries, get_citation_summary, CitationResult
from recommender import generate_recommendations
from intent_extractor import extract_intents
from query_generator import generate_queries_from_intents


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

    # Direct Answer Score
    st.markdown("---")
    st.subheader("Direct Answer Analysis")

    col1, col2 = st.columns([1, 2])

    with col1:
        display_score_gauge(result.direct_answer_score)

    with col2:
        st.markdown("**Assessment Breakdown:**")
        for reason in result.direct_answer_reasons:
            if any(word in reason.lower() for word in ["good", "contains", "doesn't start with weak", "not promotional", "definitive"]):
                st.markdown(f"- :white_check_mark: {reason}")
            else:
                st.markdown(f"- :warning: {reason}")

    # First paragraph analysis
    st.markdown("---")
    st.subheader("First Paragraph")

    if result.first_paragraph:
        if result.has_direct_answer:
            st.success("This paragraph appears to provide a direct answer!")
        else:
            st.warning("This paragraph may not be optimal for answer engines.")

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

    st.title("AEO AUDIT AGENT")
    st.caption("v0.3 | Answer Engine Optimization")

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
            """)

            # Select All / Select None buttons
            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                if st.button("Select All", use_container_width=True):
                    st.session_state.selected_intents = st.session_state.extracted_intents.copy()
                    st.rerun()
            with col2:
                if st.button("Select None", use_container_width=True):
                    st.session_state.selected_intents = []
                    st.rerun()

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

        # Citation Check Section (only after intent validation)
        if result.extraction_success and st.session_state.intent_validated:
            # Use regenerated queries if available, otherwise use original
            queries_to_use = st.session_state.regenerated_queries or result.generated_queries

            if queries_to_use:
                st.markdown("---")
                st.subheader("Citation Check")
                st.markdown("""
                Test if Perplexity AI cites your page when answering these queries.
                """)

                # Show selected intents if any
                if st.session_state.selected_intents:
                    with st.expander("Selected intents", expanded=False):
                        for intent in st.session_state.selected_intents:
                            st.markdown(f"- {intent}")

                # Display generated queries
                if st.session_state.regenerated_queries and st.session_state.selected_intents:
                    st.markdown("**Generated Queries:** *(based on your selected intents)*")
                elif result.queries_ai_generated:
                    st.markdown("**Generated Queries:** *(AI-generated using GPT-4o-mini)*")
                else:
                    st.markdown("**Generated Queries:** *(rule-based fallback)*")

                for i, query in enumerate(queries_to_use, 1):
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
                    with st.spinner("Checking citations with Perplexity AI..."):
                        api_key = st.secrets["PERPLEXITY_API_KEY"]
                        citation_results = check_all_queries(
                            queries_to_use,
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
                            rec_result = generate_recommendations(
                                title=result.title,
                                first_paragraph=result.first_paragraph,
                                first_500_words=result.first_500_words,
                                direct_answer_score=result.direct_answer_score,
                                headings=result.headings,
                                citation_results=st.session_state.citation_results,
                                api_key=openai_key
                            )
                            st.session_state.recommendations = rec_result

                    # Display recommendations if available
                    if st.session_state.recommendations:
                        rec_result = st.session_state.recommendations
                        if rec_result.success and rec_result.recommendations:
                            for i, rec in enumerate(rec_result.recommendations, 1):
                                st.info(f"**{i}.** {rec}")
                        elif rec_result.error:
                            st.error(f"Failed to generate recommendations: {rec_result.error}")

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666666; font-size: 12px; padding: 16px 0;'>"
        "AEO Audit Agent v0.3 | Built for Answer Engine Optimization"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
