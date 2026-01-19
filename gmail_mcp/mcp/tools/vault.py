"""
Vault Integration Tools Module

Handles saving emails to an Obsidian vault or other note-taking system.
Configurable inbox path for different vault setups.
"""

import os
import re
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
from gmail_mcp.utils.config import get_config
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger(__name__)


def setup_vault_tools(mcp: FastMCP) -> None:
    """Set up vault integration tools on the FastMCP application."""

    @mcp.tool()
    def save_email_to_vault(
        email_id: str,
        vault_path: Optional[str] = None,
        inbox_folder: str = "0-inbox",
        include_attachments: bool = False,
        attachment_folder: str = "attachments",
        custom_filename: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Save an email to an Obsidian vault or note-taking system.

        Creates a markdown file with the email content, metadata as frontmatter,
        and optionally downloads attachments.

        Args:
            email_id (str): The ID of the email to save
            vault_path (str, optional): Path to the vault root. If not provided,
                                       uses VAULT_PATH from config or environment.
            inbox_folder (str): Folder within vault for inbox items (default: "0-inbox")
            include_attachments (bool): Whether to download attachments (default: False)
            attachment_folder (str): Folder for attachments relative to inbox (default: "attachments")
            custom_filename (str, optional): Custom filename (without .md extension).
                                            Defaults to "YYYY-MM-DD Email from [sender] - [subject]"
            tags (List[str], optional): Additional tags to add to frontmatter

        Returns:
            Dict[str, Any]: Result including the saved file path

        Example usage:
        1. Save email with default settings:
           save_email_to_vault(email_id="...")

        2. Save to custom vault location:
           save_email_to_vault(
               email_id="...",
               vault_path="/Users/katherine/ObsidianVault",
               inbox_folder="Inbox"
           )

        3. Save with attachments and custom tags:
           save_email_to_vault(
               email_id="...",
               include_attachments=True,
               tags=["work", "important"]
           )
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        # Determine vault path
        if not vault_path:
            config = get_config()
            vault_path = config.get("vault_path") or os.environ.get("VAULT_PATH")

        if not vault_path:
            return {
                "success": False,
                "error": "No vault path configured. Provide vault_path parameter or set VAULT_PATH environment variable."
            }

        vault_path = os.path.expanduser(vault_path)
        if not os.path.isdir(vault_path):
            return {
                "success": False,
                "error": f"Vault path does not exist: {vault_path}"
            }

        try:
            service = get_gmail_service(credentials)

            # Get the email
            msg = service.users().messages().get(userId="me", id=email_id, format="full").execute()

            # Extract headers
            headers = {}
            for header in msg["payload"]["headers"]:
                headers[header["name"].lower()] = header["value"]

            # Extract body
            body = ""
            html_body = ""
            if "parts" in msg["payload"]:
                for part in msg["payload"]["parts"]:
                    if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    elif part["mimeType"] == "text/html" and "data" in part.get("body", {}):
                        html_body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            elif "body" in msg["payload"] and "data" in msg["payload"]["body"]:
                body = base64.urlsafe_b64decode(msg["payload"]["body"]["data"]).decode("utf-8")

            # Use plain text if available, otherwise convert HTML
            if not body and html_body:
                body = _html_to_markdown(html_body)

            # Parse date
            email_date = headers.get("date", "")
            try:
                import dateutil.parser as parser
                parsed_date = parser.parse(email_date)
                date_str = parsed_date.strftime("%Y-%m-%d")
                datetime_str = parsed_date.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                date_str = datetime.now().strftime("%Y-%m-%d")
                datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Extract sender name/email
            from_header = headers.get("from", "Unknown")
            sender_match = re.match(r'^"?([^"<]+)"?\s*<?([^>]*)>?$', from_header)
            if sender_match:
                sender_name = sender_match.group(1).strip()
                sender_email = sender_match.group(2).strip() or sender_name
            else:
                sender_name = from_header
                sender_email = from_header

            # Clean subject for filename
            subject = headers.get("subject", "No Subject")
            clean_subject = _sanitize_filename(subject)[:50]
            clean_sender = _sanitize_filename(sender_name)[:30]

            # Generate filename
            if custom_filename:
                filename = _sanitize_filename(custom_filename)
            else:
                filename = f"{date_str} Email from {clean_sender} - {clean_subject}"

            # Ensure inbox folder exists
            inbox_path = Path(vault_path) / inbox_folder
            inbox_path.mkdir(parents=True, exist_ok=True)

            # Handle attachments
            attachment_paths = []
            if include_attachments:
                attachments = _get_attachments(msg)
                if attachments:
                    attachment_dir = inbox_path / attachment_folder
                    attachment_dir.mkdir(parents=True, exist_ok=True)

                    for att in attachments:
                        try:
                            att_data = service.users().messages().attachments().get(
                                userId="me",
                                messageId=email_id,
                                id=att["attachment_id"]
                            ).execute()

                            data = base64.urlsafe_b64decode(att_data["data"])
                            att_filename = _sanitize_filename(att["filename"])
                            att_path = attachment_dir / att_filename

                            with open(att_path, "wb") as f:
                                f.write(data)

                            # Relative path for linking in markdown
                            rel_path = f"{attachment_folder}/{att_filename}"
                            attachment_paths.append({
                                "filename": att["filename"],
                                "path": rel_path,
                                "size": len(data)
                            })
                        except Exception as e:
                            logger.error(f"Failed to download attachment {att['filename']}: {e}")

            # Build frontmatter
            frontmatter_tags = ["email", "inbox"]
            if tags:
                frontmatter_tags.extend(tags)

            frontmatter = f"""---
type: email
created: {datetime_str}
from: "{sender_email}"
from_name: "{sender_name}"
to: "{headers.get('to', 'Unknown')}"
subject: "{subject}"
date: {date_str}
email_id: "{email_id}"
tags: [{', '.join(frontmatter_tags)}]
---

"""

            # Build note content
            content = frontmatter
            content += f"# {subject}\n\n"
            content += f"**From:** {from_header}\n"
            content += f"**To:** {headers.get('to', 'Unknown')}\n"
            if headers.get('cc'):
                content += f"**CC:** {headers.get('cc')}\n"
            content += f"**Date:** {email_date}\n"
            content += f"**Email Link:** [Open in Gmail](https://mail.google.com/mail/u/0/#inbox/{msg['threadId']}/{email_id})\n"
            content += "\n---\n\n"
            content += body

            # Add attachments section
            if attachment_paths:
                content += "\n\n---\n\n## Attachments\n\n"
                for att in attachment_paths:
                    content += f"- [[{att['path']}|{att['filename']}]] ({att['size']} bytes)\n"

            # Write the file
            file_path = inbox_path / f"{filename}.md"

            # Handle duplicate filenames
            counter = 1
            while file_path.exists():
                file_path = inbox_path / f"{filename} ({counter}).md"
                counter += 1

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "message": f"Email saved to vault.",
                "file_path": str(file_path),
                "filename": file_path.name,
                "attachments_saved": len(attachment_paths),
                "attachment_details": attachment_paths
            }

        except Exception as e:
            logger.error(f"Failed to save email to vault: {e}")
            return {"success": False, "error": f"Failed to save email to vault: {e}"}

    @mcp.tool()
    def batch_save_emails_to_vault(
        query: str,
        vault_path: Optional[str] = None,
        inbox_folder: str = "0-inbox",
        max_emails: int = 10,
        include_attachments: bool = False,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Save multiple emails matching a query to the vault.

        Args:
            query (str): Gmail search query
            vault_path (str, optional): Path to vault root
            inbox_folder (str): Folder for inbox items (default: "0-inbox")
            max_emails (int): Maximum emails to save (default: 10, max: 25)
            include_attachments (bool): Download attachments (default: False)
            tags (List[str], optional): Tags to add to all saved emails

        Returns:
            Dict[str, Any]: Results of the batch operation

        Example usage:
        1. Save unread emails from a sender:
           batch_save_emails_to_vault(
               query="from:important@company.com is:unread",
               tags=["work", "review"]
           )

        2. Save emails with Claude review label:
           batch_save_emails_to_vault(
               query="label:Claude-Review",
               include_attachments=True
           )
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        max_emails = min(max_emails, 25)

        try:
            service = get_gmail_service(credentials)

            result = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_emails
            ).execute()

            messages = result.get("messages", [])

            if not messages:
                return {
                    "success": True,
                    "message": "No emails found matching query.",
                    "saved": 0,
                    "failed": 0,
                    "query": query
                }

            saved = []
            failed = []

            # Use the save_email_to_vault tool for each email
            for msg in messages:
                # Get basic info for reporting
                try:
                    email = service.users().messages().get(
                        userId="me",
                        id=msg["id"],
                        format="metadata",
                        metadataHeaders=["Subject", "From"]
                    ).execute()

                    headers = {h["name"].lower(): h["value"] for h in email.get("payload", {}).get("headers", [])}
                    subject = headers.get("subject", "No Subject")
                    from_addr = headers.get("from", "Unknown")

                    # Call save function directly (not through mcp.tool)
                    save_result = _save_single_email(
                        service=service,
                        email_id=msg["id"],
                        vault_path=vault_path,
                        inbox_folder=inbox_folder,
                        include_attachments=include_attachments,
                        tags=tags
                    )

                    if save_result.get("success"):
                        saved.append({
                            "email_id": msg["id"],
                            "subject": subject,
                            "from": from_addr,
                            "file_path": save_result.get("file_path")
                        })
                    else:
                        failed.append({
                            "email_id": msg["id"],
                            "subject": subject,
                            "from": from_addr,
                            "error": save_result.get("error")
                        })

                except Exception as e:
                    failed.append({
                        "email_id": msg["id"],
                        "error": str(e)
                    })

            return {
                "success": True,
                "message": f"Saved {len(saved)} emails to vault.",
                "saved": len(saved),
                "failed": len(failed),
                "query": query,
                "saved_details": saved,
                "failed_details": failed if failed else None
            }

        except Exception as e:
            logger.error(f"Failed to batch save emails: {e}")
            return {"success": False, "error": f"Failed to batch save emails: {e}"}


def _save_single_email(
    service,
    email_id: str,
    vault_path: Optional[str],
    inbox_folder: str,
    include_attachments: bool,
    tags: Optional[List[str]]
) -> Dict[str, Any]:
    """Internal function to save a single email (for batch operations)."""

    # Determine vault path
    if not vault_path:
        config = get_config()
        vault_path = config.get("vault_path") or os.environ.get("VAULT_PATH")

    if not vault_path:
        return {
            "success": False,
            "error": "No vault path configured."
        }

    vault_path = os.path.expanduser(vault_path)
    if not os.path.isdir(vault_path):
        return {
            "success": False,
            "error": f"Vault path does not exist: {vault_path}"
        }

    try:
        # Get the email
        msg = service.users().messages().get(userId="me", id=email_id, format="full").execute()

        # Extract headers
        headers = {}
        for header in msg["payload"]["headers"]:
            headers[header["name"].lower()] = header["value"]

        # Extract body
        body = ""
        html_body = ""
        if "parts" in msg["payload"]:
            for part in msg["payload"]["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                elif part["mimeType"] == "text/html" and "data" in part.get("body", {}):
                    html_body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
        elif "body" in msg["payload"] and "data" in msg["payload"]["body"]:
            body = base64.urlsafe_b64decode(msg["payload"]["body"]["data"]).decode("utf-8")

        if not body and html_body:
            body = _html_to_markdown(html_body)

        # Parse date
        email_date = headers.get("date", "")
        try:
            import dateutil.parser as parser
            parsed_date = parser.parse(email_date)
            date_str = parsed_date.strftime("%Y-%m-%d")
            datetime_str = parsed_date.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            date_str = datetime.now().strftime("%Y-%m-%d")
            datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Extract sender
        from_header = headers.get("from", "Unknown")
        sender_match = re.match(r'^"?([^"<]+)"?\s*<?([^>]*)>?$', from_header)
        if sender_match:
            sender_name = sender_match.group(1).strip()
            sender_email = sender_match.group(2).strip() or sender_name
        else:
            sender_name = from_header
            sender_email = from_header

        subject = headers.get("subject", "No Subject")
        clean_subject = _sanitize_filename(subject)[:50]
        clean_sender = _sanitize_filename(sender_name)[:30]

        filename = f"{date_str} Email from {clean_sender} - {clean_subject}"

        inbox_path = Path(vault_path) / inbox_folder
        inbox_path.mkdir(parents=True, exist_ok=True)

        # Handle attachments
        attachment_paths = []
        if include_attachments:
            attachments = _get_attachments(msg)
            if attachments:
                attachment_dir = inbox_path / "attachments"
                attachment_dir.mkdir(parents=True, exist_ok=True)

                for att in attachments:
                    try:
                        att_data = service.users().messages().attachments().get(
                            userId="me",
                            messageId=email_id,
                            id=att["attachment_id"]
                        ).execute()

                        data = base64.urlsafe_b64decode(att_data["data"])
                        att_filename = _sanitize_filename(att["filename"])
                        att_path = attachment_dir / att_filename

                        with open(att_path, "wb") as f:
                            f.write(data)

                        rel_path = f"attachments/{att_filename}"
                        attachment_paths.append({
                            "filename": att["filename"],
                            "path": rel_path,
                            "size": len(data)
                        })
                    except Exception as e:
                        logger.error(f"Failed to download attachment: {e}")

        # Build frontmatter
        frontmatter_tags = ["email", "inbox"]
        if tags:
            frontmatter_tags.extend(tags)

        frontmatter = f"""---
type: email
created: {datetime_str}
from: "{sender_email}"
from_name: "{sender_name}"
to: "{headers.get('to', 'Unknown')}"
subject: "{subject}"
date: {date_str}
email_id: "{email_id}"
tags: [{', '.join(frontmatter_tags)}]
---

"""

        content = frontmatter
        content += f"# {subject}\n\n"
        content += f"**From:** {from_header}\n"
        content += f"**To:** {headers.get('to', 'Unknown')}\n"
        if headers.get('cc'):
            content += f"**CC:** {headers.get('cc')}\n"
        content += f"**Date:** {email_date}\n"
        content += f"**Email Link:** [Open in Gmail](https://mail.google.com/mail/u/0/#inbox/{msg['threadId']}/{email_id})\n"
        content += "\n---\n\n"
        content += body

        if attachment_paths:
            content += "\n\n---\n\n## Attachments\n\n"
            for att in attachment_paths:
                content += f"- [[{att['path']}|{att['filename']}]] ({att['size']} bytes)\n"

        file_path = inbox_path / f"{filename}.md"

        counter = 1
        while file_path.exists():
            file_path = inbox_path / f"{filename} ({counter}).md"
            counter += 1

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "file_path": str(file_path)
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def _sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    # Remove or replace invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def _get_attachments(msg: dict) -> list:
    """Extract attachment info from a message."""
    attachments = []

    def find_attachments(parts):
        for part in parts:
            if part.get("filename"):
                attachments.append({
                    "attachment_id": part["body"].get("attachmentId"),
                    "filename": part["filename"],
                    "mime_type": part["mimeType"],
                    "size": part["body"].get("size", 0)
                })
            if "parts" in part:
                find_attachments(part["parts"])

    if "parts" in msg["payload"]:
        find_attachments(msg["payload"]["parts"])

    return attachments


def _html_to_markdown(html: str) -> str:
    """Basic HTML to markdown conversion."""
    import re

    # Remove scripts and styles
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Convert common elements
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p[^>]*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<li[^>]*>', '- ', text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)

    # Remove remaining tags
    text = re.sub(r'<[^>]+>', '', text)

    # Decode HTML entities
    import html as html_module
    text = html_module.unescape(text)

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text
