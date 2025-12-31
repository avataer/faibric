"""
INSTRUCTION-BASED SOLUTION LOG
==============================

Since we can't truly prevent instruction-based solutions from being created,
we LOG every instance so the owner can see them and take action.

This creates a permanent, visible record of all instruction-based patterns
detected in the codebase.
"""

import logging
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class InstructionSolutionEntry:
    """A logged instruction-based solution."""
    id: str
    detected_at: datetime
    file_path: str
    line_number: int
    instruction_text: str
    missing_enforcement: str
    status: str  # 'pending', 'fixed', 'acknowledged'
    fixed_by: Optional[str] = None
    fixed_at: Optional[datetime] = None


class InstructionSolutionLog:
    """
    Persistent log of all instruction-based solutions detected.
    
    This is the VISIBILITY layer - since we can't prevent instructions,
    we make them VISIBLE so the owner can act on them.
    """
    
    def __init__(self):
        self._entries: List[InstructionSolutionEntry] = []
        self._load_from_db()
    
    def _load_from_db(self):
        """Load existing entries from database."""
        try:
            from .models import InstructionSolutionRecord
            for record in InstructionSolutionRecord.objects.filter(status='pending'):
                self._entries.append(InstructionSolutionEntry(
                    id=str(record.id),
                    detected_at=record.detected_at,
                    file_path=record.file_path,
                    line_number=record.line_number,
                    instruction_text=record.instruction_text,
                    missing_enforcement=record.missing_enforcement,
                    status=record.status,
                    fixed_by=record.fixed_by,
                    fixed_at=record.fixed_at
                ))
        except Exception:
            pass  # Model might not exist yet
    
    def log_instruction_solution(
        self,
        file_path: str,
        line_number: int,
        instruction_text: str,
        missing_enforcement: str
    ) -> str:
        """
        Log an instruction-based solution.
        
        Returns the entry ID.
        """
        import uuid
        
        entry_id = str(uuid.uuid4())[:8]
        now = datetime.now()
        
        entry = InstructionSolutionEntry(
            id=entry_id,
            detected_at=now,
            file_path=file_path,
            line_number=line_number,
            instruction_text=instruction_text[:500],
            missing_enforcement=missing_enforcement,
            status='pending'
        )
        
        self._entries.append(entry)
        self._save_to_db(entry)
        
        # Log prominently
        logger.warning(
            f"[INSTRUCTION SOLUTION DETECTED] ID={entry_id}\n"
            f"  File: {file_path}:{line_number}\n"
            f"  Text: {instruction_text[:100]}...\n"
            f"  Missing: {missing_enforcement}\n"
            f"  Status: PENDING - needs code enforcement"
        )
        
        # Send notification
        try:
            from .instruction_notifier import notify_instruction_solution
            notify_instruction_solution(
                entry_id=entry_id,
                file_path=file_path,
                line_number=line_number,
                instruction_text=instruction_text,
                missing_enforcement=missing_enforcement
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
        
        # PUSH alert to ALERTS.md file (owner sees this without checking anything)
        try:
            from .alert_pusher import push_alert
            push_alert(
                alert_type="instruction_solution",
                title=f"Instruction-based solution: {file_path}:{line_number}",
                message=f"Instruction:\n{instruction_text}\n\nMissing:\n{missing_enforcement}",
                entry_id=entry_id
            )
        except Exception as e:
            logger.error(f"Failed to push alert: {e}")
        
        return entry_id
    
    def _save_to_db(self, entry: InstructionSolutionEntry):
        """Save entry to database."""
        try:
            from .models import InstructionSolutionRecord
            InstructionSolutionRecord.objects.create(
                id=entry.id,
                detected_at=entry.detected_at,
                file_path=entry.file_path,
                line_number=entry.line_number,
                instruction_text=entry.instruction_text,
                missing_enforcement=entry.missing_enforcement,
                status=entry.status
            )
        except Exception as e:
            logger.error(f"Failed to save instruction log: {e}")
    
    def get_pending(self) -> List[InstructionSolutionEntry]:
        """Get all pending (unfixed) instruction solutions."""
        return [e for e in self._entries if e.status == 'pending']
    
    def get_all(self) -> List[InstructionSolutionEntry]:
        """Get all logged instruction solutions."""
        return self._entries
    
    def mark_fixed(self, entry_id: str, fixed_by: str):
        """Mark an entry as fixed."""
        for entry in self._entries:
            if entry.id == entry_id:
                entry.status = 'fixed'
                entry.fixed_by = fixed_by
                entry.fixed_at = datetime.now()
                self._update_db(entry)
                logger.info(f"[INSTRUCTION LOG] Entry {entry_id} marked as fixed by {fixed_by}")
                return True
        return False
    
    def _update_db(self, entry: InstructionSolutionEntry):
        """Update entry in database."""
        try:
            from .models import InstructionSolutionRecord
            InstructionSolutionRecord.objects.filter(id=entry.id).update(
                status=entry.status,
                fixed_by=entry.fixed_by,
                fixed_at=entry.fixed_at
            )
        except Exception:
            pass
    
    def get_summary(self) -> str:
        """Get a summary for display."""
        pending = self.get_pending()
        total = len(self._entries)
        
        lines = [
            "=" * 60,
            "INSTRUCTION-BASED SOLUTIONS LOG",
            "=" * 60,
            f"Total logged: {total}",
            f"Pending (need enforcement): {len(pending)}",
            "",
        ]
        
        if pending:
            lines.append("PENDING ITEMS:")
            lines.append("-" * 40)
            for entry in pending[:10]:  # Show first 10
                lines.append(f"[{entry.id}] {entry.file_path}:{entry.line_number}")
                lines.append(f"  {entry.instruction_text[:60]}...")
                lines.append(f"  Missing: {entry.missing_enforcement}")
                lines.append("")
        else:
            lines.append("No pending instruction-based solutions.")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# Global instance
_log = None


def get_instruction_log() -> InstructionSolutionLog:
    """Get the global instruction solution log."""
    global _log
    if _log is None:
        _log = InstructionSolutionLog()
    return _log


def log_instruction_solution(
    file_path: str,
    line_number: int,
    instruction_text: str,
    missing_enforcement: str
) -> str:
    """Log an instruction-based solution."""
    return get_instruction_log().log_instruction_solution(
        file_path, line_number, instruction_text, missing_enforcement
    )


def get_pending_instructions() -> List[InstructionSolutionEntry]:
    """Get all pending instruction-based solutions."""
    return get_instruction_log().get_pending()


def get_instruction_log_summary() -> str:
    """Get summary of instruction log."""
    return get_instruction_log().get_summary()

