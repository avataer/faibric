"""
Management command: reuse_stats

Show reuse statistics and metrics.

Usage:
    python manage.py reuse_stats
    python manage.py reuse_stats --days 30
"""
from django.core.management.base import BaseCommand
import json

from apps.code_library.metrics import ReuseMetrics, DuplicateDetector


class Command(BaseCommand):
    help = 'Show reuse statistics and metrics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', '-d',
            type=int,
            default=7,
            help='Number of days to analyze',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output as JSON',
        )

    def handle(self, *args, **options):
        days = options['days']
        
        stats = ReuseMetrics.get_reuse_ratio(days=days)
        duplicates = DuplicateDetector.find_duplicates()
        
        if options['json']:
            self.stdout.write(json.dumps({
                'reuse_stats': stats,
                'duplicate_count': len(duplicates),
            }, indent=2))
            return
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"  REUSE STATISTICS (Last {days} days)")
        self.stdout.write("=" * 60 + "\n")
        
        self.stdout.write(f"  Total builds: {stats.get('total', 0)}")
        self.stdout.write(f"  Reused from library: {stats.get('reused', 0)}")
        self.stdout.write(f"  Generated new: {stats.get('generated', 0)}")
        self.stdout.write(f"  Gray zone: {stats.get('gray_zone', 0)}")
        self.stdout.write("")
        
        ratio = stats.get('ratio', 0)
        if ratio >= 0.5:
            style = self.style.SUCCESS
        elif ratio >= 0.3:
            style = self.style.WARNING
        else:
            style = self.style.ERROR
        
        self.stdout.write(style(f"  REUSE RATIO: {ratio:.1%}"))
        self.stdout.write("")
        
        self.stdout.write("=" * 60)
        self.stdout.write("  DUPLICATE DETECTION")
        self.stdout.write("=" * 60 + "\n")
        
        if not duplicates:
            self.stdout.write(self.style.SUCCESS("  No near-duplicates found"))
        else:
            self.stdout.write(self.style.WARNING(f"  Found {len(duplicates)} near-duplicate pairs:"))
            for d in duplicates[:5]:
                self.stdout.write(f"    - {d[3]} <-> {d[4]} ({d[2]:.0%} similar)")
        
        self.stdout.write("\n" + "=" * 60 + "\n")
