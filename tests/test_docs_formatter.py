"""
Tests for the Google Docs builder (gdocs_builder.py).
"""

import pytest
from drive_mcp.drive.gdocs_builder import Document, markdown_to_docs_requests, TextRun


class TestDocumentBuilder:
    """Tests for the Document builder API."""

    def test_empty_document(self):
        """Empty document produces only style setup."""
        doc = Document()
        requests = doc.build()
        # Should have style setup requests (updateNamedStyle)
        assert all('updateNamedStyle' in r for r in requests)

    def test_add_heading(self):
        """Add heading generates correct requests."""
        doc = Document()
        doc.add_heading("Test Heading", level=1)
        requests = doc.build()

        # Has style setup + insertText + updateParagraphStyle
        assert any('insertText' in r for r in requests)
        assert any('updateParagraphStyle' in r for r in requests)

        # Check heading style applied
        para_styles = [r for r in requests if 'updateParagraphStyle' in r]
        assert any(
            r['updateParagraphStyle']['paragraphStyle'].get('namedStyleType') == 'HEADING_1'
            for r in para_styles
        )

    def test_add_paragraph(self):
        """Add paragraph inserts text."""
        doc = Document()
        doc.add_paragraph("Hello World")
        requests = doc.build()

        text_inserts = [r for r in requests if 'insertText' in r]
        assert len(text_inserts) == 1
        assert text_inserts[0]['insertText']['text'] == 'Hello World\n'

    def test_add_table(self):
        """Add table creates table structure and styling."""
        doc = Document()
        doc.add_table([
            ["Header 1", "Header 2"],
            ["Cell 1", "Cell 2"],
        ])
        requests = doc.build()

        # Has insertTable
        assert any('insertTable' in r for r in requests)
        table_req = next(r for r in requests if 'insertTable' in r)
        assert table_req['insertTable']['rows'] == 2
        assert table_req['insertTable']['columns'] == 2

        # Has table cell styling (header bg, borders)
        assert any('updateTableCellStyle' in r for r in requests)

    def test_add_bullet_list(self):
        """Bullet list generates createParagraphBullets."""
        doc = Document()
        doc.add_bullet_list(["Item 1", "Item 2"])
        requests = doc.build()

        bullets = [r for r in requests if 'createParagraphBullets' in r]
        # Single bullet request covering entire list range
        assert len(bullets) == 1
        assert bullets[0]['createParagraphBullets']['bulletPreset'] == 'BULLET_DISC_CIRCLE_SQUARE'

    def test_add_numbered_list(self):
        """Numbered list generates createParagraphBullets with numbered preset."""
        doc = Document()
        doc.add_numbered_list(["First", "Second"])
        requests = doc.build()

        # Should have createParagraphBullets with numbered preset
        bullets = [r for r in requests if 'createParagraphBullets' in r]
        assert len(bullets) == 1
        assert bullets[0]['createParagraphBullets']['bulletPreset'] == 'NUMBERED_DECIMAL_ALPHA_ROMAN'

        # Verify text is present (without manual numbers)
        inserts = [r for r in requests if 'insertText' in r]
        text = ''.join(r['insertText']['text'] for r in inserts)
        assert 'First' in text
        assert 'Second' in text
        # No manual numbers in the text
        assert '1. First' not in text


class TestMarkdownConversion:
    """Tests for markdown_to_docs_requests function."""

    def test_simple_markdown(self):
        """Simple markdown produces expected requests."""
        requests = markdown_to_docs_requests("# Heading\n\nParagraph text")

        # Has content inserts first, then formatting
        assert any('insertText' in r for r in requests)
        assert any('updateParagraphStyle' in r for r in requests)

    def test_complex_markdown(self):
        """Complex markdown with multiple element types."""
        markdown = """# Meeting Notes

**Date:** Jan 29, 2026

## Attendees
- Alice
- Bob

| Task | Status |
|------|--------|
| Review | Done |
"""
        requests = markdown_to_docs_requests(markdown)

        # Count request types
        insert_text = sum(1 for r in requests if 'insertText' in r)
        insert_table = sum(1 for r in requests if 'insertTable' in r)
        bullets = sum(1 for r in requests if 'createParagraphBullets' in r)
        table_style = sum(1 for r in requests if 'updateTableCellStyle' in r)

        assert insert_text >= 4  # Headings, date line, list items
        assert insert_table == 1
        # Single bullet request covers the entire list range
        assert bullets == 1
        assert table_style >= 1  # Header styling + borders

    def test_empty_markdown(self):
        """Empty markdown produces no requests."""
        requests = markdown_to_docs_requests("")
        # No content, no requests
        assert len(requests) == 0

    def test_whitespace_only(self):
        """Whitespace-only markdown produces no requests."""
        requests = markdown_to_docs_requests("   \n\n   ")
        assert len(requests) == 0

    def test_inline_formatting(self):
        """Bold and italic text generates updateTextStyle."""
        requests = markdown_to_docs_requests("**bold** and *italic*")

        text_styles = [r for r in requests if 'updateTextStyle' in r]
        assert len(text_styles) >= 2

        # Check bold
        assert any(
            r['updateTextStyle']['textStyle'].get('bold') is True
            for r in text_styles
        )
        # Check italic
        assert any(
            r['updateTextStyle']['textStyle'].get('italic') is True
            for r in text_styles
        )

    def test_hyperlinks(self):
        """Markdown links generate updateTextStyle with link."""
        requests = markdown_to_docs_requests("Check [Google](https://google.com) for info")

        text_styles = [r for r in requests if 'updateTextStyle' in r]
        link_styles = [r for r in text_styles if 'link' in r['updateTextStyle']['textStyle']]
        assert len(link_styles) == 1
        assert link_styles[0]['updateTextStyle']['textStyle']['link']['url'] == 'https://google.com'

    def test_inline_code(self):
        """Inline code generates updateTextStyle with monospace font."""
        requests = markdown_to_docs_requests("Run `npm install` to setup")

        text_styles = [r for r in requests if 'updateTextStyle' in r]
        font_styles = [r for r in text_styles if 'weightedFontFamily' in r['updateTextStyle']['textStyle']]
        assert len(font_styles) == 1
        assert font_styles[0]['updateTextStyle']['textStyle']['weightedFontFamily']['fontFamily'] == 'Consolas'

    def test_nested_lists(self):
        """Nested lists include tab characters for indentation levels."""
        markdown = """- Level 0
  - Level 1
    - Level 2
  - Level 1 again
- Level 0 again"""
        requests = markdown_to_docs_requests(markdown)

        # Find the insertText for the list
        inserts = [r for r in requests if 'insertText' in r]
        text = ''.join(r['insertText']['text'] for r in inserts)

        # Check tabs are present for nesting
        assert '\tLevel 1\n' in text
        assert '\t\tLevel 2\n' in text
        assert 'Level 0\n' in text  # No tabs for top level

    def test_code_blocks(self):
        """Fenced code blocks get monospace font."""
        markdown = """Here is some code:

```
def hello():
    print("world")
```

And more text."""
        requests = markdown_to_docs_requests(markdown)

        # Check for monospace font style
        text_styles = [r for r in requests if 'updateTextStyle' in r]
        font_styles = [r for r in text_styles if 'weightedFontFamily' in r['updateTextStyle']['textStyle']]
        assert len(font_styles) >= 1
        assert any(
            r['updateTextStyle']['textStyle']['weightedFontFamily']['fontFamily'] == 'Consolas'
            for r in font_styles
        )

    def test_blockquotes(self):
        """Blockquotes get indented paragraph style."""
        markdown = """> This is a quote
> from someone important"""
        requests = markdown_to_docs_requests(markdown)

        # Check for indented paragraph style
        para_styles = [r for r in requests if 'updateParagraphStyle' in r]
        indent_styles = [r for r in para_styles if 'indentStart' in r['updateParagraphStyle']['paragraphStyle']]
        assert len(indent_styles) >= 1
        assert indent_styles[0]['updateParagraphStyle']['paragraphStyle']['indentStart']['magnitude'] == 36

    def test_page_breaks(self):
        """Page break syntax generates pageBreakBefore style."""
        markdown = """Page one content

---page---

Page two content"""
        requests = markdown_to_docs_requests(markdown)

        # Check for pageBreakBefore in paragraph style
        para_styles = [r for r in requests if 'updateParagraphStyle' in r]
        page_breaks = [r for r in para_styles if 'pageBreakBefore' in r['updateParagraphStyle']['paragraphStyle']]
        assert len(page_breaks) >= 1
        assert page_breaks[0]['updateParagraphStyle']['paragraphStyle']['pageBreakBefore'] is True


class TestStyleSetup:
    """Tests for document style configuration."""

    def test_content_order(self):
        """Insert requests come before formatting requests."""
        requests = markdown_to_docs_requests("# Hello")

        # Should have at least one insert and one paragraph style request
        inserts = [i for i, r in enumerate(requests) if 'insertText' in r]
        para_styles = [i for i, r in enumerate(requests) if 'updateParagraphStyle' in r]

        assert len(inserts) > 0
        assert len(para_styles) > 0
        # Inserts should come before paragraph styles
        assert max(inserts) < min(para_styles)

    def test_document_defaults(self):
        """Document uses expected default style."""
        doc = Document()
        # Verify the style configuration exists
        assert doc.style.font_family == 'Arial'
        assert doc.style.body_size == 11.0

    def test_table_header_background(self):
        """Tables get light blue header background."""
        doc = Document()
        doc.add_table([["Header"], ["Data"]])
        requests = doc.build()

        # Find header background style
        cell_styles = [r for r in requests if 'updateTableCellStyle' in r]
        header_style = next(
            (r for r in cell_styles
             if r['updateTableCellStyle'].get('tableRange', {}).get('rowSpan') == 1),
            None
        )
        assert header_style is not None
        bg = header_style['updateTableCellStyle']['tableCellStyle']['backgroundColor']['color']['rgbColor']
        # Light blue: approximately 0.835, 0.910, 0.940
        assert 0.8 < bg['red'] < 0.9
        assert 0.9 < bg['green'] < 0.95
        assert 0.9 < bg['blue'] < 0.98
