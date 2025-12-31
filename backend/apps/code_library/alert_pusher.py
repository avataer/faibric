"""
ALERT PUSHER
============

Actually PUSHES alerts to the owner, not just stores them.

Methods:
1. Updates ALERTS.md in repo root - visible in file explorer/git
2. Writes to a watched file that can trigger notifications
3. Sends to configured webhook immediately
"""

import os
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to alerts file - try multiple locations
def get_alerts_file():
    """Get the path to ALERTS.md, trying multiple locations."""
    # In Docker container
    docker_path = Path("/app/ALERTS.md")
    if docker_path.parent.exists():
        return docker_path
    
    # Local development
    local_path = Path(__file__).parent.parent.parent.parent / "ALERTS.md"
    return local_path

ALERTS_FILE = get_alerts_file()


def push_alert(
    alert_type: str,
    title: str,
    message: str,
    entry_id: str = ""
):
    """
    Push an alert so the owner SEES it without checking anything.
    
    Updates ALERTS.md in the repo root - this file will:
    - Show up in git status
    - Be visible in file explorer
    - Appear in Cursor's file tree
    """
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Format the alert
    alert_content = f"""
## [{timestamp}] {title}

**Type:** {alert_type}  
**ID:** {entry_id}

{message}

---
"""
    
    # Read existing alerts
    existing = ""
    if ALERTS_FILE.exists():
        existing = ALERTS_FILE.read_text()
    
    # Prepend new alert (newest first)
    header = """# FAIBRIC ALERTS

This file is automatically updated when issues are detected.
Check this file for new alerts.

---
"""
    
    # Keep only last 20 alerts to prevent file from growing forever
    alerts_section = existing.replace(header, "")
    alert_blocks = alerts_section.split("\n---\n")
    alert_blocks = [b for b in alert_blocks if b.strip()][:19]  # Keep last 19
    
    new_content = header + alert_content + "\n---\n".join(alert_blocks)
    
    # Write to file
    try:
        ALERTS_FILE.write_text(new_content)
        logger.info(f"[ALERT PUSHER] Updated {ALERTS_FILE}")
    except Exception as e:
        logger.error(f"[ALERT PUSHER] Failed to write: {e}")
    
    # Also try to send webhook if configured
    _send_webhook(alert_type, title, message, entry_id)


def _send_webhook(alert_type: str, title: str, message: str, entry_id: str):
    """Send to webhook if configured."""
    import requests
    
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL') or os.environ.get('INSTRUCTION_ALERT_WEBHOOK')
    
    if not webhook_url:
        return
    
    try:
        payload = {
            "text": f"[{alert_type.upper()}] {title}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{title}*\n```{message[:500]}```"
                    }
                }
            ]
        }
        
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception as e:
        logger.warning(f"[ALERT PUSHER] Webhook failed: {e}")


def get_unread_count() -> int:
    """Get count of alerts in the file."""
    if not ALERTS_FILE.exists():
        return 0
    
    content = ALERTS_FILE.read_text()
    return content.count("## [")


def clear_alerts():
    """Clear all alerts."""
    header = """# FAIBRIC ALERTS

This file is automatically updated when issues are detected.
Check this file for new alerts.

---

No current alerts.
"""
    ALERTS_FILE.write_text(header)

