"""
Shared type definitions for the gmail-mcp monorepo.

This module contains TypedDict definitions used across all MCP servers.
"""

from typing import TypedDict, Optional, List, Dict, Any


# =============================================================================
# Drive Types
# =============================================================================

class DriveUser(TypedDict):
    """Represents a Google Drive user."""
    displayName: str
    emailAddress: str
    photoLink: Optional[str]


class DriveFile(TypedDict):
    """Represents a file in Google Drive."""
    id: str
    name: str
    mimeType: str
    size: Optional[int]
    createdTime: str
    modifiedTime: str
    parents: List[str]
    webViewLink: str
    webContentLink: Optional[str]
    owners: List[DriveUser]
    shared: bool
    trashed: bool


class DrivePermission(TypedDict):
    """Represents a permission on a Drive file."""
    id: str
    type: str  # user, group, domain, anyone
    role: str  # owner, organizer, fileOrganizer, writer, commenter, reader
    emailAddress: Optional[str]
    displayName: Optional[str]


class DriveReply(TypedDict):
    """Represents a reply to a Drive comment."""
    id: str
    author: DriveUser
    content: str
    createdTime: str
    modifiedTime: str


class DriveComment(TypedDict):
    """Represents a comment on a Drive file."""
    id: str
    author: DriveUser
    content: str
    createdTime: str
    modifiedTime: str
    resolved: bool
    replies: List[DriveReply]


class DriveRevision(TypedDict):
    """Represents a revision of a Drive file."""
    id: str
    modifiedTime: str
    lastModifyingUser: DriveUser
    size: Optional[int]


class SharedDrive(TypedDict):
    """Represents a Shared Drive."""
    id: str
    name: str
    createdTime: str
    hidden: bool


class DriveLabel(TypedDict):
    """Represents a Drive Label definition."""
    id: str
    name: str
    revisionId: str
    labelType: str
    fields: List[Dict[str, Any]]


class DriveFileLabel(TypedDict):
    """Represents a label applied to a file."""
    labelId: str
    revisionId: str
    fields: Dict[str, Any]


# =============================================================================
# Document Types
# =============================================================================

class DocContent(TypedDict):
    """Represents extracted content from a document."""
    text: str
    tables: List[List[List[str]]]
    metadata: Dict[str, Any]


class OcrResult(TypedDict):
    """Represents the result of OCR processing."""
    text: str
    confidence: float
    method: str  # "tesseract" | "drive"
    pages: Optional[int]


class PdfMetadata(TypedDict):
    """Represents PDF metadata."""
    title: Optional[str]
    author: Optional[str]
    subject: Optional[str]
    creator: Optional[str]
    producer: Optional[str]
    creation_date: Optional[str]
    modification_date: Optional[str]
    pages: int


class VaultExport(TypedDict):
    """Represents the result of exporting to vault."""
    success: bool
    file_path: str
    original_path: str
    frontmatter: Dict[str, Any]


# =============================================================================
# Chat Types
# =============================================================================

class ChatUser(TypedDict):
    """Represents a Google Chat user."""
    name: str
    displayName: str
    domainId: Optional[str]
    type: str  # HUMAN, BOT


class ChatSpace(TypedDict):
    """Represents a Google Chat space."""
    name: str
    type: str  # ROOM, DM, GROUP_CHAT
    displayName: Optional[str]
    spaceType: str
    singleUserBotDm: bool
    threaded: bool
    externalUserAllowed: bool


class ChatMessage(TypedDict):
    """Represents a message in Google Chat."""
    name: str
    sender: ChatUser
    createTime: str
    text: str
    thread: Optional[Dict[str, str]]
    space: Dict[str, str]
    argumentText: Optional[str]


class ChatMember(TypedDict):
    """Represents a member of a Google Chat space."""
    name: str
    state: str  # JOINED, INVITED, NOT_A_MEMBER
    role: str  # ROLE_MEMBER, ROLE_MANAGER
    member: ChatUser
    createTime: str


class ChatReaction(TypedDict):
    """Represents a reaction on a Google Chat message."""
    name: str
    user: ChatUser
    emoji: Dict[str, str]


class ChatAttachment(TypedDict):
    """Represents an attachment in Google Chat."""
    name: str
    contentName: str
    contentType: str
    thumbnailUri: Optional[str]
    downloadUri: Optional[str]
    source: str  # DRIVE_FILE, UPLOADED_CONTENT


# =============================================================================
# Common Types
# =============================================================================

class OperationResult(TypedDict):
    """Standard result type for operations."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]]
