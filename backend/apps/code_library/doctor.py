"""
Code Library Doctor - Health checks and diagnostics.

Run: python manage.py reuse_doctor
"""
import logging
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass

from . import constants
from .metrics import ReuseMetrics, DuplicateDetector, RetrievalDiagnostics

logger = logging.getLogger(__name__)


@dataclass
class DoctorCheck:
    name: str
    passed: bool
    message: str
    severity: str  # 'error', 'warning', 'info'
    fix_suggestion: str = None


class LibraryDoctor:
    """
    Health checks for the code library system.
    """
    
    def __init__(self):
        self.checks: List[DoctorCheck] = []
    
    def run_all_checks(self) -> Dict:
        """Run all health checks and return report."""
        self.checks = []
        
        self._check_thresholds_configured()
        self._check_reuse_ratio()
        self._check_near_duplicates()
        self._check_unapproved_items()
        self._check_versioning()
        self._check_items_without_keywords()
        self._check_retrieval_determinism()
        
        passed = sum(1 for c in self.checks if c.passed)
        failed = len(self.checks) - passed
        
        return {
            'total_checks': len(self.checks),
            'passed': passed,
            'failed': failed,
            'checks': [
                {
                    'name': c.name,
                    'passed': c.passed,
                    'message': c.message,
                    'severity': c.severity,
                    'fix': c.fix_suggestion,
                }
                for c in self.checks
            ],
            'healthy': failed == 0,
        }
    
    def _check_thresholds_configured(self):
        """Verify thresholds are in constants module."""
        try:
            assert hasattr(constants, 'REUSE_THRESHOLD_HIGH')
            assert hasattr(constants, 'REUSE_THRESHOLD_LOW')
            assert hasattr(constants, 'GRAY_ZONE_MIN')
            assert hasattr(constants, 'GRAY_ZONE_MAX')
            assert constants.REUSE_THRESHOLD_HIGH > constants.REUSE_THRESHOLD_LOW
            
            self.checks.append(DoctorCheck(
                name='thresholds_configured',
                passed=True,
                message=f"Thresholds configured: HIGH={constants.REUSE_THRESHOLD_HIGH}, LOW={constants.REUSE_THRESHOLD_LOW}",
                severity='info',
            ))
        except AssertionError as e:
            self.checks.append(DoctorCheck(
                name='thresholds_configured',
                passed=False,
                message=f"Threshold configuration error: {e}",
                severity='error',
                fix_suggestion="Check constants.py for proper threshold values",
            ))
    
    def _check_reuse_ratio(self):
        """Check reuse ratio is healthy."""
        stats = ReuseMetrics.get_reuse_ratio(days=7)
        
        if stats.get('error'):
            self.checks.append(DoctorCheck(
                name='reuse_ratio',
                passed=False,
                message=f"Could not compute reuse ratio: {stats['error']}",
                severity='warning',
                fix_suggestion="Ensure ReuseLog model exists and is migrated",
            ))
            return
        
        ratio = stats.get('ratio', 0)
        total = stats.get('total', 0)
        
        if total < 5:
            self.checks.append(DoctorCheck(
                name='reuse_ratio',
                passed=True,
                message=f"Insufficient data: only {total} builds in last 7 days",
                severity='info',
            ))
        elif ratio >= 0.3:
            self.checks.append(DoctorCheck(
                name='reuse_ratio',
                passed=True,
                message=f"Healthy reuse ratio: {ratio:.1%} ({stats['reused']}/{total})",
                severity='info',
            ))
        else:
            self.checks.append(DoctorCheck(
                name='reuse_ratio',
                passed=False,
                message=f"Low reuse ratio: {ratio:.1%} ({stats['reused']}/{total})",
                severity='warning',
                fix_suggestion="Add more approved components to library or lower threshold",
            ))
    
    def _check_near_duplicates(self):
        """Check for near-duplicate items in library."""
        duplicates = DuplicateDetector.find_duplicates()
        
        if not duplicates:
            self.checks.append(DoctorCheck(
                name='near_duplicates',
                passed=True,
                message="No near-duplicates detected",
                severity='info',
            ))
        else:
            dup_summary = ', '.join([
                f"{d[3]} <-> {d[4]} ({d[2]:.0%})"
                for d in duplicates[:3]
            ])
            self.checks.append(DoctorCheck(
                name='near_duplicates',
                passed=False,
                message=f"Found {len(duplicates)} near-duplicate pairs: {dup_summary}",
                severity='warning',
                fix_suggestion="Review and merge or deprecate duplicate items",
            ))
    
    def _check_unapproved_items(self):
        """Check for items awaiting approval."""
        from .models import LibraryItem
        
        unapproved = LibraryItem.objects.filter(is_approved=False).count()
        
        if unapproved == 0:
            self.checks.append(DoctorCheck(
                name='unapproved_items',
                passed=True,
                message="No items pending approval",
                severity='info',
            ))
        elif unapproved <= 5:
            self.checks.append(DoctorCheck(
                name='unapproved_items',
                passed=True,
                message=f"{unapproved} items pending approval",
                severity='info',
            ))
        else:
            self.checks.append(DoctorCheck(
                name='unapproved_items',
                passed=False,
                message=f"{unapproved} items pending approval - backlog growing",
                severity='warning',
                fix_suggestion="Review pending items at /admin/code_library/libraryitem/",
            ))
    
    def _check_versioning(self):
        """Check versioning compliance."""
        from .models import LibraryItem
        
        # Check if items have proper version format (not enforced yet)
        items_count = LibraryItem.objects.filter(is_active=True).count()
        
        self.checks.append(DoctorCheck(
            name='versioning',
            passed=True,
            message=f"{items_count} active items in library",
            severity='info',
        ))
    
    def _check_items_without_keywords(self):
        """Check for items without proper keywords/tags."""
        from .models import LibraryItem
        
        items = LibraryItem.objects.filter(
            is_active=True,
            is_approved=True,
        )
        
        no_keywords = items.filter(keywords='').count()
        no_tags = items.filter(tags=[]).count()
        
        if no_keywords == 0 and no_tags == 0:
            self.checks.append(DoctorCheck(
                name='items_searchable',
                passed=True,
                message="All approved items have keywords and tags",
                severity='info',
            ))
        else:
            self.checks.append(DoctorCheck(
                name='items_searchable',
                passed=False,
                message=f"{no_keywords} items without keywords, {no_tags} without tags",
                severity='warning',
                fix_suggestion="Add keywords/tags to improve retrieval quality",
            ))
    
    def _check_retrieval_determinism(self):
        """Verify retrieval is deterministic for a test query."""
        # Run same query twice, results should be identical
        test_query = "I am a hair salon"
        
        try:
            result1 = RetrievalDiagnostics.diagnose_query(test_query, top_k=3)
            result2 = RetrievalDiagnostics.diagnose_query(test_query, top_k=3)
            
            ids1 = [c['item_id'] for c in result1.get('top_candidates', [])]
            ids2 = [c['item_id'] for c in result2.get('top_candidates', [])]
            
            if ids1 == ids2:
                self.checks.append(DoctorCheck(
                    name='retrieval_determinism',
                    passed=True,
                    message="Retrieval is deterministic (same query → same results)",
                    severity='info',
                ))
            else:
                self.checks.append(DoctorCheck(
                    name='retrieval_determinism',
                    passed=False,
                    message="Retrieval is non-deterministic! Results differ for same query",
                    severity='error',
                    fix_suggestion="Check for random ordering in search logic",
                ))
        except Exception as e:
            self.checks.append(DoctorCheck(
                name='retrieval_determinism',
                passed=False,
                message=f"Could not test retrieval: {e}",
                severity='warning',
            ))


def run_doctor() -> Dict:
    """Run all doctor checks and return results."""
    doctor = LibraryDoctor()
    return doctor.run_all_checks()


def diagnose(query: str) -> Dict:
    """Diagnose why a query returns certain results."""
    return RetrievalDiagnostics.diagnose_query(query)
