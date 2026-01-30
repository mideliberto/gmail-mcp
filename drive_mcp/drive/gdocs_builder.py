"""
Google Docs Builder - Professional Document Creation

A Python module for creating professional Google Docs via the API.
Based on the patterns from the docx skill that produce good-looking documents.

Philosophy: Documents should look professional by default. No configuration
required for basic use, but everything is customizable when needed.

Usage:
    from gdocs_builder import Document, Paragraph, Table, TextRun

    doc = Document()
    doc.add_heading("Infrastructure Assessment", level=1)
    doc.add_paragraph("This document summarizes findings.")
    doc.add_table([
        ["Severity", "Count", "Description"],
        ["CRITICAL", "3", "Unpatched servers"],
        ["HIGH", "5", "Authentication gaps"],
    ])
    doc.add_heading("Recommendations", level=2)
    doc.add_bullet_list([
        "Patch all critical servers",
        "Rotate compromised credentials",
        "Deploy MFA organization-wide",
    ])

    requests = doc.build()
    # Execute with: docs_service.documents().batchUpdate(documentId=id, body={'requests': requests})
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
import re


# =============================================================================
# STYLE CONFIGURATION
# =============================================================================

class FontFamily(str, Enum):
    """Standard fonts guaranteed to work in Google Docs."""
    ARIAL = "Arial"
    CALIBRI = "Calibri"
    TIMES = "Times New Roman"
    GEORGIA = "Georgia"
    VERDANA = "Verdana"
    ROBOTO = "Roboto"
    OPEN_SANS = "Open Sans"


class Color:
    """Color definitions. All values are RGB 0.0-1.0."""

    # Severity levels (text colors)
    CRITICAL = {'red': 0.8, 'green': 0.0, 'blue': 0.0}
    HIGH = {'red': 1.0, 'green': 0.55, 'blue': 0.0}
    MEDIUM = {'red': 0.85, 'green': 0.65, 'blue': 0.0}
    LOW = {'red': 0.0, 'green': 0.5, 'blue': 0.0}

    # Status colors
    COMPLETE = {'red': 0.0, 'green': 0.5, 'blue': 0.0}
    IN_PROGRESS = {'red': 0.0, 'green': 0.4, 'blue': 0.8}
    BLOCKED = {'red': 0.8, 'green': 0.0, 'blue': 0.0}
    PENDING = {'red': 1.0, 'green': 0.55, 'blue': 0.0}

    # Table colors
    HEADER_BG = {'red': 0.835, 'green': 0.910, 'blue': 0.940}  # Light blue
    BORDER = {'red': 0.8, 'green': 0.8, 'blue': 0.8}           # Light gray
    ALT_ROW = {'red': 0.97, 'green': 0.97, 'blue': 0.97}       # Very light gray

    # Basic colors
    BLACK = {'red': 0.0, 'green': 0.0, 'blue': 0.0}
    WHITE = {'red': 1.0, 'green': 1.0, 'blue': 1.0}
    RED = {'red': 0.8, 'green': 0.0, 'blue': 0.0}
    GREEN = {'red': 0.0, 'green': 0.5, 'blue': 0.0}
    BLUE = {'red': 0.0, 'green': 0.0, 'blue': 0.7}

    @staticmethod
    def from_hex(hex_color: str) -> Dict[str, float]:
        """Convert hex color (#RRGGBB) to RGB dict."""
        hex_color = hex_color.lstrip('#')
        return {
            'red': int(hex_color[0:2], 16) / 255.0,
            'green': int(hex_color[2:4], 16) / 255.0,
            'blue': int(hex_color[4:6], 16) / 255.0,
        }


@dataclass
class DocumentStyle:
    """Document-wide style settings."""

    # Font
    font_family: str = FontFamily.ARIAL.value

    # Font sizes (points) - MUST have visible hierarchy
    body_size: float = 11.0
    title_size: float = 26.0     # Document title - big and bold
    heading1_size: float = 20.0  # Major sections
    heading2_size: float = 16.0  # Subsections
    heading3_size: float = 13.0  # Minor sections
    heading4_size: float = 11.0  # Same as body, just bold

    # Spacing (points) - breathing room matters
    line_spacing: int = 115  # Percentage (115 = 1.15)
    paragraph_spacing_after: float = 8.0
    title_spacing_after: float = 24.0      # Big gap after title
    heading1_spacing_before: float = 28.0  # Major break before H1
    heading1_spacing_after: float = 12.0
    heading2_spacing_before: float = 24.0  # Visible break before H2
    heading2_spacing_after: float = 8.0
    heading3_spacing_before: float = 18.0
    heading3_spacing_after: float = 6.0

    # Table defaults
    table_header_bg: Dict[str, float] = field(default_factory=lambda: Color.HEADER_BG)
    table_header_bold: bool = True
    table_border_color: Dict[str, float] = field(default_factory=lambda: Color.BORDER)
    table_border_width: float = 0.5  # Points
    table_cell_padding: float = 6.0  # Points - more padding


# Default style - looks professional out of the box
DEFAULT_STYLE = DocumentStyle()


# =============================================================================
# CONTENT ELEMENTS
# =============================================================================

@dataclass
class TextRun:
    """A run of text with optional formatting."""
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: Optional[Dict[str, float]] = None
    background: Optional[Dict[str, float]] = None
    font_size: Optional[float] = None  # Override document default
    font_family: Optional[str] = None  # Override document font (e.g., Consolas for code)
    link: Optional[str] = None  # URL for hyperlink

    @classmethod
    def bold_text(cls, text: str) -> 'TextRun':
        return cls(text=text, bold=True)

    @classmethod
    def severity(cls, level: str) -> 'TextRun':
        """Create severity-colored text."""
        colors = {
            'critical': Color.CRITICAL,
            'high': Color.HIGH,
            'medium': Color.MEDIUM,
            'low': Color.LOW,
        }
        return cls(text=level.upper(), bold=True, color=colors.get(level.lower()))

    @classmethod
    def status(cls, status: str) -> 'TextRun':
        """Create status-colored text."""
        colors = {
            'complete': Color.COMPLETE,
            'in_progress': Color.IN_PROGRESS,
            'in progress': Color.IN_PROGRESS,
            'blocked': Color.BLOCKED,
            'pending': Color.PENDING,
        }
        display = status.upper().replace('_', ' ')
        return cls(text=display, bold=True, color=colors.get(status.lower()))


@dataclass
class Paragraph:
    """A paragraph element."""
    content: Union[str, List[TextRun]]
    heading_level: int = 0  # 0 = normal, 1-6 = headings
    alignment: str = 'START'  # START, CENTER, END, JUSTIFIED
    is_title: bool = False  # Use TITLE style (bigger than H1)
    is_blockquote: bool = False  # Indented blockquote style

    def __post_init__(self):
        # Convert string to TextRun list
        if isinstance(self.content, str):
            self.content = [TextRun(text=self.content)]


@dataclass
class TableCell:
    """A table cell."""
    content: Union[str, List[TextRun]]
    background: Optional[Dict[str, float]] = None

    def __post_init__(self):
        if isinstance(self.content, str):
            self.content = [TextRun(text=self.content)]


@dataclass
class Table:
    """A table element."""
    rows: List[List[Union[str, TableCell, List[TextRun]]]]
    header_row: bool = True  # First row gets header styling
    column_widths: Optional[List[float]] = None  # Percentages, must sum to 100
    column_alignments: Optional[List[str]] = None  # 'LEFT', 'CENTER', 'RIGHT' per column

    def __post_init__(self):
        # Normalize all cells
        normalized = []
        for row in self.rows:
            norm_row = []
            for cell in row:
                if isinstance(cell, str):
                    norm_row.append(TableCell(content=cell))
                elif isinstance(cell, list):
                    norm_row.append(TableCell(content=cell))
                elif isinstance(cell, TableCell):
                    norm_row.append(cell)
                else:
                    norm_row.append(TableCell(content=str(cell)))
            normalized.append(norm_row)
        self.rows = normalized


@dataclass
class CodeBlock:
    """A code block element - renders as multiple paragraphs with no spacing."""
    lines: List[str]
    language: Optional[str] = None  # Optional language hint (not used for styling yet)


# =============================================================================
# DOCUMENT BUILDER
# =============================================================================

class Document:
    """
    Google Docs document builder.

    Creates a list of API requests that produce a professional-looking document.
    """

    def __init__(self, style: Optional[DocumentStyle] = None):
        self.style = style or DEFAULT_STYLE
        self.elements: List[Any] = []
        self.header_text: Optional[str] = None
        self.footer_text: Optional[str] = None
        self.include_page_numbers: bool = False
        self.page_number_position: str = 'footer'  # 'header' or 'footer'

    # -------------------------------------------------------------------------
    # Content Addition Methods
    # -------------------------------------------------------------------------

    def add_title(self, text: str) -> 'Document':
        """Add a document title (larger than H1)."""
        self.elements.append(Paragraph(content=text, is_title=True))
        return self

    def add_heading(self, text: str, level: int = 1) -> 'Document':
        """Add a heading (level 1-6)."""
        self.elements.append(Paragraph(content=text, heading_level=level))
        return self

    def add_paragraph(self, text: Union[str, List[TextRun]],
                      alignment: str = 'START') -> 'Document':
        """Add a paragraph."""
        self.elements.append(Paragraph(content=text, alignment=alignment))
        return self

    def add_text(self, *runs: TextRun) -> 'Document':
        """Add a paragraph with formatted text runs."""
        self.elements.append(Paragraph(content=list(runs)))
        return self

    def add_bullet_list(self, items: List[Union[str, List[TextRun]]]) -> 'Document':
        """Add a bullet list."""
        for item in items:
            self.elements.append(('bullet', Paragraph(content=item), 0))
        return self

    def add_numbered_list(self, items: List[Union[str, List[TextRun]]]) -> 'Document':
        """Add a numbered list."""
        for item in items:
            self.elements.append(('numbered', Paragraph(content=item), 0))
        return self

    def add_table(self, rows: List[List[Any]],
                  header_row: bool = True,
                  column_widths: Optional[List[float]] = None,
                  column_alignments: Optional[List[str]] = None) -> 'Document':
        """
        Add a table.

        Args:
            rows: List of rows, each row is a list of cell contents.
                  Cell contents can be strings, TextRuns, or TableCells.
            header_row: If True, first row gets header styling.
            column_widths: Optional list of column width percentages.
            column_alignments: Optional list of alignments ('LEFT', 'CENTER', 'RIGHT').
        """
        self.elements.append(Table(rows=rows, header_row=header_row,
                                   column_widths=column_widths,
                                   column_alignments=column_alignments))
        return self

    def add_code_block(self, code: str) -> 'Document':
        """Add a code block with monospace font and light gray background."""
        CODE_BG = {'red': 0.95, 'green': 0.95, 'blue': 0.95}
        self.elements.append(Paragraph(
            content=[TextRun(text=code, font_family='Consolas', background=CODE_BG)]
        ))
        return self

    def add_blockquote(self, text: Union[str, List[TextRun]]) -> 'Document':
        """Add an indented blockquote."""
        self.elements.append(Paragraph(content=text, is_blockquote=True))
        return self

    def add_horizontal_rule(self) -> 'Document':
        """Add a horizontal rule (rendered as spacing)."""
        self.elements.append('hr')
        return self

    def add_page_break(self) -> 'Document':
        """Add a page break."""
        self.elements.append('pagebreak')
        return self

    def set_header(self, text: str) -> 'Document':
        """Set document header text (appears on every page)."""
        self.header_text = text
        return self

    def set_footer(self, text: str) -> 'Document':
        """Set document footer text (appears on every page)."""
        self.footer_text = text
        return self

    def add_page_numbers(self, position: str = 'footer') -> 'Document':
        """
        Add page numbers to the document.

        Args:
            position: 'header' or 'footer' (default: 'footer')
        """
        self.include_page_numbers = True
        self.page_number_position = position
        return self

    # -------------------------------------------------------------------------
    # Markdown Parsing
    # -------------------------------------------------------------------------

    def add_markdown(self, markdown: str) -> 'Document':
        """Parse and add markdown content."""
        lines = markdown.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Fenced code block (triple backticks)
            if line.strip().startswith('```'):
                # Extract optional language hint
                lang_match = re.match(r'^```(\w+)?', line.strip())
                language = lang_match.group(1) if lang_match else None
                i += 1
                code_lines = []
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                if i < len(lines):  # Skip closing ```
                    i += 1
                if code_lines:
                    self.elements.append(CodeBlock(lines=code_lines, language=language))
                continue

            # Page break (---page---, <!-- pagebreak -->, or \pagebreak)
            if re.match(r'^(---page---|<!--\s*pagebreak\s*-->|\\pagebreak)\s*$', line, re.IGNORECASE):
                self.add_page_break()
                i += 1
                continue

            # Horizontal rule (---, ***, or ___)
            if re.match(r'^(---+|\*\*\*+|___+)\s*$', line):
                self.add_horizontal_rule()
                i += 1
                continue

            # Table
            if re.match(r'^\|.+\|$', line):
                table_rows = []
                column_alignments = None
                while i < len(lines) and re.match(r'^\|.+\|$', lines[i]):
                    # Check if this is a separator row with alignment info
                    if re.match(r'^\|[\s\-:|]+\|$', lines[i]):
                        # Parse alignment from separator (|:--|:--:|--:|)
                        sep_cells = [c.strip() for c in lines[i].strip('|').split('|')]
                        column_alignments = []
                        for sep in sep_cells:
                            sep = sep.strip()
                            if sep.startswith(':') and sep.endswith(':'):
                                column_alignments.append('CENTER')
                            elif sep.endswith(':'):
                                column_alignments.append('RIGHT')
                            else:
                                column_alignments.append('LEFT')
                    else:
                        cells = [c.strip() for c in lines[i].strip('|').split('|')]
                        # Parse inline formatting in cells
                        parsed_cells = [self._parse_inline(c) for c in cells]
                        table_rows.append(parsed_cells)
                    i += 1
                if table_rows:
                    self.add_table(table_rows, column_alignments=column_alignments)
                continue

            # Heading
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if match:
                level = len(match.group(1))
                text = self._parse_inline(match.group(2))
                self.elements.append(Paragraph(content=text, heading_level=level))
                i += 1
                continue

            # Bullet list (capture leading whitespace for nesting)
            match = re.match(r'^(\s*)[-*]\s+(.+)$', line)
            if match:
                indent = match.group(1)
                nesting = len(indent) // 2  # 2 spaces = 1 nesting level
                content = self._parse_inline(match.group(2))
                self.elements.append(('bullet', Paragraph(content=content), nesting))
                i += 1
                continue

            # Numbered list (capture leading whitespace for nesting)
            match = re.match(r'^(\s*)\d+\.\s+(.+)$', line)
            if match:
                indent = match.group(1)
                nesting = len(indent) // 2
                content = self._parse_inline(match.group(2))
                self.elements.append(('numbered', Paragraph(content=content), nesting))
                i += 1
                continue

            # Blockquote (> prefix, supports nesting with >>)
            match = re.match(r'^(>+)\s*(.*)$', line)
            if match:
                # Strip leading > from nested quotes
                quote_text = match.group(2)
                content = self._parse_inline(quote_text) if quote_text else [TextRun(text='')]
                self.elements.append(Paragraph(content=content, is_blockquote=True))
                i += 1
                continue

            # Regular paragraph
            content = self._parse_inline(line)
            self.elements.append(Paragraph(content=content))
            i += 1

        return self

    def _parse_inline(self, text: str) -> List[TextRun]:
        """Parse inline markdown formatting (links, bold, italic, inline code)."""
        runs: List[TextRun] = []

        # Light gray background for inline code
        CODE_BG = {'red': 0.93, 'green': 0.93, 'blue': 0.93}

        # Pattern for links, bold, italic, bold-italic, inline code
        # Supports both * and _ for bold/italic
        pattern = re.compile(
            r'(\[([^\]]+)\]\(([^)]+)\))|'      # [text](url)
            r'(`([^`]+)`)|'                    # `inline code`
            r'(\*\*\*(.+?)\*\*\*)|'            # ***bold italic***
            r'(___(.+?)___)|'                  # ___bold italic___
            r'(\*\*(.+?)\*\*)|'                # **bold**
            r'(__(.+?)__)|'                    # __bold__
            r'(\*(.+?)\*)|'                    # *italic*
            r'(\b_([^_]+)_\b)'                 # _italic_ (word boundaries to avoid mid_word_matches)
        )

        last_end = 0
        for match in pattern.finditer(text):
            if match.start() > last_end:
                plain = text[last_end:match.start()]
                if plain:
                    runs.append(TextRun(text=plain))

            if match.group(2):  # Link: [text](url)
                runs.append(TextRun(text=match.group(2), link=match.group(3)))
            elif match.group(5):  # Inline code: `code`
                runs.append(TextRun(text=match.group(5), font_family='Consolas', background=CODE_BG))
            elif match.group(7):  # ***bold italic***
                runs.append(TextRun(text=match.group(7), bold=True, italic=True))
            elif match.group(9):  # ___bold italic___
                runs.append(TextRun(text=match.group(9), bold=True, italic=True))
            elif match.group(11):  # **bold**
                runs.append(TextRun(text=match.group(11), bold=True))
            elif match.group(13):  # __bold__
                runs.append(TextRun(text=match.group(13), bold=True))
            elif match.group(15):  # *italic*
                runs.append(TextRun(text=match.group(15), italic=True))
            elif match.group(17):  # _italic_
                runs.append(TextRun(text=match.group(17), italic=True))

            last_end = match.end()

        if last_end < len(text):
            remaining = text[last_end:]
            if remaining:
                runs.append(TextRun(text=remaining))

        return runs if runs else [TextRun(text=text)]

    # -------------------------------------------------------------------------
    # Build API Requests
    # -------------------------------------------------------------------------

    def build(self) -> List[Dict[str, Any]]:
        """
        Build the list of Google Docs API requests.

        Returns requests in the correct order for batchUpdate.
        """
        # Content lists - separate by type for proper ordering
        insert_requests: List[Dict[str, Any]] = []
        paragraph_style_requests: List[Dict[str, Any]] = []
        text_style_requests: List[Dict[str, Any]] = []
        list_requests: List[Dict[str, Any]] = []
        table_requests: List[Dict[str, Any]] = []

        current_index = 1  # Google Docs starts at index 1

        # Track consecutive list items for batching
        current_list_type: Optional[str] = None
        list_start_index: Optional[int] = None
        pending_list_items: List[Tuple[Paragraph, int, int, int]] = []  # (para, start, end, nesting)

        def flush_list():
            """Flush accumulated list items and apply bullet formatting.

            CRITICAL (#64): createParagraphBullets must be added to list_requests
            immediately after insertText requests (before styling) for numbered lists
            to enumerate correctly. See docs/google-docs-api-lists.md for details.
            """
            nonlocal current_list_type, list_start_index, pending_list_items, current_index

            if not pending_list_items:
                current_list_type = None
                list_start_index = None
                return

            # Build combined text for all list items
            combined_text = ""
            item_ranges = []  # Track ranges for text formatting

            for i, (para, _, _, nesting) in enumerate(pending_list_items):
                runs = para.content if isinstance(para.content, list) else [TextRun(text=str(para.content))]
                item_text = ''.join(run.text for run in runs)

                # Prepend tabs for nesting level (per Google Docs API)
                tabs = '\t' * nesting
                item_start = list_start_index + len(combined_text) + nesting  # Start after tabs
                combined_text += tabs + item_text + '\n'
                item_end = list_start_index + len(combined_text)
                item_ranges.append((item_start, item_end, runs))

            # Insert all list text in one request
            insert_requests.append({
                'insertText': {
                    'location': {'index': list_start_index},
                    'text': combined_text,
                }
            })

            # Apply createParagraphBullets for both bullet and numbered lists
            # IMPORTANT: This request must be in the SAME batchUpdate as insertText
            # to ensure all paragraphs get the same listId (see bug #64)
            preset = ('BULLET_DISC_CIRCLE_SQUARE' if current_list_type == 'bullet'
                      else 'NUMBERED_DECIMAL_ALPHA_ROMAN')
            list_end = list_start_index + len(combined_text)
            list_requests.append({
                'createParagraphBullets': {
                    'range': {
                        'startIndex': list_start_index,
                        'endIndex': list_end,
                    },
                    'bulletPreset': preset,
                }
            })

            # Add text formatting for runs if needed
            for item_start, item_end, runs in item_ranges:
                run_start = item_start
                for run in runs:
                    run_end = run_start + len(run.text)
                    style = {}
                    fields = []

                    if run.bold:
                        style['bold'] = True
                        fields.append('bold')
                    if run.italic:
                        style['italic'] = True
                        fields.append('italic')
                    if run.underline:
                        style['underline'] = True
                        fields.append('underline')
                    if run.color:
                        style['foregroundColor'] = {'color': {'rgbColor': run.color}}
                        fields.append('foregroundColor')
                    if run.font_family:
                        style['weightedFontFamily'] = {'fontFamily': run.font_family}
                        fields.append('weightedFontFamily')
                    if run.link:
                        style['link'] = {'url': run.link}
                        fields.append('link')

                    if fields:
                        text_style_requests.append({
                            'updateTextStyle': {
                                'range': {'startIndex': run_start, 'endIndex': run_end},
                                'textStyle': style,
                                'fields': ','.join(fields),
                            }
                        })
                    run_start = run_end

            list_end = list_start_index + len(combined_text)
            current_index = list_end
            current_list_type = None
            list_start_index = None
            pending_list_items = []

        for element in self.elements:
            # Flush list if we hit a non-list element
            if not isinstance(element, tuple) and current_list_type:
                flush_list()

            if element == 'hr':
                # Insert empty paragraph with bottom border to simulate horizontal rule
                insert_requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': '\n',
                    }
                })
                paragraph_style_requests.append({
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': current_index,
                            'endIndex': current_index + 1,
                        },
                        'paragraphStyle': {
                            'borderBottom': {
                                'color': {'color': {'rgbColor': {'red': 0.7, 'green': 0.7, 'blue': 0.7}}},
                                'width': {'magnitude': 1, 'unit': 'PT'},
                                'padding': {'magnitude': 8, 'unit': 'PT'},
                                'dashStyle': 'SOLID',
                            },
                            'spaceBelow': {'magnitude': 12, 'unit': 'PT'},
                        },
                        'fields': 'borderBottom,spaceBelow',
                    }
                })
                current_index += 1

            elif element == 'pagebreak':
                insert_requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': '\n',
                    }
                })
                paragraph_style_requests.append({
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': current_index,
                            'endIndex': current_index + 1,
                        },
                        'paragraphStyle': {
                            'pageBreakBefore': True,
                        },
                        'fields': 'pageBreakBefore',
                    }
                })
                current_index += 1

            elif isinstance(element, tuple):  # List item
                list_type, para, nesting = element

                if list_type != current_list_type:
                    # Different list type - flush previous and start new
                    flush_list()
                    current_list_type = list_type
                    list_start_index = current_index

                # Queue this item for batched insertion
                runs = para.content if isinstance(para.content, list) else [TextRun(text=str(para.content))]
                item_text = ''.join(run.text for run in runs)
                # Include nesting level in pending items
                pending_list_items.append((para, current_index, current_index + len(item_text), nesting))
                # Account for tabs (nesting) and newline in index calculation
                current_index += nesting + len(item_text) + 1

            elif isinstance(element, Paragraph):
                current_index = self._build_paragraph(
                    element, insert_requests, paragraph_style_requests,
                    text_style_requests, current_index
                )

            elif isinstance(element, Table):
                current_index = self._build_table(
                    element, insert_requests, paragraph_style_requests,
                    text_style_requests, table_requests, current_index
                )

            elif isinstance(element, CodeBlock):
                current_index = self._build_codeblock(
                    element, insert_requests, paragraph_style_requests,
                    text_style_requests, current_index
                )

        # Flush any remaining list
        flush_list()

        # Combine in correct order (per Google Docs API best practices):
        # 1. Content insertions first (in order)
        # 2. List bullets IMMEDIATELY after inserts (critical for proper enumeration)
        # 3. Paragraph styling (reversed to preserve indices)
        # 4. Text styling (reversed to preserve indices)
        # 5. Table cell styling
        all_requests: List[Dict[str, Any]] = []
        all_requests.extend(insert_requests)
        all_requests.extend(list_requests)  # Must be right after inserts!
        all_requests.extend(reversed(paragraph_style_requests))
        all_requests.extend(reversed(text_style_requests))
        all_requests.extend(table_requests)

        return all_requests

    def _build_style_requests(self) -> List[Dict[str, Any]]:
        """Build document-level style configuration requests."""
        s = self.style
        requests = []

        # NORMAL_TEXT
        requests.append({
            'updateNamedStyle': {
                'namedStyle': {
                    'namedStyleType': 'NORMAL_TEXT',
                    'textStyle': {
                        'fontSize': {'magnitude': s.body_size, 'unit': 'PT'},
                        'weightedFontFamily': {'fontFamily': s.font_family},
                    },
                    'paragraphStyle': {
                        'lineSpacing': s.line_spacing,
                        'spaceBelow': {'magnitude': s.paragraph_spacing_after, 'unit': 'PT'},
                    },
                },
                'fields': 'textStyle.fontSize,textStyle.weightedFontFamily,paragraphStyle.lineSpacing,paragraphStyle.spaceBelow',
            }
        })

        # TITLE - for document titles, big and centered
        requests.append({
            'updateNamedStyle': {
                'namedStyle': {
                    'namedStyleType': 'TITLE',
                    'textStyle': {
                        'fontSize': {'magnitude': s.title_size, 'unit': 'PT'},
                        'weightedFontFamily': {'fontFamily': s.font_family},
                        'bold': True,
                    },
                    'paragraphStyle': {
                        'spaceBelow': {'magnitude': s.title_spacing_after, 'unit': 'PT'},
                    },
                },
                'fields': 'textStyle.fontSize,textStyle.weightedFontFamily,textStyle.bold,paragraphStyle.spaceBelow',
            }
        })

        # HEADING_1
        requests.append({
            'updateNamedStyle': {
                'namedStyle': {
                    'namedStyleType': 'HEADING_1',
                    'textStyle': {
                        'fontSize': {'magnitude': s.heading1_size, 'unit': 'PT'},
                        'weightedFontFamily': {'fontFamily': s.font_family},
                        'bold': True,
                    },
                    'paragraphStyle': {
                        'spaceAbove': {'magnitude': s.heading1_spacing_before, 'unit': 'PT'},
                        'spaceBelow': {'magnitude': s.heading1_spacing_after, 'unit': 'PT'},
                    },
                },
                'fields': 'textStyle.fontSize,textStyle.weightedFontFamily,textStyle.bold,paragraphStyle.spaceAbove,paragraphStyle.spaceBelow',
            }
        })

        # HEADING_2
        requests.append({
            'updateNamedStyle': {
                'namedStyle': {
                    'namedStyleType': 'HEADING_2',
                    'textStyle': {
                        'fontSize': {'magnitude': s.heading2_size, 'unit': 'PT'},
                        'weightedFontFamily': {'fontFamily': s.font_family},
                        'bold': True,
                    },
                    'paragraphStyle': {
                        'spaceAbove': {'magnitude': s.heading2_spacing_before, 'unit': 'PT'},
                        'spaceBelow': {'magnitude': s.heading2_spacing_after, 'unit': 'PT'},
                    },
                },
                'fields': 'textStyle.fontSize,textStyle.weightedFontFamily,textStyle.bold,paragraphStyle.spaceAbove,paragraphStyle.spaceBelow',
            }
        })

        # HEADING_3
        requests.append({
            'updateNamedStyle': {
                'namedStyle': {
                    'namedStyleType': 'HEADING_3',
                    'textStyle': {
                        'fontSize': {'magnitude': s.heading3_size, 'unit': 'PT'},
                        'weightedFontFamily': {'fontFamily': s.font_family},
                        'bold': True,
                    },
                    'paragraphStyle': {
                        'spaceAbove': {'magnitude': s.heading3_spacing_before, 'unit': 'PT'},
                        'spaceBelow': {'magnitude': s.heading3_spacing_after, 'unit': 'PT'},
                    },
                },
                'fields': 'textStyle.fontSize,textStyle.weightedFontFamily,textStyle.bold,paragraphStyle.spaceAbove,paragraphStyle.spaceBelow',
            }
        })

        # HEADING_4
        requests.append({
            'updateNamedStyle': {
                'namedStyle': {
                    'namedStyleType': 'HEADING_4',
                    'textStyle': {
                        'fontSize': {'magnitude': s.heading4_size, 'unit': 'PT'},
                        'weightedFontFamily': {'fontFamily': s.font_family},
                        'bold': True,
                    },
                    'paragraphStyle': {
                        'spaceAbove': {'magnitude': s.heading3_spacing_before, 'unit': 'PT'},
                        'spaceBelow': {'magnitude': s.heading3_spacing_after, 'unit': 'PT'},
                    },
                },
                'fields': 'textStyle.fontSize,textStyle.weightedFontFamily,textStyle.bold,paragraphStyle.spaceAbove,paragraphStyle.spaceBelow',
            }
        })

        return requests

    def _build_paragraph(self, para: Paragraph,
                         insert_requests: List,
                         paragraph_style_requests: List,
                         text_style_requests: List,
                         current_index: int) -> int:
        """Build requests for a paragraph. Returns new current_index."""

        # Get full text
        runs = para.content if isinstance(para.content, list) else [TextRun(text=para.content)]
        full_text = ''.join(run.text for run in runs)

        if not full_text:
            return current_index

        text_with_newline = full_text + '\n'

        # Insert text
        insert_requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': text_with_newline,
            }
        })

        start = current_index
        end = current_index + len(full_text)

        # Title style (takes precedence over heading)
        if para.is_title:
            paragraph_style_requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': start, 'endIndex': end + 1},
                    'paragraphStyle': {
                        'namedStyleType': 'TITLE',
                    },
                    'fields': 'namedStyleType',
                }
            })
        # Heading style
        elif para.heading_level > 0:
            paragraph_style_requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': start, 'endIndex': end + 1},
                    'paragraphStyle': {
                        'namedStyleType': f'HEADING_{para.heading_level}',
                    },
                    'fields': 'namedStyleType',
                }
            })

        # Alignment
        if para.alignment != 'START':
            paragraph_style_requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': start, 'endIndex': end + 1},
                    'paragraphStyle': {
                        'alignment': para.alignment,
                    },
                    'fields': 'alignment',
                }
            })

        # Blockquote (indented, with left border effect via indentation)
        if para.is_blockquote:
            paragraph_style_requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': start, 'endIndex': end + 1},
                    'paragraphStyle': {
                        'indentStart': {'magnitude': 36, 'unit': 'PT'},  # ~0.5 inch
                        'indentFirstLine': {'magnitude': 36, 'unit': 'PT'},
                    },
                    'fields': 'indentStart,indentFirstLine',
                }
            })

        # Inline formatting - goes to text_style_requests (applied after paragraph styles)
        run_start = current_index
        for run in runs:
            run_end = run_start + len(run.text)

            style = {}
            fields = []

            if run.bold:
                style['bold'] = True
                fields.append('bold')
            if run.italic:
                style['italic'] = True
                fields.append('italic')
            if run.underline:
                style['underline'] = True
                fields.append('underline')
            if run.color:
                style['foregroundColor'] = {'color': {'rgbColor': run.color}}
                fields.append('foregroundColor')
            if run.background:
                style['backgroundColor'] = {'color': {'rgbColor': run.background}}
                fields.append('backgroundColor')
            if run.font_size:
                style['fontSize'] = {'magnitude': run.font_size, 'unit': 'PT'}
                fields.append('fontSize')
            if run.font_family:
                style['weightedFontFamily'] = {'fontFamily': run.font_family}
                fields.append('weightedFontFamily')
            if run.link:
                style['link'] = {'url': run.link}
                fields.append('link')

            if fields:
                text_style_requests.append({
                    'updateTextStyle': {
                        'range': {'startIndex': run_start, 'endIndex': run_end},
                        'textStyle': style,
                        'fields': ','.join(fields),
                    }
                })

            run_start = run_end

        return current_index + len(text_with_newline)

    def _build_table(self, table: Table,
                     insert_requests: List,
                     paragraph_style_requests: List,
                     text_style_requests: List,
                     table_requests: List,
                     current_index: int) -> int:
        """Build requests for a table. Returns new current_index."""

        num_rows = len(table.rows)
        num_cols = max(len(row) for row in table.rows) if table.rows else 1
        table_start = current_index

        # Insert table structure
        insert_requests.append({
            'insertTable': {
                'rows': num_rows,
                'columns': num_cols,
                'location': {'index': current_index},
            }
        })

        # Calculate table size
        table_size = 3 + num_rows * (num_cols * 2 + 1)

        # First pass: collect all cell info (text, runs, base indices)
        cell_info = []  # List of (row_idx, col_idx, cell_text, runs, base_index)
        cell_content_length = 0

        for row_idx, row in enumerate(table.rows):
            for col_idx in range(num_cols):
                if col_idx < len(row):
                    cell = row[col_idx]
                    runs = cell.content if isinstance(cell.content, list) else [TextRun(text=str(cell.content))]
                    cell_text = ''.join(run.text for run in runs)
                else:
                    cell_text = ''
                    runs = []

                if cell_text:
                    base_index = (
                        current_index + 4 +
                        row_idx * (num_cols * 2 + 1) +
                        col_idx * 2
                    )
                    cell_info.append((row_idx, col_idx, cell_text, runs, base_index))
                    cell_content_length += len(cell_text)

        # Second pass: calculate final indices and create requests
        # After reversed inserts, format_index = base_index + sum of all prior cell lengths
        cell_inserts = []
        cell_formats = []

        for i, (row_idx, col_idx, cell_text, runs, base_index) in enumerate(cell_info):
            # Insert request uses base_index
            cell_inserts.append({
                'insertText': {
                    'location': {'index': base_index},
                    'text': cell_text,
                }
            })

            # Format index accounts for all prior cells' content
            prior_content = sum(len(info[2]) for info in cell_info[:i])
            format_index = base_index + prior_content

            # Header row bold
            if row_idx == 0 and table.header_row and self.style.table_header_bold:
                cell_formats.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': format_index,
                            'endIndex': format_index + len(cell_text),
                        },
                        'textStyle': {'bold': True},
                        'fields': 'bold',
                    }
                })

            # Column alignment (applies to all rows)
            if table.column_alignments and col_idx < len(table.column_alignments):
                alignment = table.column_alignments[col_idx]
                if alignment != 'LEFT':  # LEFT is default
                    align_map = {'CENTER': 'CENTER', 'RIGHT': 'END'}
                    cell_formats.append({
                        'updateParagraphStyle': {
                            'range': {
                                'startIndex': format_index,
                                'endIndex': format_index + len(cell_text),
                            },
                            'paragraphStyle': {'alignment': align_map.get(alignment, 'START')},
                            'fields': 'alignment',
                        }
                    })

            # Apply text run formatting
            run_start = format_index
            for run in runs:
                run_end = run_start + len(run.text)
                style = {}
                fields = []

                if run.bold and not (row_idx == 0 and table.header_row):
                    style['bold'] = True
                    fields.append('bold')
                if run.italic:
                    style['italic'] = True
                    fields.append('italic')
                if run.color:
                    style['foregroundColor'] = {'color': {'rgbColor': run.color}}
                    fields.append('foregroundColor')
                if run.background:
                    style['backgroundColor'] = {'color': {'rgbColor': run.background}}
                    fields.append('backgroundColor')
                if run.font_family:
                    style['weightedFontFamily'] = {'fontFamily': run.font_family}
                    fields.append('weightedFontFamily')
                if run.link:
                    style['link'] = {'url': run.link}
                    fields.append('link')

                if fields:
                    cell_formats.append({
                        'updateTextStyle': {
                            'range': {'startIndex': run_start, 'endIndex': run_end},
                            'textStyle': style,
                            'fields': ','.join(fields),
                        }
                    })

                run_start = run_end

        insert_requests.extend(reversed(cell_inserts))
        text_style_requests.extend(cell_formats)  # Cell text formatting goes to text_style_requests

        # Table styling
        s = self.style

        # Header row background
        if table.header_row:
            table_requests.append({
                'updateTableCellStyle': {
                    'tableRange': {
                        'tableCellLocation': {
                            'tableStartLocation': {'index': table_start},
                            'rowIndex': 0,
                            'columnIndex': 0,
                        },
                        'rowSpan': 1,
                        'columnSpan': num_cols,
                    },
                    'tableCellStyle': {
                        'backgroundColor': {'color': {'rgbColor': s.table_header_bg}},
                    },
                    'fields': 'backgroundColor',
                }
            })

        # Borders and padding for ALL cells
        border = {
            'color': {'color': {'rgbColor': s.table_border_color}},
            'width': {'magnitude': s.table_border_width, 'unit': 'PT'},
            'dashStyle': 'SOLID',
        }

        table_requests.append({
            'updateTableCellStyle': {
                'tableRange': {
                    'tableCellLocation': {
                        'tableStartLocation': {'index': table_start},
                        'rowIndex': 0,
                        'columnIndex': 0,
                    },
                    'rowSpan': num_rows,
                    'columnSpan': num_cols,
                },
                'tableCellStyle': {
                    'borderLeft': border,
                    'borderRight': border,
                    'borderTop': border,
                    'borderBottom': border,
                    'paddingTop': {'magnitude': s.table_cell_padding, 'unit': 'PT'},
                    'paddingBottom': {'magnitude': s.table_cell_padding, 'unit': 'PT'},
                    'paddingLeft': {'magnitude': s.table_cell_padding + 2, 'unit': 'PT'},
                    'paddingRight': {'magnitude': s.table_cell_padding + 2, 'unit': 'PT'},
                },
                'fields': 'borderLeft,borderRight,borderTop,borderBottom,paddingTop,paddingBottom,paddingLeft,paddingRight',
            }
        })

        # Account for table structure AND cell content
        current_index += table_size + cell_content_length

        # Newline after table
        insert_requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': '\n',
            }
        })

        return current_index + 1

    def _build_codeblock(self, codeblock: CodeBlock,
                         insert_requests: List,
                         paragraph_style_requests: List,
                         text_style_requests: List,
                         current_index: int) -> int:
        """Build requests for a code block. Returns new current_index."""

        CODE_BG = {'red': 0.95, 'green': 0.95, 'blue': 0.95}
        start_index = current_index

        # Insert all lines with newlines
        for i, line in enumerate(codeblock.lines):
            # Use line or single space for empty lines (to preserve structure)
            text = line if line else ' '
            insert_requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': text + '\n',
                }
            })

            line_start = current_index
            line_end = current_index + len(text)

            # Apply monospace font and background to each line
            text_style_requests.append({
                'updateTextStyle': {
                    'range': {'startIndex': line_start, 'endIndex': line_end},
                    'textStyle': {
                        'weightedFontFamily': {'fontFamily': 'Consolas'},
                        'backgroundColor': {'color': {'rgbColor': CODE_BG}},
                    },
                    'fields': 'weightedFontFamily,backgroundColor',
                }
            })

            # Zero spacing between code lines (except last line)
            paragraph_style_requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': line_start, 'endIndex': line_end + 1},
                    'paragraphStyle': {
                        'spaceAbove': {'magnitude': 0, 'unit': 'PT'},
                        'spaceBelow': {'magnitude': 0, 'unit': 'PT'},
                        'lineSpacing': 100,  # Single spacing
                    },
                    'fields': 'spaceAbove,spaceBelow,lineSpacing',
                }
            })

            current_index += len(text) + 1  # +1 for newline

        # Add small spacing after the code block
        if codeblock.lines:
            paragraph_style_requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': current_index - 1, 'endIndex': current_index},
                    'paragraphStyle': {
                        'spaceBelow': {'magnitude': 12, 'unit': 'PT'},
                    },
                    'fields': 'spaceBelow',
                }
            })

        return current_index


# =============================================================================
# CONVENIENCE FUNCTION (backward compatible with old formatter)
# =============================================================================

def markdown_to_docs_requests(markdown: str) -> List[Dict[str, Any]]:
    """
    Convert markdown to Google Docs API requests.

    Drop-in replacement for the old formatter.
    """
    doc = Document()
    doc.add_markdown(markdown)
    return doc.build()


# =============================================================================
# TEST
# =============================================================================

if __name__ == '__main__':
    # Test the builder API
    doc = Document()

    doc.add_heading("Infrastructure Assessment", level=1)
    doc.add_paragraph("This document summarizes the current state of the environment.")

    doc.add_heading("Risk Summary", level=2)
    doc.add_table([
        ["Severity", "Count", "Key Issues"],
        [TextRun.severity('critical'), "3", "Unpatched servers, default creds"],
        [TextRun.severity('high'), "5", "Authentication gaps"],
        [TextRun.severity('medium'), "8", "Missing documentation"],
        [TextRun.severity('low'), "2", "Minor config drift"],
    ])

    doc.add_heading("Critical Findings", level=2)
    doc.add_bullet_list([
        "SQL Server unpatched since January 2015",
        "Firewall firmware 11 years old",
        "KRBTGT password unchanged since 2006",
    ])

    doc.add_heading("Remediation Status", level=2)
    doc.add_table([
        ["Task", "Status"],
        ["CHICDB01 Patching", TextRun.status('complete')],
        ["FortiGate Deployment", TextRun.status('in_progress')],
        ["HOST05/06 Firmware", TextRun.status('blocked')],
    ])

    requests = doc.build()

    print(f"Generated {len(requests)} requests")
    print()

    # Also test markdown parsing
    md_doc = Document()
    md_doc.add_markdown("""
# Test Document

## Section One

This is a paragraph with **bold** and *italic* text.

| Column A | Column B |
|----------|----------|
| Data 1   | Data 2   |

## Section Two

- Bullet one
- Bullet two
- Bullet three

1. First item
2. Second item
""")

    md_requests = md_doc.build()
    print(f"Markdown parsing generated {len(md_requests)} requests")
