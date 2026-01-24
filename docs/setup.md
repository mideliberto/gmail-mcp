# Gmail MCP Extended Setup Guide

Complete guide to setting up the Gmail MCP Extended monorepo with all three MCP servers.

## Overview

| Server | Purpose | Google Auth Required |
|--------|---------|---------------------|
| `gmail-mcp` | Email, Calendar, Contacts | Yes |
| `drive-mcp` | Google Drive files & folders | Yes (shares tokens with gmail-mcp) |
| `docs-mcp` | Local document processing, OCR | No |

---

## Prerequisites

- Python 3.10+ (3.11 recommended)
- A Google account (for gmail-mcp and drive-mcp)
- Claude Code or Claude Desktop installed

---

## Part 1: Installation

### 1.1 Clone and Set Up

```bash
# Clone the repository
git clone https://github.com/mideliberto/gmail-mcp-extended.git
cd gmail-mcp-extended

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install base package (gmail-mcp + drive-mcp)
pip install -e .
```

### 1.2 Install docs-mcp Dependencies (Optional)

If you want local document processing:

```bash
# Office documents (DOCX, XLSX, PPTX)
pip install python-docx openpyxl python-pptx

# PDF processing
pip install pypdf pdfplumber

# Local OCR (optional - for scanned documents)
pip install pytesseract pdf2image Pillow
```

### 1.3 Install OCR System Dependencies (Optional)

For local OCR with docs-mcp, you need Tesseract and Poppler:

**macOS:**
```bash
brew install tesseract poppler

# Verify installation
tesseract --version
pdftoppm -v
```

**Ubuntu/Debian:**
```bash
sudo apt install tesseract-ocr poppler-utils

# For additional language support
sudo apt install tesseract-ocr-fra tesseract-ocr-deu  # French, German, etc.
```

**Windows:**
- Tesseract: Download from https://github.com/UB-Mannheim/tesseract/wiki
- Poppler: Download from https://github.com/osber/poppler-windows/releases
- Add both to PATH

### 1.4 Generate Encryption Key

Generate a key to encrypt your OAuth tokens at rest:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Save this key - you'll need it for configuration.

---

## Part 2: Google Cloud Project Setup

**Required for:** gmail-mcp, drive-mcp
**Skip if:** Only using docs-mcp

### 2.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown (top-left, next to "Google Cloud")
3. Click **New Project**
4. **Project name:** `gmail-mcp` (or any name)
5. Click **Create**
6. Select the new project from the dropdown

### 2.2 Enable Required APIs

Navigate to **APIs & Services → Library** and enable these APIs:

| API | Required For |
|-----|--------------|
| **Gmail API** | gmail-mcp: Email operations |
| **Google Calendar API** | gmail-mcp: Calendar operations |
| **People API** | gmail-mcp: Contacts |
| **Google Drive API** | drive-mcp: File operations |
| **Drive Labels API** | drive-mcp: Label management |
| **Drive Activity API** | drive-mcp: Activity tracking |

For each API:
1. Search for the API name
2. Click on the result
3. Click **Enable**

**Verify:** Go to **APIs & Services → Enabled APIs & services**. You should see all 6 APIs listed.

### 2.3 Configure OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. Select **External** and click **Create**
3. Fill in App Information:

| Field | Value |
|-------|-------|
| App name | `Gmail MCP` |
| User support email | Your email |
| Developer contact | Your email |

4. Click **Save and Continue**

### 2.4 Add OAuth Scopes

1. Click **Add or Remove Scopes**
2. Scroll to **Manually add scopes**
3. Paste all scopes (copy the entire block):

```
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.labels
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/gmail.settings.basic
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/calendar.events
https://www.googleapis.com/auth/contacts.readonly
https://www.googleapis.com/auth/contacts
https://www.googleapis.com/auth/drive
https://www.googleapis.com/auth/drive.labels
https://www.googleapis.com/auth/drive.activity.readonly
https://www.googleapis.com/auth/userinfo.email
https://www.googleapis.com/auth/userinfo.profile
openid
```

4. Click **Add to Table**
5. Click **Update**
6. Click **Save and Continue**

### 2.5 Add Test Users

**IMPORTANT:** While in Testing mode, only users listed here can authenticate.

1. Click **+ Add Users**
2. Enter your email address
3. Click **Add**
4. Click **Save and Continue**

### 2.6 Create OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth client ID**
3. **Application type:** Select **Desktop app** (NOT "Web application")
4. **Name:** `Gmail MCP Desktop`
5. Click **Create**
6. **Save your Client ID and Client Secret!**

---

## Part 3: Configure Claude Code / Claude Desktop

### 3.1 Full Configuration (All Three Servers)

Edit your Claude configuration file:

- **Claude Code:** `~/.claude/settings.json`
- **Claude Desktop (macOS):** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Claude Desktop (Windows):** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gmail-mcp": {
      "command": "/path/to/gmail-mcp-extended/.venv/bin/mcp",
      "args": ["run", "/path/to/gmail-mcp-extended/gmail_mcp/main.py:mcp"],
      "cwd": "/path/to/gmail-mcp-extended",
      "env": {
        "PYTHONPATH": "/path/to/gmail-mcp-extended",
        "CONFIG_FILE_PATH": "/path/to/gmail-mcp-extended/config.yaml",
        "GOOGLE_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "GOCSPX-your-client-secret",
        "TOKEN_ENCRYPTION_KEY": "your-generated-encryption-key",
        "VAULT_PATH": "/path/to/your/obsidian/vault"
      }
    },
    "drive-mcp": {
      "command": "/path/to/gmail-mcp-extended/.venv/bin/mcp",
      "args": ["run", "/path/to/gmail-mcp-extended/drive_mcp/main.py:mcp"],
      "cwd": "/path/to/gmail-mcp-extended",
      "env": {
        "PYTHONPATH": "/path/to/gmail-mcp-extended",
        "GOOGLE_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "GOCSPX-your-client-secret",
        "TOKEN_ENCRYPTION_KEY": "your-generated-encryption-key"
      }
    },
    "docs-mcp": {
      "command": "/path/to/gmail-mcp-extended/.venv/bin/mcp",
      "args": ["run", "/path/to/gmail-mcp-extended/docs_mcp/main.py:mcp"],
      "cwd": "/path/to/gmail-mcp-extended",
      "env": {
        "PYTHONPATH": "/path/to/gmail-mcp-extended",
        "VAULT_PATH": "/path/to/your/obsidian/vault"
      }
    }
  }
}
```

Replace `/path/to/gmail-mcp-extended` with your actual path.

### 3.2 Minimal Configuration (Email Only)

If you only need email and calendar:

```json
{
  "mcpServers": {
    "gmail-mcp": {
      "command": "/path/to/gmail-mcp-extended/.venv/bin/mcp",
      "args": ["run", "/path/to/gmail-mcp-extended/gmail_mcp/main.py:mcp"],
      "cwd": "/path/to/gmail-mcp-extended",
      "env": {
        "PYTHONPATH": "/path/to/gmail-mcp-extended",
        "GOOGLE_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "GOCSPX-your-client-secret",
        "TOKEN_ENCRYPTION_KEY": "your-generated-encryption-key"
      }
    }
  }
}
```

### 3.3 Offline Only (docs-mcp)

For local document processing without Google:

```json
{
  "mcpServers": {
    "docs-mcp": {
      "command": "/path/to/gmail-mcp-extended/.venv/bin/mcp",
      "args": ["run", "/path/to/gmail-mcp-extended/docs_mcp/main.py:mcp"],
      "cwd": "/path/to/gmail-mcp-extended",
      "env": {
        "PYTHONPATH": "/path/to/gmail-mcp-extended",
        "VAULT_PATH": "/path/to/your/obsidian/vault"
      }
    }
  }
}
```

---

## Part 4: First-Time Authentication

### Authentication Methods

There are two ways to authenticate:

| Method | Tool | Best For |
|--------|------|----------|
| **Automatic** | `authenticate` | When it works - opens browser and handles callback automatically |
| **Manual** | `login_tool` | More reliable - returns OAuth URL for you to open manually |

**Recommended approach:** Use `login_tool` if `authenticate` fails or hangs.

### Using authenticate (Automatic)

1. Start Claude Code or Claude Desktop
2. Ask Claude: "authenticate to gmail"
3. Browser opens automatically
4. Log in with your Google account
5. Grant all requested permissions
6. Redirected to `localhost:8000/auth/callback` - done!

### Using login_tool (Manual - More Reliable)

1. Ask Claude: "use login_tool to get auth URL"
2. Claude returns an OAuth URL
3. Copy/paste URL into your browser
4. Log in with your Google account
5. Grant all requested permissions
6. Redirected to `localhost:8000/auth/callback` - done!

**Why login_tool is more reliable:** The `authenticate` tool tries to open a browser AND start a callback server simultaneously. If there's a timing issue or browser launch failure, authentication fails. The `login_tool` just returns the URL, letting you handle the browser manually while the MCP server handles the callback.

### Token Storage

Tokens are stored encrypted in `~/gmail_mcp_tokens/` (or custom path in config.yaml).

**Note:** drive-mcp shares tokens with gmail-mcp. Once authenticated with gmail-mcp, drive-mcp will work automatically (if Drive API scopes were included).

---

## Environment Variables Reference

| Variable | Required For | Description |
|----------|--------------|-------------|
| `GOOGLE_CLIENT_ID` | gmail-mcp, drive-mcp | OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | gmail-mcp, drive-mcp | OAuth client secret |
| `TOKEN_ENCRYPTION_KEY` | gmail-mcp, drive-mcp | **Required.** Fernet encryption key for token storage |
| `VAULT_PATH` | Optional | Path to Obsidian vault for vault export tools |
| `CONFIG_FILE_PATH` | Optional | Path to config.yaml |

**Note:** `TOKEN_ENCRYPTION_KEY` is mandatory. The server will fail to start without it. A random salt file (`encryption_salt`) is automatically created alongside your tokens for PBKDF2 key derivation.

---

## OAuth Scopes Reference

### gmail-mcp Scopes

| Scope | Purpose |
|-------|---------|
| `gmail.readonly` | Read emails |
| `gmail.send` | Send emails |
| `gmail.labels` | Manage labels |
| `gmail.modify` | Archive, trash, mark read |
| `gmail.settings.basic` | Filters, vacation responder |
| `calendar.readonly` | Read calendar |
| `calendar.events` | Create/modify events |
| `contacts.readonly` | Read contacts |
| `contacts` | Create/update/delete contacts |

### drive-mcp Scopes

| Scope | Purpose |
|-------|---------|
| `drive` | Full Drive access (files, folders, sharing) |
| `drive.labels` | Drive label management |
| `drive.activity.readonly` | Drive activity tracking |

---

## Updating OAuth Scopes

If you need to add new scopes after initial setup:

1. **Google Cloud Console:** Add scope to OAuth consent screen
2. **Re-authenticate:**
   ```
   Ask Claude: "logout and re-authenticate"
   ```
   Or delete `~/gmail_mcp_tokens/tokens.json` and authenticate fresh

---

## Troubleshooting

### "Access blocked: This app's request is invalid"
- Ensure you selected **Desktop app** (not Web application) when creating credentials
- Verify redirect_uri is `http://localhost:8000/auth/callback`

### "This app isn't verified"
- Click **Advanced** → **Go to [app name] (unsafe)**
- This is expected for personal apps in Testing mode

### "User not in test users list"
- Go to OAuth consent screen → Test users → Add your email

### "Token expired" or "Invalid credentials"
- Delete `~/gmail_mcp_tokens/tokens.json`
- Re-authenticate

### authenticate tool fails with "Something went wrong"
- Use `login_tool` instead - it returns the OAuth URL for manual browser navigation
- The `authenticate` tool can fail due to browser launch issues or timing problems
- `login_tool` is more reliable as it separates URL generation from browser handling

### "Contacts API not enabled" error
- Ensure `contacts_api_enabled: true` in config.yaml
- Or set environment variable `CONTACTS_API_ENABLED=true`

### "Drive API not enabled" error
- Verify Drive API is enabled in Google Cloud Console
- Check that drive scopes are in your OAuth consent screen

### OCR not working (docs-mcp)
- Verify Tesseract is installed: `tesseract --version`
- Verify Poppler is installed: `pdftoppm -v`
- Check PATH includes Tesseract and Poppler binaries

### "No module named 'python-docx'" (docs-mcp)
- Install Office dependencies: `pip install python-docx openpyxl python-pptx`

---

## Security Best Practices

1. **Never commit secrets to git** - Keep Client ID, Client Secret, and Encryption Key in your Claude config file only

2. **Rotate credentials if exposed:**
   - Google Cloud Console → Credentials → Delete old → Create new
   - Generate new encryption key
   - Delete `~/gmail_mcp_tokens/encryption_salt` (new salt will be generated)
   - Update Claude config
   - Re-authenticate

3. **Use test mode** - No need to publish OAuth app for personal use

4. **Backup config securely:**
   - Use a private git repo
   - Or encrypt with `openssl`
   - Or store in password manager

### Built-in Security Features

- **Encrypted token storage** - OAuth tokens are encrypted at rest using Fernet with PBKDF2 key derivation
- **Random salt per installation** - Each installation generates a unique random salt for key derivation
- **CSRF protection** - OAuth state parameter validation prevents cross-site request forgery
- **Thread-safe caching** - Service instances are cached with proper locking for concurrent access
- **Path traversal protection** - Vault operations validate paths stay within the vault directory

---

## Files Reference

### Repository Files (Public)

| File | Purpose |
|------|---------|
| `config.yaml` | Server settings, defaults (no secrets) |
| `pyproject.toml` | Python package configuration |
| `gmail_mcp/` | Email, Calendar, Contacts server |
| `drive_mcp/` | Google Drive server |
| `docs_mcp/` | Local document processing server |

### User Files (Private)

| File | Purpose |
|------|---------|
| `~/.claude/settings.json` | Claude Code MCP config with secrets |
| `~/Library/Application Support/Claude/claude_desktop_config.json` | Claude Desktop config |
| `~/gmail_mcp_tokens/tokens.json` | Encrypted OAuth tokens |

---

## Quick Reference

| Task | Command |
|------|---------|
| Check auth status | Ask Claude: "check gmail auth status" |
| Re-authenticate | Ask Claude: "logout and authenticate" |
| View tokens location | `~/gmail_mcp_tokens/tokens.json` |
| Run tests | `cd gmail-mcp-extended && pytest tests/ -v` |
| List all tools | Ask Claude: "what tools are available" |
