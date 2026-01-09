"""
AEO Audit Agent - Streamlit Application

A tool to analyze web pages for Answer Engine Optimization.
"""

import streamlit as st
from analyzer import analyze_url, AnalysisResult


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


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="AEO Audit Agent",
        page_icon="🔍",
        layout="wide"
    )

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
                display_results(result)

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; font-size: 12px;'>"
        "AEO Audit Agent v0.1 - Pre-MVP"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
