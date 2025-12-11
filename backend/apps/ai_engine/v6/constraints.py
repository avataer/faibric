"""
Constraint loader and manager for code generation.
Loads constraints from MD files and applies them during generation.
"""
import logging
import os
import re
from pathlib import Path
from typing import List, Optional

from django.conf import settings

from apps.code_library.models import Constraint

logger = logging.getLogger(__name__)


class ConstraintLoader:
    """
    Loads and parses constraints from Markdown files.
    """
    
    def __init__(self):
        self.constraints_dir = getattr(
            settings,
            'CONSTRAINTS_DIR',
            Path(settings.BASE_DIR).parent / 'constraints'
        )
    
    def load_from_file(self, file_path: str) -> dict:
        """
        Load constraints from a Markdown file.
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            return self.parse_markdown(content, file_path)
        except Exception as e:
            logger.error(f"Error loading constraint file {file_path}: {e}")
            return {'error': str(e)}
    
    def parse_markdown(self, content: str, source: str = '') -> dict:
        """
        Parse Markdown content and extract constraint rules.
        """
        result = {
            'source': source,
            'title': '',
            'description': '',
            'rules': [],
            'examples': [],
            'applies_to': [],
        }
        
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            # Extract title from first heading
            if line.startswith('# ') and not result['title']:
                result['title'] = line[2:].strip()
                continue
            
            # Check for section headers
            if line.startswith('## '):
                # Save previous section
                if current_section:
                    self._process_section(result, current_section, current_content)
                
                current_section = line[3:].strip().lower()
                current_content = []
                continue
            
            current_content.append(line)
        
        # Process last section
        if current_section:
            self._process_section(result, current_section, current_content)
        
        # Extract rules from bullet points throughout the content
        result['rules'].extend(self._extract_rules(content))
        
        return result
    
    def _process_section(
        self,
        result: dict,
        section: str,
        content: List[str]
    ):
        """Process a markdown section."""
        text = '\n'.join(content).strip()
        
        if 'description' in section or 'overview' in section:
            result['description'] = text
        elif 'rule' in section:
            result['rules'].extend(self._extract_rules(text))
        elif 'example' in section:
            result['examples'].append(text)
        elif 'applies' in section or 'scope' in section:
            result['applies_to'] = [
                item.strip().lower()
                for item in text.split(',')
                if item.strip()
            ]
    
    def _extract_rules(self, content: str) -> List[str]:
        """Extract rules from bullet points and numbered lists."""
        rules = []
        
        # Match bullet points (-, *, •) and numbered lists
        pattern = r'^\s*[-*•]\s+(.+)$|^\s*\d+\.\s+(.+)$'
        
        for line in content.split('\n'):
            match = re.match(pattern, line)
            if match:
                rule_text = match.group(1) or match.group(2)
                if rule_text and len(rule_text) > 10:  # Skip very short items
                    rules.append(rule_text.strip())
        
        return rules
    
    def load_all_constraints(self) -> List[dict]:
        """
        Load all constraint files from the constraints directory.
        """
        constraints = []
        
        if not os.path.isdir(self.constraints_dir):
            logger.warning(f"Constraints directory not found: {self.constraints_dir}")
            return constraints
        
        for filename in os.listdir(self.constraints_dir):
            if filename.endswith('.md'):
                file_path = os.path.join(self.constraints_dir, filename)
                constraint = self.load_from_file(file_path)
                
                if 'error' not in constraint:
                    constraint['slug'] = filename[:-3]  # Remove .md
                    constraints.append(constraint)
        
        return constraints
    
    def sync_to_database(self, tenant_id: str = None) -> dict:
        """
        Sync constraint files to the database.
        """
        constraints = self.load_all_constraints()
        
        created = 0
        updated = 0
        
        for constraint_data in constraints:
            slug = constraint_data.get('slug', '')
            
            # Determine constraint type from filename
            constraint_type = 'custom'
            for ctype in ['security', 'styling', 'architecture', 'api', 'database', 'react', 'python']:
                if ctype in slug.lower():
                    constraint_type = ctype
                    break
            
            obj, was_created = Constraint.objects.update_or_create(
                slug=slug,
                tenant_id=tenant_id,
                defaults={
                    'name': constraint_data.get('title', slug),
                    'constraint_type': constraint_type,
                    'content': open(
                        os.path.join(self.constraints_dir, f"{slug}.md")
                    ).read() if os.path.exists(
                        os.path.join(self.constraints_dir, f"{slug}.md")
                    ) else '',
                    'rules': constraint_data.get('rules', []),
                    'applies_to': constraint_data.get('applies_to', []),
                }
            )
            
            if was_created:
                created += 1
            else:
                updated += 1
        
        return {
            'created': created,
            'updated': updated,
            'total': len(constraints),
        }


class ConstraintManager:
    """
    Manages constraint application during code generation.
    """
    
    def __init__(self, tenant_id: str = None):
        self.tenant_id = tenant_id
        self.loader = ConstraintLoader()
    
    def get_applicable_constraints(
        self,
        language: str = None,
        item_type: str = None,
        constraint_types: List[str] = None
    ) -> List[Constraint]:
        """
        Get constraints that apply to the given context.
        """
        from django.db.models import Q
        
        qs = Constraint.objects.filter(is_active=True)
        
        # Filter by tenant or global
        if self.tenant_id:
            qs = qs.filter(
                Q(tenant_id=self.tenant_id) | Q(tenant__isnull=True)
            )
        else:
            qs = qs.filter(tenant__isnull=True)
        
        # Filter by constraint types
        if constraint_types:
            qs = qs.filter(constraint_type__in=constraint_types)
        
        # Get all and filter by applies_to
        constraints = list(qs.order_by('-priority'))
        
        if language or item_type:
            filtered = []
            for constraint in constraints:
                applies_to = constraint.applies_to or []
                
                # If no applies_to specified, it applies to all
                if not applies_to:
                    filtered.append(constraint)
                    continue
                
                # Check if language or item_type matches
                if language and language.lower() in [a.lower() for a in applies_to]:
                    filtered.append(constraint)
                elif item_type and item_type.lower() in [a.lower() for a in applies_to]:
                    filtered.append(constraint)
            
            constraints = filtered
        
        return constraints
    
    def format_constraints_for_prompt(
        self,
        constraints: List[Constraint]
    ) -> str:
        """
        Format constraints for inclusion in an LLM prompt.
        """
        if not constraints:
            return ""
        
        sections = []
        sections.append("## Constraints and Requirements\n")
        sections.append("You MUST follow these constraints when generating code:\n")
        
        for constraint in constraints:
            sections.append(f"\n### {constraint.name}")
            
            # Add rules
            for rule in (constraint.rules or []):
                sections.append(f"- {rule}")
        
        return '\n'.join(sections)
    
    def get_constraint_prompt(
        self,
        language: str = None,
        item_type: str = None,
        constraint_types: List[str] = None
    ) -> str:
        """
        Get formatted constraint prompt for the given context.
        """
        constraints = self.get_applicable_constraints(
            language=language,
            item_type=item_type,
            constraint_types=constraint_types
        )
        
        return self.format_constraints_for_prompt(constraints)
    
    def validate_code_against_constraints(
        self,
        code: str,
        language: str,
        constraints: List[Constraint] = None
    ) -> dict:
        """
        Validate code against constraints.
        Returns validation results.
        """
        if constraints is None:
            constraints = self.get_applicable_constraints(language=language)
        
        violations = []
        warnings = []
        
        for constraint in constraints:
            for rule in (constraint.rules or []):
                # Simple pattern-based checks
                violation = self._check_rule(code, rule, language)
                if violation:
                    if 'MUST NOT' in rule.upper() or 'DO NOT' in rule.upper():
                        violations.append({
                            'constraint': constraint.name,
                            'rule': rule,
                            'message': violation,
                        })
                    else:
                        warnings.append({
                            'constraint': constraint.name,
                            'rule': rule,
                            'message': violation,
                        })
        
        return {
            'valid': len(violations) == 0,
            'violations': violations,
            'warnings': warnings,
        }
    
    def _check_rule(self, code: str, rule: str, language: str) -> Optional[str]:
        """
        Check a single rule against code.
        Returns violation message or None.
        """
        rule_lower = rule.lower()
        
        # Security checks
        if 'no eval' in rule_lower or "don't use eval" in rule_lower:
            if 'eval(' in code:
                return "Code contains eval() which is forbidden"
        
        if 'sanitize' in rule_lower and 'input' in rule_lower:
            if 'innerHTML' in code and 'sanitize' not in code.lower():
                return "Code uses innerHTML without apparent sanitization"
        
        if 'no external api' in rule_lower or 'use gateway' in rule_lower:
            external_patterns = ['fetch(', 'axios.', 'http.get', 'requests.get']
            if any(p in code for p in external_patterns):
                if 'gateway' not in code.lower() and 'api/' not in code:
                    return "Code may be making direct external API calls"
        
        # React checks
        if language in ['typescript', 'javascript']:
            if 'hooks only' in rule_lower or 'no class component' in rule_lower:
                if 'extends React.Component' in code or 'extends Component' in code:
                    return "Code uses class components instead of hooks"
        
        # Style checks
        if 'inline styles' in rule_lower:
            if 'className=' in code and 'style=' not in code:
                if '.css' not in code and 'styled' not in code.lower():
                    pass  # Could be a warning but not definitive
        
        return None


def load_constraints_sync(
    language: str = None,
    item_type: str = None,
    tenant_id: str = None
) -> str:
    """
    Synchronous helper to load constraints for a prompt.
    """
    manager = ConstraintManager(tenant_id)
    return manager.get_constraint_prompt(language=language, item_type=item_type)







