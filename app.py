"""
AEO Audit Agent - Streamlit Application

A tool to analyze web pages for Answer Engine Optimization.
"""

import streamlit as st
from analyzer import analyze_url, AnalysisResult
from perplexity_checker import check_all_queries, get_citation_summary, CitationResult


def display_score_gauge(score: int) -> None:
    """Display a visual score indicator."""
    if score >= 70:
        color = "green"
        status = "Good"
    elif score >= 40:
        color = "orange"
        status = "Needs Work"
    else:
        color = "red"
        status = "Poor"

    st.markdown(f"""
    <div style="text-align: center; padding: 20px;">
        <div style="font-size: 48px; font-weight: bold; color: {color};">{score}/100</div>
        <div style="font-size: 18px; color: {color};">{status}</div>
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

    # Initialize session state
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "citation_results" not in st.session_state:
        st.session_state.citation_results = None

    st.title("AEO Audit Agent")
    st.markdown("*Analyze your content for Answer Engine Optimization*")

    st.markdown("""
    This tool analyzes web pages to see how well they're optimized for AI answer engines
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

    # Analysis
    if analyze_button:
        if not url:
            st.warning("Please enter a URL to analyze.")
        else:
            with st.spinner("Analyzing page content..."):
                result = analyze_url(url)
                st.session_state.analysis_result = result
                st.session_state.citation_results = None  # Reset citations on new analysis

    # Display analysis results if available
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result
        display_results(result)

        # Citation Check Section
        if result.extraction_success and result.generated_queries:
            st.markdown("---")
            st.subheader("Citation Check")
            st.markdown("""
            Test if Perplexity AI cites your page when answering these queries.
            These queries are generated based on your page's title and content.
            """)

            # Display generated queries
            st.markdown("**Generated Queries:**")
            for i, query in enumerate(result.generated_queries, 1):
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
                        result.generated_queries,
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

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; font-size: 12px;'>"
        "AEO Audit Agent v0.2 - MVP"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
