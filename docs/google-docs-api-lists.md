# Google Docs API: Lists and Formatting

Technical reference for creating properly formatted lists via Google Docs API.

## The List Enumeration Problem (#64)

### Symptom
Numbered lists render as "1. 1. 1." instead of "1. 2. 3."

### Root Cause
Each paragraph gets a separate `listId` when `insertText` and `createParagraphBullets` are in **separate** batchUpdate API calls.

### Solution
**Two requirements:**
1. All requests must be in the **SAME batchUpdate call**
2. `createParagraphBullets` must come **IMMEDIATELY after** `insertText` (before any styling requests)

```python
# WRONG - separate batches
docs_service.documents().batchUpdate(body={"requests": insert_requests}).execute()
docs_service.documents().batchUpdate(body={"requests": bullet_requests}).execute()  # Too late!

# WRONG - bullets after styling (even in same batch)
all_requests = insert_requests + style_requests + bullet_requests  # Fails!

# CORRECT - bullets immediately after inserts, same batch
all_requests = insert_requests + bullet_requests + style_requests  # Works!
docs_service.documents().batchUpdate(body={"requests": all_requests}).execute()
```

---

## Request Structure

### Basic Numbered List

```json
[
  {
    "insertText": {
      "location": { "index": 1 },
      "text": "Item 1\nItem 2\nItem 3\n"
    }
  },
  {
    "createParagraphBullets": {
      "range": {
        "startIndex": 1,
        "endIndex": 22
      },
      "bulletPreset": "NUMBERED_DECIMAL_ALPHA_ROMAN"
    }
  }
]
```

### Key Points

1. **Insert all text at once** - Single `insertText` with `\n` separating paragraphs
2. **Single range for bullets** - One `createParagraphBullets` covering ALL list items
3. **Same batch** - Both requests in the same `batchUpdate` call
4. **Start at index 1** - Google Docs has a structural element at index 0

---

## Nested Lists

Use tab characters (`\t`) at the start of lines to control nesting level:

```json
{
  "insertText": {
    "location": { "index": 1 },
    "text": "Level 0\n\tLevel 1\n\t\tLevel 2\n\tLevel 1\nLevel 0\n"
  }
}
```

For items that shouldn't be bulleted, use `deleteParagraphBullets` after applying bullets:

```json
[
  { "insertText": { "text": "Not a list\nItem 1\nItem 2\n", "location": { "index": 1 } } },
  { "createParagraphBullets": { "range": { "startIndex": 1, "endIndex": 28 }, "bulletPreset": "NUMBERED_DECIMAL_ALPHA_ROMAN" } },
  { "deleteParagraphBullets": { "range": { "startIndex": 1, "endIndex": 2 } } }
]
```

---

## BulletPreset Values

### Bullet Lists
- `BULLET_DISC_CIRCLE_SQUARE` - Standard bullets (disc → circle → square)
- `BULLET_DIAMONDX_ARROW3D_SQUARE`
- `BULLET_CHECKBOX` - Checkboxes
- `BULLET_ARROW_DIAMOND_DISC`
- `BULLET_STAR_CIRCLE_SQUARE`
- `BULLET_ARROW3D_CIRCLE_SQUARE`
- `BULLET_LEFTTRIANGLE_DIAMOND_DISC`
- `BULLET_DIAMONDX_HOLLOWDIAMOND_SQUARE`
- `BULLET_DIAMOND_CIRCLE_SQUARE`

### Numbered Lists
- `NUMBERED_DECIMAL_ALPHA_ROMAN` - 1, 2, 3 → a, b, c → i, ii, iii
- `NUMBERED_DECIMAL_ALPHA_ROMAN_PARENS` - 1), 2), 3)
- `NUMBERED_DECIMAL_NESTED` - 1, 1.1, 1.1.1
- `NUMBERED_UPPERALPHA_ALPHA_ROMAN` - A, B, C → a, b, c → i, ii, iii
- `NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL` - I, II, III → A, B, C → 1, 2, 3
- `NUMBERED_ZERODECIMAL_ALPHA_ROMAN` - 01, 02, 03

---

## Request Order

**CRITICAL:** The order within a batchUpdate matters for list enumeration.

1. `insertText` - All content first
2. `createParagraphBullets` - **MUST be immediately after inserts** (this is the fix for #64)
3. `deleteParagraphBullets` - Remove bullets from non-list items (if needed)
4. `updateParagraphStyle` - Heading styles, alignment (reversed order for index preservation)
5. `updateTextStyle` - Bold, italic, colors (reversed order for index preservation)
6. `updateTableCellStyle` - Table formatting (may need separate batch due to position issues)

If `createParagraphBullets` comes after styling requests, each paragraph gets a separate `listId` and numbered lists show "1. 1. 1." instead of "1. 2. 3."

---

## Index Calculations

- **Zero-based indexing** starting at index 1 (index 0 is structural)
- **UTF-16 code units** - Emoji and special chars may be multiple units
- **Exclusive end index** - `endIndex` doesn't include the character at that position
- **Newlines count** - Each `\n` is one character

```python
text = "Item 1\nItem 2\n"
# Indices: I=1, t=2, e=3, m=4, (space)=5, 1=6, \n=7, I=8, t=9, ...
# Range for entire text at index 1: startIndex=1, endIndex=1+len(text)=15
```

---

## Common Mistakes

### 1. Separate Batches
```python
# WRONG
batch1 = [insertText_requests]
batch2 = [createParagraphBullets_requests]
```

### 2. Bullets After Styling (even in same batch)
```python
# WRONG - styling between inserts and bullets breaks enumeration
all_requests = inserts + paragraph_styles + text_styles + bullets  # 1. 1. 1.

# CORRECT - bullets immediately after inserts
all_requests = inserts + bullets + paragraph_styles + text_styles  # 1. 2. 3.
```

### 3. Wrong Parameter Name
```python
# WRONG
"bulletGlyphPreset": "NUMBERED..."  # Not a real parameter

# CORRECT
"bulletPreset": "NUMBERED_DECIMAL_ALPHA_ROMAN"
```

### 4. Per-Paragraph Bullet Requests
```python
# WRONG - creates separate listId for each
for item in items:
    requests.append({"createParagraphBullets": {"range": item_range, ...}})

# CORRECT - single range covering all items
requests.append({"createParagraphBullets": {"range": full_list_range, ...}})
```

### 5. Starting at Index 0
```python
# WRONG
"location": {"index": 0}  # Index 0 is structural

# CORRECT
"location": {"index": 1}  # Content starts at 1
```

---

## Debugging

### Get Document Structure
```python
doc = docs_service.documents().get(documentId=doc_id).execute()

# Check lists
for list_id, list_props in doc.get('lists', {}).items():
    print(f"List {list_id}: {list_props}")

# Check paragraph bullets
for element in doc['body']['content']:
    if 'paragraph' in element:
        para = element['paragraph']
        if 'bullet' in para:
            print(f"Paragraph at {element['startIndex']}: listId={para['bullet'].get('listId')}")
```

### Verify Same ListId
All paragraphs in a properly enumerated list should have the same `listId`. If they have different IDs, the requests were in separate batches.

---

## Hyperlinks

Use `updateTextStyle` with `link.url`:

```json
{
  "updateTextStyle": {
    "range": { "startIndex": 10, "endIndex": 20 },
    "textStyle": {
      "link": { "url": "https://example.com" }
    },
    "fields": "link"
  }
}
```

---

## Inline Code / Monospace

Use `updateTextStyle` with `weightedFontFamily`:

```json
{
  "updateTextStyle": {
    "range": { "startIndex": 5, "endIndex": 15 },
    "textStyle": {
      "weightedFontFamily": { "fontFamily": "Consolas" }
    },
    "fields": "weightedFontFamily"
  }
}
```

---

## Blockquotes

Use `updateParagraphStyle` with `indentStart`:

```json
{
  "updateParagraphStyle": {
    "range": { "startIndex": 1, "endIndex": 50 },
    "paragraphStyle": {
      "indentStart": { "magnitude": 36, "unit": "PT" },
      "indentFirstLine": { "magnitude": 36, "unit": "PT" }
    },
    "fields": "indentStart,indentFirstLine"
  }
}
```

---

## References

- [Google Docs API: Work with lists](https://developers.google.com/workspace/docs/api/how-tos/lists)
- [CreateParagraphBulletsRequest](https://developers.google.com/docs/api/reference/rest/v1/documents/request#CreateParagraphBulletsRequest)
- [BulletGlyphPreset enum](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/request#bulletglyphpreset)
- [Range object](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents#range)
- [Kanshi Tanaike: Nested Lists](https://medium.com/google-cloud/techniques-for-creating-nested-lists-on-google-documents-using-google-docs-api-e6bd2c1718d8) - Key insight on same-batch requirement
