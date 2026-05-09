"""Email manager — mailbox-based communication for the LingTai network.

Storage layout:
    agent_dir/mailbox/inbox/{uuid}.json
    agent_dir/mailbox/sent/{uuid}.json
    agent_dir/mailbox/archive/{uuid}.json
    agent_dir/mailbox/contacts.json

Actions: send, check, read, reply, search, archive, delete,
         contacts, add_contact, remove_contact, edit_contact
"""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

log = logging.getLogger(__name__)

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "send", "check", "read", "reply", "search",
                "archive", "delete",
                "contacts", "add_contact", "remove_contact", "edit_contact",
            ],
            "description": (
                "send: send an email (to, subject, body). "
                "check: list inbox summary with unread counts (optional folder). "
                "read: read a specific email by id. "
                "reply: reply to an email (id, body). "
                "search: search emails (query; optional folder). "
                "archive: move an email to archive (id). "
                "delete: permanently delete an email (id). "
                "contacts: list saved contacts. "
                "add_contact: add a new contact (name, address). "
                "remove_contact: remove a contact (name or address). "
                "edit_contact: edit an existing contact (name; optional new_name, new_address)."
            ),
        },
        "to": {
            "type": "string",
            "description": "Recipient agent name or address (for send)",
        },
        "subject": {
            "type": "string",
            "description": "Email subject (for send)",
        },
        "body": {
            "type": "string",
            "description": "Email body (for send, reply)",
        },
        "id": {
            "type": "string",
            "description": "Email ID (for read, reply, archive, delete)",
        },
        "folder": {
            "type": "string",
            "enum": ["inbox", "sent", "archive"],
            "description": "Folder to check or search (default: inbox)",
        },
        "query": {
            "type": "string",
            "description": "Search query (regex pattern)",
        },
        "limit": {
            "type": "integer",
            "description": "Max results to return (default 20)",
            "default": 20,
        },
        "name": {
            "type": "string",
            "description": "Contact name (for add_contact, remove_contact, edit_contact)",
        },
        "address": {
            "type": "string",
            "description": "Contact address (for add_contact, remove_contact)",
        },
        "new_name": {
            "type": "string",
            "description": "New name for edit_contact",
        },
        "new_address": {
            "type": "string",
            "description": "New address for edit_contact",
        },
    },
    "required": ["action"],
}

DESCRIPTION = (
    "Mailbox — send and receive messages in the LingTai agent network. "
    "Use 'send' to send a message (to, subject, body). "
    "Use 'check' to see inbox summary. "
    "Use 'read' to read a specific message by id. "
    "Use 'reply' to respond to a message. "
    "Use 'search' to find messages by text. "
    "Use 'archive' to move a message to the archive folder. "
    "Use 'delete' to permanently remove a message. "
    "Use 'contacts'/'add_contact'/'remove_contact'/'edit_contact' to manage contacts."
)


class EmailManager:
    """Manages the mailbox directory structure for agent communication."""

    def __init__(
        self,
        agent_dir: Path,
        *,
        agent_name: str = "",
    ) -> None:
        self._agent_dir = Path(agent_dir)
        self._mailbox_dir = self._agent_dir / "mailbox"
        self._agent_name = agent_name
        # Track read state in memory (set of email IDs)
        self._read_ids: set[str] = set()
        self._load_read_state()

    def _folder_dir(self, folder: str) -> Path:
        return self._mailbox_dir / folder

    # ------------------------------------------------------------------
    # Read state persistence
    # ------------------------------------------------------------------

    def _read_state_path(self) -> Path:
        return self._mailbox_dir / ".read_state.json"

    def _load_read_state(self) -> None:
        path = self._read_state_path()
        if path.is_file():
            try:
                self._read_ids = set(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                self._read_ids = set()

    def _save_read_state(self) -> None:
        self._mailbox_dir.mkdir(parents=True, exist_ok=True)
        target = self._read_state_path()
        fd, tmp = tempfile.mkstemp(dir=str(self._mailbox_dir), suffix=".tmp")
        try:
            os.write(fd, json.dumps(sorted(self._read_ids)).encode())
            os.fsync(fd)
            os.close(fd)
            os.replace(tmp, str(target))
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def _mark_read(self, email_id: str) -> None:
        self._read_ids.add(email_id)
        self._save_read_state()

    # ------------------------------------------------------------------
    # Email file I/O
    # ------------------------------------------------------------------

    def _write_email(self, folder: str, email: dict) -> Path:
        """Write an email JSON file to a folder. Returns the file path."""
        folder_path = self._folder_dir(folder)
        folder_path.mkdir(parents=True, exist_ok=True)
        email_id = email["id"]
        target = folder_path / f"{email_id}.json"
        fd, tmp = tempfile.mkstemp(dir=str(folder_path), suffix=".tmp")
        try:
            os.write(fd, json.dumps(email, indent=2, ensure_ascii=False).encode())
            os.fsync(fd)
            os.close(fd)
            os.replace(tmp, str(target))
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        return target

    def _read_email_file(self, path: Path) -> dict | None:
        """Read a single email JSON file."""
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _list_emails(self, folder: str) -> list[dict]:
        """Load all emails from a folder, sorted by date (newest first)."""
        folder_path = self._folder_dir(folder)
        if not folder_path.is_dir():
            return []
        emails = []
        for f in folder_path.iterdir():
            if f.suffix == ".json" and not f.name.startswith("."):
                email = self._read_email_file(f)
                if email:
                    emails.append(email)
        emails.sort(key=lambda e: e.get("date", ""), reverse=True)
        return emails

    def _find_email(self, email_id: str) -> tuple[str, Path] | None:
        """Find an email by ID across all folders. Returns (folder, path)."""
        for folder in ("inbox", "sent", "archive"):
            path = self._folder_dir(folder) / f"{email_id}.json"
            if path.is_file():
                return folder, path
        return None

    def _delete_email_file(self, path: Path) -> None:
        """Delete an email file."""
        try:
            path.unlink()
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Contacts
    # ------------------------------------------------------------------

    def _contacts_path(self) -> Path:
        return self._mailbox_dir / "contacts.json"

    def _load_contacts(self) -> dict[str, dict]:
        path = self._contacts_path()
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_contacts(self, contacts: dict[str, dict]) -> None:
        self._mailbox_dir.mkdir(parents=True, exist_ok=True)
        target = self._contacts_path()
        fd, tmp = tempfile.mkstemp(dir=str(self._mailbox_dir), suffix=".tmp")
        try:
            os.write(fd, json.dumps(contacts, indent=2, ensure_ascii=False).encode())
            os.fsync(fd)
            os.close(fd)
            os.replace(tmp, str(target))
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def handle(self, args: dict) -> dict:
        action = args.get("action")
        try:
            if action == "send":
                return self._send(args)
            elif action == "check":
                return self._check(args)
            elif action == "read":
                return self._read(args)
            elif action == "reply":
                return self._reply(args)
            elif action == "search":
                return self._search(args)
            elif action == "archive":
                return self._archive(args)
            elif action == "delete":
                return self._delete(args)
            elif action == "contacts":
                return self._contacts()
            elif action == "add_contact":
                return self._add_contact(args)
            elif action == "remove_contact":
                return self._remove_contact(args)
            elif action == "edit_contact":
                return self._edit_contact(args)
            else:
                return {"error": f"Unknown email action: {action}"}
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _send(self, args: dict) -> dict:
        to = args.get("to", "")
        subject = args.get("subject", "")
        body = args.get("body", "")
        if not to:
            return {"error": "to is required"}
        if not subject:
            return {"error": "subject is required"}
        if not body:
            return {"error": "body is required"}

        now = datetime.now(timezone.utc).isoformat()
        email_id = uuid4().hex[:12]

        email = {
            "id": email_id,
            "from": self._agent_name,
            "to": to,
            "subject": subject,
            "body": body,
            "date": now,
            "in_reply_to": args.get("in_reply_to"),
            "thread_id": args.get("thread_id") or email_id,
            "status": "sent",
        }

        # Write to sent/
        self._write_email("sent", email)

        # Also write to the recipient's inbox if they share the same
        # agent_dir parent (local delivery). We write a copy with
        # status="delivered" to our own sent/ and the original to their inbox.
        # For now, we write to the recipient's mailbox if it exists under
        # a sibling directory.
        self._try_local_delivery(email)

        return {"status": "sent", "id": email_id}

    def _try_local_delivery(self, email: dict) -> None:
        """Attempt local delivery to a sibling agent directory."""
        to = email.get("to", "")
        if not to:
            return
        # Check if recipient has a directory at ../to/ relative to agent_dir
        recipient_dir = self._agent_dir.parent / to
        if not recipient_dir.is_dir():
            return
        recipient_inbox = recipient_dir / "mailbox" / "inbox"
        recipient_inbox.mkdir(parents=True, exist_ok=True)
        target = recipient_inbox / f"{email['id']}.json"
        try:
            delivered = dict(email)
            delivered["status"] = "delivered"
            fd, tmp = tempfile.mkstemp(dir=str(recipient_inbox), suffix=".tmp")
            os.write(fd, json.dumps(delivered, indent=2, ensure_ascii=False).encode())
            os.fsync(fd)
            os.close(fd)
            os.replace(tmp, str(target))
            log.info("Local delivery: %s → %s", email["id"], to)
        except Exception as e:
            log.debug("Local delivery failed for %s: %s", to, e)

    def _check(self, args: dict) -> dict:
        folder = args.get("folder", "inbox")
        emails = self._list_emails(folder)
        limit = args.get("limit", 20)

        summaries = []
        unread_count = 0
        for email in emails[:limit]:
            email_id = email.get("id", "")
            is_read = email_id in self._read_ids
            if not is_read:
                unread_count += 1
            summaries.append({
                "id": email_id,
                "from": email.get("from", ""),
                "to": email.get("to", ""),
                "subject": email.get("subject", ""),
                "date": email.get("date", ""),
                "read": is_read,
                "thread_id": email.get("thread_id"),
            })

        return {
            "status": "ok",
            "folder": folder,
            "total": len(emails),
            "unread": unread_count,
            "emails": summaries,
        }

    def _read(self, args: dict) -> dict:
        email_id = args.get("id", "")
        if not email_id:
            return {"error": "id is required"}

        result = self._find_email(email_id)
        if result is None:
            return {"error": f"Email not found: {email_id}"}

        folder, path = result
        email = self._read_email_file(path)
        if email is None:
            return {"error": f"Failed to read email: {email_id}"}

        # Mark as read
        self._mark_read(email_id)

        return {"status": "ok", "folder": folder, "email": email}

    def _reply(self, args: dict) -> dict:
        email_id = args.get("id", "")
        body = args.get("body", "")
        if not email_id:
            return {"error": "id is required"}
        if not body:
            return {"error": "body is required"}

        result = self._find_email(email_id)
        if result is None:
            return {"error": f"Original email not found: {email_id}"}

        _folder, path = result
        original = self._read_email_file(path)
        if original is None:
            return {"error": f"Failed to read original email: {email_id}"}

        # Reply goes to the sender of the original
        reply_to = original.get("from", "")
        subject = original.get("subject", "")
        if not subject.startswith("Re: "):
            subject = f"Re: {subject}"

        return self._send({
            "to": reply_to,
            "subject": subject,
            "body": body,
            "in_reply_to": email_id,
            "thread_id": original.get("thread_id", email_id),
        })

    def _search(self, args: dict) -> dict:
        query = args.get("query", "")
        if not query:
            return {"error": "query is required"}
        folder = args.get("folder", "inbox")
        limit = args.get("limit", 20)

        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error as e:
            return {"error": f"Invalid regex: {e}"}

        emails = self._list_emails(folder)
        matches = []
        for email in emails:
            searchable = " ".join([
                email.get("from", ""),
                email.get("to", ""),
                email.get("subject", ""),
                email.get("body", ""),
            ])
            if pattern.search(searchable):
                matches.append({
                    "id": email.get("id"),
                    "from": email.get("from"),
                    "to": email.get("to"),
                    "subject": email.get("subject"),
                    "date": email.get("date"),
                })
                if len(matches) >= limit:
                    break

        return {"status": "ok", "total": len(matches), "matches": matches}

    def _archive(self, args: dict) -> dict:
        email_id = args.get("id", "")
        if not email_id:
            return {"error": "id is required"}

        result = self._find_email(email_id)
        if result is None:
            return {"error": f"Email not found: {email_id}"}

        folder, path = result
        if folder == "archive":
            return {"status": "already_archived", "id": email_id}

        email = self._read_email_file(path)
        if email is None:
            return {"error": f"Failed to read email: {email_id}"}

        # Write to archive, delete from original folder
        self._write_email("archive", email)
        self._delete_email_file(path)

        return {"status": "archived", "id": email_id, "from_folder": folder}

    def _delete(self, args: dict) -> dict:
        email_id = args.get("id", "")
        if not email_id:
            return {"error": "id is required"}

        result = self._find_email(email_id)
        if result is None:
            return {"error": f"Email not found: {email_id}"}

        folder, path = result
        self._delete_email_file(path)

        return {"status": "deleted", "id": email_id, "from_folder": folder}

    def _contacts(self) -> dict:
        return {"status": "ok", "contacts": self._load_contacts()}

    def _add_contact(self, args: dict) -> dict:
        name = args.get("name", "")
        address = args.get("address", "")
        if not name:
            return {"error": "name is required"}
        if not address:
            return {"error": "address is required"}

        contacts = self._load_contacts()
        contacts[name] = {
            "address": address,
            "added_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_contacts(contacts)
        return {"status": "added", "name": name}

    def _remove_contact(self, args: dict) -> dict:
        name = args.get("name", "")
        address = args.get("address", "")
        contacts = self._load_contacts()

        if name and name in contacts:
            del contacts[name]
            self._save_contacts(contacts)
            return {"status": "removed", "name": name}
        elif address:
            to_remove = [
                k for k, v in contacts.items()
                if v.get("address") == address
            ]
            for k in to_remove:
                del contacts[k]
            if to_remove:
                self._save_contacts(contacts)
                return {"status": "removed", "names": to_remove}

        return {"error": "Contact not found"}

    def _edit_contact(self, args: dict) -> dict:
        name = args.get("name", "")
        if not name:
            return {"error": "name is required"}

        contacts = self._load_contacts()
        if name not in contacts:
            return {"error": f"Contact not found: {name}"}

        new_name = args.get("new_name")
        new_address = args.get("new_address")

        if new_address:
            contacts[name]["address"] = new_address

        if new_name and new_name != name:
            contacts[new_name] = contacts.pop(name)
            name = new_name

        self._save_contacts(contacts)
        return {"status": "updated", "name": name}
