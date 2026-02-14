"""
Sync AEO Guide from Notion to local markdown file.

Usage: python sync_aeo_guide.py

Requires NOTION_API_KEY environment variable or .streamlit/secrets.toml entry.
Fetches the AEO Guide from Notion and writes to intelligence/aeo_guide.md.

If this fails, the agent falls back to the hardcoded AEO_GUIDE in recommender.py.
"""

import os
import sys
import json
import requests
from datetime import datetime


NOTION_PAGE_ID = "2f49fa1ce4f5805dac3edce68f48be61"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "intelligence", "aeo_guide.md")


def get_notion_key():
    """Try to get Notion API key from env or Streamlit secrets."""
    key = os.environ.get("NOTION_API_KEY")
    if key:
        return key

    # Try Streamlit secrets
    secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        with open(secrets_path, "r") as f:
            for line in f:
                if line.strip().startswith("NOTION_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def fetch_notion_blocks(page_id, api_key):
    """Fetch all blocks from a Notion page."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
    }

    blocks = []
    url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"

    while url:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        blocks.extend(data.get("results", []))
        if data.get("has_more"):
            url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100&start_cursor={data['next_cursor']}"
        else:
            url = None

    return blocks


def rich_text_to_md(rich_text_list):
    """Convert Notion rich text array to markdown string."""
    parts = []
    for rt in rich_text_list:
        text = rt.get("plain_text", "")
        annotations = rt.get("annotations", {})
        if annotations.get("bold"):
            text = f"**{text}**"
        if annotations.get("italic"):
            text = f"*{text}*"
        if annotations.get("code"):
            text = f"`{text}`"
        parts.append(text)
    return "".join(parts)


def blocks_to_markdown(blocks):
    """Convert Notion blocks to markdown."""
    lines = []

    for block in blocks:
        btype = block.get("type", "")

        if btype == "heading_1":
            text = rich_text_to_md(block["heading_1"].get("rich_text", []))
            lines.append(f"# {text}")
        elif btype == "heading_2":
            text = rich_text_to_md(block["heading_2"].get("rich_text", []))
            lines.append(f"## {text}")
        elif btype == "heading_3":
            text = rich_text_to_md(block["heading_3"].get("rich_text", []))
            lines.append(f"### {text}")
        elif btype == "paragraph":
            text = rich_text_to_md(block["paragraph"].get("rich_text", []))
            lines.append(text)
        elif btype == "bulleted_list_item":
            text = rich_text_to_md(block["bulleted_list_item"].get("rich_text", []))
            lines.append(f"- {text}")
        elif btype == "numbered_list_item":
            text = rich_text_to_md(block["numbered_list_item"].get("rich_text", []))
            lines.append(f"1. {text}")
        elif btype == "code":
            text = rich_text_to_md(block["code"].get("rich_text", []))
            lang = block["code"].get("language", "")
            lines.append(f"```{lang}")
            lines.append(text)
            lines.append("```")
        elif btype == "divider":
            lines.append("---")
        elif btype == "table":
            # Tables need child block fetching — skip for now, the manual sync handles these
            lines.append("[Table — see Notion source]")
        elif btype == "toggle":
            text = rich_text_to_md(block["toggle"].get("rich_text", []))
            lines.append(f"**{text}**")
        elif btype == "callout":
            text = rich_text_to_md(block["callout"].get("rich_text", []))
            lines.append(f"> {text}")
        elif btype == "quote":
            text = rich_text_to_md(block["quote"].get("rich_text", []))
            lines.append(f"> {text}")
        # Skip empty blocks, child pages, etc.

        lines.append("")  # blank line between blocks

    return "\n".join(lines)


def main():
    api_key = get_notion_key()
    if not api_key:
        print("ERROR: No NOTION_API_KEY found in environment or .streamlit/secrets.toml")
        print("The agent will use the existing local file or hardcoded fallback.")
        sys.exit(1)

    print(f"Fetching AEO Guide from Notion page {NOTION_PAGE_ID}...")
    try:
        blocks = fetch_notion_blocks(NOTION_PAGE_ID, api_key)
        markdown = blocks_to_markdown(blocks)

        # Add sync metadata header
        header = (
            f"# AEO OPTIMIZATION GUIDE FOR AI APIs\n"
            f"**Synced from Notion:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"**Source page:** {NOTION_PAGE_ID}\n"
            f"**To update:** Edit the Notion page, then run `python sync_aeo_guide.py`\n\n"
        )

        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(header + markdown)

        print(f"SUCCESS: Written to {OUTPUT_PATH}")
        print(f"Blocks processed: {len(blocks)}")

    except requests.exceptions.HTTPError as e:
        print(f"ERROR: Notion API returned {e.response.status_code}")
        print("The agent will use the existing local file or hardcoded fallback.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
