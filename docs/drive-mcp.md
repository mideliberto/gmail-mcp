# drive-mcp Tool Reference

Google Drive file management server with 54 tools.

## Prerequisites

- Google Cloud Project with Drive API, Drive Labels API, and Drive Activity API enabled
- OAuth credentials (shared with gmail-mcp)
- Scopes: `drive`, `drive.labels`, `drive.activity.readonly`

---

## File Operations (14 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_drive_files` | List files in a folder | `folder_id`, `max_results`, `order_by` |
| `search_drive_files` | Search Drive with query | `query`, `max_results`, `file_type` |
| `get_drive_file` | Get file metadata | `file_id` |
| `read_drive_file` | Read file content | `file_id`, `mime_type` |
| `create_drive_file` | Create new file | `name`, `content`, `mime_type`, `folder_id` |
| `update_drive_file` | Update file content | `file_id`, `content`, `mime_type` |
| `rename_drive_file` | Rename file | `file_id`, `new_name` |
| `move_drive_file` | Move file to folder | `file_id`, `folder_id` |
| `copy_drive_file` | Copy file | `file_id`, `new_name`, `folder_id` |
| `trash_drive_file` | Move to trash | `file_id` |
| `restore_drive_file` | Restore from trash | `file_id` |
| `delete_drive_file` | Permanently delete | `file_id` |
| `star_drive_file` | Star file for quick access | `file_id` |
| `unstar_drive_file` | Remove star from file | `file_id` |

### Search Query Examples

```python
# By name
search_drive_files(query="name contains 'budget'")

# By type
search_drive_files(query="mimeType='application/pdf'")

# Modified recently
search_drive_files(query="modifiedTime > '2026-01-01'")

# In specific folder
search_drive_files(query="'folder_id' in parents")

# Combined
search_drive_files(query="name contains 'report' and mimeType='application/pdf'")
```

---

## Folders (3 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_drive_folder` | Create folder | `name`, `parent_folder_id` |
| `get_folder_tree` | Get folder structure | `folder_id`, `max_depth` |
| `get_folder_path` | Get full path to folder | `folder_id` |

---

## Google Workspace Files (4 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_google_doc` | Create Google Doc | `name`, `folder_id`, `content` |
| `create_google_sheet` | Create Google Sheet | `name`, `folder_id` |
| `create_google_slides` | Create Google Slides | `name`, `folder_id` |
| `export_google_file` | Export to format | `file_id`, `mime_type`, `output_path` |

### Export MIME Types

| Format | MIME Type |
|--------|-----------|
| PDF | `application/pdf` |
| Word (DOCX) | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| Excel (XLSX) | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| PowerPoint (PPTX) | `application/vnd.openxmlformats-officedocument.presentationml.presentation` |
| Plain Text | `text/plain` |
| CSV | `text/csv` |
| HTML | `text/html` |

---

## Sharing & Permissions (6 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_drive_permissions` | List file permissions | `file_id` |
| `share_drive_file` | Share file with user/group | `file_id`, `email`, `role`, `type`, `send_notification` |
| `update_drive_permission` | Update permission | `file_id`, `permission_id`, `role` |
| `remove_drive_permission` | Remove permission | `file_id`, `permission_id` |
| `transfer_drive_ownership` | Transfer ownership | `file_id`, `new_owner_email` |
| `create_drive_shortcut` | Create shortcut to file | `target_file_id`, `shortcut_name`, `folder_id` |

### Permission Roles

| Role | Description |
|------|-------------|
| `reader` | View only |
| `commenter` | View and comment |
| `writer` | View, comment, edit |
| `owner` | Full ownership (can delete, share) |

### Permission Types

| Type | Description |
|------|-------------|
| `user` | Specific user (requires email) |
| `group` | Google Group (requires email) |
| `domain` | Anyone in domain |
| `anyone` | Anyone with link |

---

## Shared Drives (6 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_shared_drives` | List accessible shared drives | `max_results` |
| `get_shared_drive` | Get shared drive details | `drive_id` |
| `list_shared_drive_members` | List drive members | `drive_id` |
| `create_shared_drive` | Create new shared drive | `name`, `request_id` |
| `delete_shared_drive` | Delete shared drive | `drive_id` |
| `update_shared_drive` | Update drive name/settings | `drive_id`, `name` |

*Note: Create/delete/update require Google Workspace admin permissions.*

---

## Bulk Operations (4 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `bulk_move_files` | Move multiple files | `file_ids`, `folder_id` |
| `bulk_trash_files` | Trash multiple files | `file_ids` |
| `bulk_delete_files` | Permanently delete multiple | `file_ids` |
| `bulk_share_files` | Share multiple files | `file_ids`, `email`, `role` |

---

## Storage & Activity (2 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_drive_quota` | Get storage quota info | None |
| `get_drive_activity` | Get activity log | `file_id` or `folder_id`, `max_results` |

### Activity Types Returned

- File created, edited, renamed, moved
- Comments added
- Permissions changed
- File shared
- File trashed/restored

---

## Comments (3 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_drive_comments` | List comments on file | `file_id`, `page_size`, `page_token`, `include_deleted` |
| `add_drive_comment` | Add comment to file | `file_id`, `content` |
| `delete_drive_comment` | Delete a comment | `file_id`, `comment_id` |

---

## Revisions (3 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_drive_revisions` | List file version history | `file_id`, `page_size`, `page_token` |
| `get_drive_revision` | Get revision metadata | `file_id`, `revision_id` |
| `download_drive_revision` | Download previous version | `file_id`, `revision_id`, `output_path` |

---

## Drive Labels (6 tools)

Drive Labels allow categorization and metadata on files (requires Drive Labels API).

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_drive_labels` | List available labels | `max_results` |
| `get_drive_label` | Get label details | `label_id` |
| `get_file_labels` | Get labels on a file | `file_id` |
| `set_file_label` | Apply label to file | `file_id`, `label_id`, `field_values` |
| `remove_file_label` | Remove label from file | `file_id`, `label_id` |
| `search_by_label` | Search files by label | `label_id`, `field_id`, `field_value`, `max_results` |

### Label Field Values

```python
# Setting label with field values
set_file_label(
    file_id="abc123",
    label_id="label_xyz",
    field_values={
        "status": "approved",
        "reviewer": "john@example.com",
        "review_date": "2026-01-22"
    }
)
```

---

## Drive OCR (3 tools)

Uses Google Drive's native OCR to extract text from images and PDFs.

| Tool | Description | Parameters |
|------|-------------|------------|
| `upload_image_with_ocr` | Upload image, convert to Doc with OCR | `image_path`, `doc_name`, `folder_id` |
| `ocr_existing_image` | OCR an image already in Drive | `file_id`, `doc_name` |
| `upload_pdf_with_ocr` | Upload PDF, convert to Doc with OCR | `pdf_path`, `doc_name`, `folder_id` |

### How Drive OCR Works

1. Upload image/PDF to Google Drive
2. Convert to Google Doc (triggers OCR)
3. Extract text from the resulting Doc
4. Optionally delete the intermediate files

**Supported formats:** PNG, JPG, GIF, PDF

**Languages:** Automatic language detection

---

## Common Patterns

### Upload and Share

```python
# 1. Create file
result = create_drive_file(
    name="report.txt",
    content="Report content here",
    mime_type="text/plain",
    folder_id="folder123"
)

# 2. Share with team
share_drive_file(
    file_id=result["file_id"],
    email="team@company.com",
    role="writer",
    type="group"
)
```

### Organize Files

```python
# Create folder structure
parent = create_drive_folder(name="Projects")
subfolder = create_drive_folder(name="Q1 2026", parent_folder_id=parent["folder_id"])

# Move files into folder
bulk_move_files(file_ids=["file1", "file2"], folder_id=subfolder["folder_id"])
```

### Export and Process

```python
# Export Google Doc as PDF
export_google_file(
    file_id="doc123",
    mime_type="application/pdf",
    output_path="/tmp/document.pdf"
)
```

### OCR Workflow

```python
# OCR a scanned document
result = upload_image_with_ocr(
    image_path="/path/to/scan.png",
    doc_name="OCR Result"
)
# result["text"] contains the extracted text
```

---

## Notes

- drive-mcp shares OAuth tokens with gmail-mcp
- No separate authentication needed if already authenticated with gmail-mcp
- File IDs are stable and can be stored for later use
- Shared Drive operations require appropriate permissions
- Drive Labels require the Drive Labels API to be enabled
