"""
Management command: reuse_diagnose

Diagnose why a query returns certain library matches.

Usage:
    python manage.py reuse_diagnose "I am a hair salon"
"""
from django.core.management.base import BaseCommand
import json

from apps.code_library.doctor import diagnose


class Command(BaseCommand):
    help = 'Diagnose library retrieval for a given query'

    def add_arguments(self, parser):
        parser.add_argument(
            'query',
            type=str,
            help='The query to diagnose',
        )
        parser.add_argument(
            '--top-k', '-k',
            type=int,
            default=5,
            help='Number of top candidates to show',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output as JSON',
        )

    def handle(self, *args, **options):
        query = options['query']
        top_k = options['top_k']
        
        self.stdout.write(f"\nDiagnosing query: \"{query}\"\n")
        
        results = diagnose(query)
        
        if options['json']:
            self.stdout.write(json.dumps(results, indent=2, default=str))
            return
        
        self.stdout.write("=" * 60)
        self.stdout.write("  EXTRACTED REQUIREMENTS")
        self.stdout.write("=" * 60)
        reqs = results.get('extracted_requirements', {})
        self.stdout.write(f"  Site type: {reqs.get('site_type', 'N/A')}")
        self.stdout.write(f"  Industry: {reqs.get('industry', 'N/A')}")
        self.stdout.write(f"  Sections: {', '.join(reqs.get('sections_needed', []))}")
        self.stdout.write(f"  Features: {', '.join(reqs.get('features', []))}")
        self.stdout.write("")
        
        self.stdout.write("=" * 60)
        self.stdout.write("  SEARCH KEYWORDS")
        self.stdout.write("=" * 60)
        self.stdout.write(f"  {results.get('search_keywords', [])}")
        self.stdout.write("")
        
        self.stdout.write("=" * 60)
        self.stdout.write("  THRESHOLDS")
        self.stdout.write("=" * 60)
        thresholds = results.get('thresholds', {})
        self.stdout.write(f"  Reuse (confident): >= {thresholds.get('reuse_high', 'N/A')}")
        self.stdout.write(f"  Gray zone: {thresholds.get('gray_zone', 'N/A')}")
        self.stdout.write(f"  Generate new: < {thresholds.get('reuse_low', 'N/A')}")
        self.stdout.write("")
        
        self.stdout.write("=" * 60)
        self.stdout.write(f"  TOP {top_k} CANDIDATES")
        self.stdout.write("=" * 60)
        
        candidates = results.get('top_candidates', [])[:top_k]
        
        if not candidates:
            self.stdout.write(self.style.WARNING("  No candidates found"))
        else:
            for i, c in enumerate(candidates, 1):
                self.stdout.write(f"\n  #{i}: {c['item_name']}")
                self.stdout.write(f"      Score: {c['total_score']:.1f}")
                self.stdout.write(f"      Quality: {c['quality_score']:.0%}")
                self.stdout.write(f"      Usage count: {c['usage_count']}")
                
                if c.get('keyword_matches'):
                    self.stdout.write(f"      Keyword matches: {', '.join(c['keyword_matches'])}")
                if c.get('tag_matches'):
                    self.stdout.write(f"      Tag matches: {', '.join(c['tag_matches'])}")
                
                self.stdout.write("      Score breakdown:")
                for comp in c.get('score_components', []):
                    self.stdout.write(f"        {comp}")
        
        self.stdout.write("")
        self.stdout.write("=" * 60)
        decision = results.get('decision', 'UNKNOWN')
        if 'REUSE' in decision:
            self.stdout.write(self.style.SUCCESS(f"  DECISION: {decision}"))
        elif 'GRAY' in decision:
            self.stdout.write(self.style.WARNING(f"  DECISION: {decision}"))
        else:
            self.stdout.write(self.style.NOTICE(f"  DECISION: {decision}"))
        self.stdout.write("=" * 60 + "\n")
