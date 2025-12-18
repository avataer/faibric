"""
Management command: reuse_doctor

Run health checks on the code library reuse system.

Usage:
    python manage.py reuse_doctor
    python manage.py reuse_doctor --verbose
"""
from django.core.management.base import BaseCommand
import json

from apps.code_library.doctor import run_doctor


class Command(BaseCommand):
    help = 'Run health checks on the code library reuse system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed output with fix suggestions',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output as JSON',
        )

    def handle(self, *args, **options):
        results = run_doctor()
        
        if options['json']:
            self.stdout.write(json.dumps(results, indent=2))
            return
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("  CODE LIBRARY REUSE SYSTEM - HEALTH CHECK")
        self.stdout.write("=" * 60 + "\n")
        
        for check in results['checks']:
            if check['passed']:
                status = self.style.SUCCESS('✓ PASS')
            else:
                if check['severity'] == 'error':
                    status = self.style.ERROR('✗ FAIL')
                else:
                    status = self.style.WARNING('⚠ WARN')
            
            self.stdout.write(f"{status}  {check['name']}")
            self.stdout.write(f"        {check['message']}")
            
            if options['detailed'] and check.get('fix'):
                self.stdout.write(self.style.NOTICE(f"        FIX: {check['fix']}"))
            
            self.stdout.write("")
        
        self.stdout.write("=" * 60)
        summary = f"  {results['passed']}/{results['total_checks']} checks passed"
        if results['healthy']:
            self.stdout.write(self.style.SUCCESS(summary + " - HEALTHY"))
        else:
            self.stdout.write(self.style.ERROR(summary + " - NEEDS ATTENTION"))
        self.stdout.write("=" * 60 + "\n")
