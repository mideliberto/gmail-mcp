# Gmail MCP Project Structure

This document outlines the structure of the Gmail MCP project.

```
gmail-mcp/
├── gmail_mcp/                     # Main package directory
│   ├── auth/                      # Authentication modules
│   │   ├── callback_server.py     # OAuth callback server
│   │   ├── oauth.py               # OAuth2 flow implementation
│   │   └── token_manager.py       # Token storage with PBKDF2 encryption
│   │
│   ├── calendar/                  # Calendar modules
│   │   └── processor.py           # Calendar event processing
│   │
│   ├── gmail/                     # Gmail modules
│   │   ├── processor.py           # Email parsing and analysis
│   │   └── helpers.py             # Email extraction utilities
│   │
│   ├── mcp/                       # MCP implementation
│   │   ├── resources.py           # MCP resources
│   │   ├── prompts.py             # MCP prompts
│   │   ├── tools.py               # MCP tools (40+ tools)
│   │   └── schemas.py             # Pydantic schemas
│   │
│   ├── utils/                     # Utilities
│   │   ├── config.py              # Configuration with caching
│   │   ├── services.py            # Gmail/Calendar service caching
│   │   └── logger.py              # Logging
│   │
│   └── main.py                    # Entry point
│
├── tests/                         # Test suite (153 tests)
│   ├── test_token_manager.py      # Token manager tests
│   ├── test_oauth.py              # OAuth flow tests
│   ├── test_config.py             # Config tests
│   ├── test_services.py           # Service caching tests
│   ├── test_helpers.py            # Helper function tests
│   ├── test_tools.py              # Gmail tool tests
│   ├── test_calendar_processor.py # Calendar processor tests
│   ├── test_calendar_tools.py     # Calendar tool tests
│   ├── test_email_management.py   # Email management tests
│   ├── test_labels_attachments.py # Labels/attachments tests
│   └── test_bulk_and_reply.py     # Bulk ops/reply tests
│
├── docs/                          # Documentation
│   ├── overview.md                # Component overview
│   └── structure.md               # This file
│
├── config.yaml                    # Application configuration
├── pyproject.toml                 # Dependencies and metadata
├── README.md                      # Project readme
└── uv.lock                        # UV lock file
```

## Key Components

### Authentication (auth/)

- **token_manager.py**: Singleton pattern, PBKDF2 encryption, OAuth state verification
- **oauth.py**: OAuth2 flow with CSRF protection via state parameter
- **callback_server.py**: Local server for OAuth callbacks

### Gmail (gmail/)

- **processor.py**: Email parsing, thread analysis, entity extraction
- **helpers.py**: `extract_email_info()` helper to reduce code duplication

### Calendar (calendar/)

- **processor.py**: Natural language date parsing, event creation, meeting suggestions

### MCP (mcp/)

- **tools.py**: 40+ tools for Gmail and Calendar operations
- **resources.py**: Context resources for Claude
- **prompts.py**: User guidance prompts
- **schemas.py**: Pydantic v2 schemas with field serializers

### Utilities (utils/)

- **config.py**: YAML config loading with caching
- **services.py**: Gmail/Calendar API service caching (credentials-aware)
- **logger.py**: Logging utilities

## Configuration

- **config.yaml**: API scopes, token paths, feature flags
- Environment variables override YAML values:
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
  - `TOKEN_ENCRYPTION_KEY`
  - `TOKEN_STORAGE_PATH`
