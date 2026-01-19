"""
MCP Schemas Module

This module defines the schemas used by the MCP resources.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_serializer


class EmailContextItem(BaseModel):
    """
    Schema for email context items.
    
    This schema defines the structure of email context items that are
    returned by the email resource.
    """
    type: str = "email"
    content: Dict[str, Any]


class ThreadContextItem(BaseModel):
    """
    Schema for thread context items.
    
    This schema defines the structure of thread context items that are
    returned by the thread resource.
    """
    type: str = "thread"
    content: Dict[str, Any]


class SenderContextItem(BaseModel):
    """
    Schema for sender context items.
    
    This schema defines the structure of sender context items that are
    returned by the sender resource.
    """
    type: str = "sender"
    content: Dict[str, Any]


class EmailMetadata(BaseModel):
    """
    Schema for email metadata.
    
    This schema defines the structure of email metadata that is
    extracted from Gmail API responses.
    """
    id: str
    thread_id: str
    subject: str
    from_email: str
    from_name: str
    to: List[str]
    cc: List[str] = []
    date: datetime
    has_attachments: bool
    labels: List[str]


class EmailContent(BaseModel):
    """
    Schema for email content.
    
    This schema defines the structure of email content that is
    extracted from Gmail API responses.
    """
    plain_text: str
    html: Optional[str] = None
    attachments: List[Dict[str, Any]] = []


class ThreadInfo(BaseModel):
    """
    Schema for thread information.
    
    This schema defines the structure of thread information that is
    extracted from Gmail API responses.
    """
    id: str
    subject: str
    message_count: int
    participants: List[Dict[str, str]]
    last_message_date: datetime


class SenderInfo(BaseModel):
    """
    Schema for sender information.
    
    This schema defines the structure of sender information that is
    extracted from Gmail API responses.
    """
    email: str
    name: str
    message_count: int
    first_message_date: Optional[datetime] = None
    last_message_date: Optional[datetime] = None
    common_topics: List[str] = []


class EntityExtraction(BaseModel):
    """
    Schema for entity extraction results.
    
    This schema defines the structure of entity extraction results
    from email content analysis.
    """
    dates: List[str] = []
    times: List[str] = []
    phone_numbers: List[str] = []
    email_addresses: List[str] = []
    urls: List[str] = []
    action_items: List[str] = []


class CommunicationPattern(BaseModel):
    """
    Schema for communication pattern analysis.
    
    This schema defines the structure of communication pattern analysis
    between two email addresses.
    """
    message_count: int
    communication_exists: bool
    first_contact: Optional[str] = None
    last_contact: Optional[str] = None
    frequency: Optional[str] = None
    avg_response_time_hours: Optional[float] = None
    communication_style: Optional[Dict[str, Any]] = None
    common_topics: List[str] = []


class RelatedEmail(BaseModel):
    """
    Schema for related email information.
    
    This schema defines the structure of related email information
    that is returned by the find_related_emails function.
    """
    id: str
    thread_id: str
    subject: str
    from_email: str
    from_name: str
    date: str
    relevance_score: float


class EmailReplyContext(BaseModel):
    """
    Schema for email reply context.
    
    This schema defines the structure of the context used for
    generating email replies.
    """
    original_email: Dict[str, Any]
    thread_context: Optional[Dict[str, Any]] = None
    sender_context: Optional[Dict[str, Any]] = None
    communication_patterns: Optional[Dict[str, Any]] = None
    entities: Optional[Dict[str, List[str]]] = None
    related_emails: Optional[List[Dict[str, Any]]] = None


class CalendarEventSchema(BaseModel):
    """
    Schema for calendar event information.

    This schema defines the structure of calendar event information
    that is used for creating and managing events.
    """
    summary: str
    start_datetime: datetime
    end_datetime: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: List[str] = []
    color_id: Optional[str] = None
    timezone: str = "UTC"
    all_day: bool = False

    @field_serializer("start_datetime", "end_datetime")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime fields to ISO format."""
        return value.isoformat() 