"""
Tests for the code library reuse system.

Run: python manage.py test apps.code_library
"""
from django.test import TestCase
from unittest.mock import patch, MagicMock

from . import constants
from .models import LibraryItem, ReuseLog
from .metrics import DuplicateDetector, ReuseMetrics
from .doctor import LibraryDoctor


class ConstantsTest(TestCase):
    """Test that all required constants are defined."""
    
    def test_thresholds_exist(self):
        """All threshold constants must be defined."""
        self.assertTrue(hasattr(constants, 'REUSE_THRESHOLD_HIGH'))
        self.assertTrue(hasattr(constants, 'REUSE_THRESHOLD_LOW'))
        self.assertTrue(hasattr(constants, 'GRAY_ZONE_MIN'))
        self.assertTrue(hasattr(constants, 'GRAY_ZONE_MAX'))
    
    def test_threshold_ordering(self):
        """High threshold must be greater than low."""
        self.assertGreater(
            constants.REUSE_THRESHOLD_HIGH,
            constants.REUSE_THRESHOLD_LOW
        )
    
    def test_gray_zone_valid(self):
        """Gray zone must be between low and high."""
        self.assertGreaterEqual(constants.GRAY_ZONE_MIN, constants.REUSE_THRESHOLD_LOW)
        self.assertLessEqual(constants.GRAY_ZONE_MAX, constants.REUSE_THRESHOLD_HIGH)


class DuplicateDetectorTest(TestCase):
    """Test duplicate detection."""
    
    def test_identical_code_is_duplicate(self):
        """Identical code should be detected as duplicate."""
        code = "function App() { return <div>Hello</div>; }"
        similarity = DuplicateDetector.compute_similarity(code, code)
        self.assertEqual(similarity, 1.0)
    
    def test_different_code_is_not_duplicate(self):
        """Completely different code should not be duplicate."""
        code1 = "function App() { return <div>Hello</div>; }"
        code2 = "const x = 1; const y = 2; console.log(x + y);"
        similarity = DuplicateDetector.compute_similarity(code1, code2)
        self.assertLess(similarity, 0.5)
    
    def test_hash_normalization(self):
        """Hash should be same for differently formatted but equivalent code."""
        code1 = "function App() { return 1; }"
        code2 = "function App()  {  return  1;  }"  # Extra spaces
        hash1 = DuplicateDetector.compute_code_hash(code1)
        hash2 = DuplicateDetector.compute_code_hash(code2)
        self.assertEqual(hash1, hash2)


class ReuseMetricsTest(TestCase):
    """Test reuse metrics tracking."""
    
    def test_log_decision_creates_record(self):
        """Logging a decision should create a ReuseLog record."""
        ReuseMetrics.log_decision(
            session_token='test-session-123',
            decision='reused',
            match_score=10.5,
            library_item_id='item-123',
            candidate_count=3,
        )
        
        log = ReuseLog.objects.get(session_token='test-session-123')
        self.assertEqual(log.decision, 'reused')
        self.assertEqual(log.match_score, 10.5)
        self.assertEqual(log.candidate_count, 3)
    
    def test_reuse_ratio_calculation(self):
        """Reuse ratio should be calculated correctly."""
        # Create test data
        for i in range(3):
            ReuseLog.objects.create(
                session_token=f'reused-{i}',
                decision='reused',
                match_score=10.0,
            )
        for i in range(7):
            ReuseLog.objects.create(
                session_token=f'generated-{i}',
                decision='generated',
                match_score=2.0,
            )
        
        stats = ReuseMetrics.get_reuse_ratio(days=7)
        self.assertEqual(stats['reused'], 3)
        self.assertEqual(stats['generated'], 7)
        self.assertEqual(stats['total'], 10)
        self.assertAlmostEqual(stats['ratio'], 0.3, places=2)


class LibraryDoctorTest(TestCase):
    """Test doctor health checks."""
    
    def test_doctor_runs_without_error(self):
        """Doctor should run all checks without error."""
        doctor = LibraryDoctor()
        results = doctor.run_all_checks()
        
        self.assertIn('total_checks', results)
        self.assertIn('passed', results)
        self.assertIn('failed', results)
        self.assertIn('checks', results)
        self.assertIn('healthy', results)
    
    def test_threshold_check_passes(self):
        """Threshold configuration check should pass."""
        doctor = LibraryDoctor()
        doctor._check_thresholds_configured()
        
        check = doctor.checks[0]
        self.assertTrue(check.passed)
        self.assertEqual(check.name, 'thresholds_configured')


class RetrievalDeterminismTest(TestCase):
    """Test that retrieval is deterministic."""
    
    def test_same_query_same_results(self):
        """Same query should always return same ranked results."""
        # Create some library items
        LibraryItem.objects.create(
            name="Salon Hero",
            description="A hero section for salons",
            code="function SalonHero() { return <div>Salon</div>; }",
            keywords="salon, hero, beauty",
            tags=["salon", "hero"],
            is_active=True,
            is_approved=True,
            quality_score=0.8,
        )
        
        from .doctor import RetrievalDiagnostics
        
        result1 = RetrievalDiagnostics.diagnose_query("I need a salon website")
        result2 = RetrievalDiagnostics.diagnose_query("I need a salon website")
        
        ids1 = [c['item_id'] for c in result1.get('top_candidates', [])]
        ids2 = [c['item_id'] for c in result2.get('top_candidates', [])]
        
        self.assertEqual(ids1, ids2, "Same query should return same results")
