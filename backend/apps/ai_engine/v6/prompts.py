"""
Enhanced prompts for research-driven code generation.
"""


class PromptBuilder:
    """
    Builds prompts for code generation with research and constraints.
    """
    
    def get_system_prompt(self, language: str) -> str:
        """
        Get the system prompt for code generation.
        """
        language_specific = self._get_language_guidelines(language)
        
        return f"""You are an expert code generator. Your task is to generate high-quality, 
production-ready code based on the user's requirements.

## Guidelines
1. Write clean, well-documented code
2. Follow best practices and modern patterns
3. Include error handling where appropriate
4. Make code modular and reusable
5. Add helpful comments for complex logic

{language_specific}

## Output Format
- Provide the code in a markdown code block with the language specified
- Include any necessary imports at the top
- Add brief comments explaining key sections
- If the code requires additional files/dependencies, mention them

Focus on generating practical, working code that solves the user's problem."""

    def _get_language_guidelines(self, language: str) -> str:
        """Get language-specific guidelines."""
        guidelines = {
            'typescript': """
## TypeScript Guidelines
- Use TypeScript types and interfaces
- Prefer const and let over var
- Use async/await for asynchronous code
- Use React hooks for components (no class components)
- Use proper error handling with try/catch
- Export types and interfaces that might be reused
""",
            'javascript': """
## JavaScript Guidelines
- Use ES6+ syntax (arrow functions, destructuring, etc.)
- Prefer const and let over var
- Use async/await for asynchronous code
- Use React hooks for components
- Add JSDoc comments for functions
""",
            'python': """
## Python Guidelines
- Follow PEP 8 style guide
- Use type hints for function parameters and returns
- Use dataclasses or Pydantic for data structures
- Use async/await for asynchronous code
- Add docstrings for classes and functions
- Handle exceptions appropriately
""",
            'html': """
## HTML Guidelines
- Use semantic HTML5 elements
- Include proper accessibility attributes
- Keep structure clean and well-indented
- Use meaningful class names
""",
            'css': """
## CSS Guidelines
- Use CSS variables for colors and common values
- Use flexbox/grid for layouts
- Keep selectors simple and specific
- Consider responsive design
""",
        }
        
        return guidelines.get(language, "")
    
    def build_generation_prompt(
        self,
        description: str,
        language: str,
        item_type: str,
        research: dict = None,
        constraints: str = None,
        existing_code: str = None
    ) -> str:
        """
        Build the generation prompt with all context.
        """
        sections = []
        
        # Main request
        sections.append(f"## Request\n")
        sections.append(f"Generate a {item_type} in {language}:\n")
        sections.append(f"{description}\n")
        
        # Research findings
        if research and research.get('summary'):
            sections.append("\n## Research Findings\n")
            sections.append("Based on research of current best practices:\n")
            sections.append(research['summary'])
            sections.append("")
        
        # Constraints
        if constraints:
            sections.append("\n" + constraints)
        
        # Existing code context
        if existing_code:
            sections.append("\n## Existing Code Context\n")
            sections.append("The generated code should work with/extend:\n")
            sections.append(f"```{language}\n{existing_code[:2000]}\n```\n")
        
        # Final instructions
        sections.append("\n## Instructions\n")
        sections.append("1. Generate complete, working code")
        sections.append("2. Follow all constraints if provided")
        sections.append("3. Include necessary imports")
        sections.append("4. Add helpful comments")
        sections.append("5. Make the code production-ready")
        
        return '\n'.join(sections)
    
    def build_modification_prompt(
        self,
        original_code: str,
        modification_request: str,
        language: str,
        constraints: str = None
    ) -> str:
        """
        Build a prompt for modifying existing code.
        """
        sections = []
        
        sections.append("## Modification Request\n")
        sections.append(f"{modification_request}\n")
        
        sections.append("\n## Original Code\n")
        sections.append(f"```{language}\n{original_code}\n```\n")
        
        if constraints:
            sections.append("\n" + constraints)
        
        sections.append("\n## Instructions\n")
        sections.append("1. Apply the requested modifications")
        sections.append("2. Preserve existing functionality unless asked to change it")
        sections.append("3. Follow all constraints if provided")
        sections.append("4. Return the complete modified code")
        
        return '\n'.join(sections)
    
    def build_review_prompt(
        self,
        code: str,
        language: str,
        review_type: str = 'general'
    ) -> str:
        """
        Build a prompt for code review.
        """
        review_focus = {
            'general': "Review for overall quality, best practices, and potential issues",
            'security': "Focus on security vulnerabilities and unsafe patterns",
            'performance': "Focus on performance issues and optimization opportunities",
            'style': "Focus on code style, naming, and organization",
        }
        
        focus = review_focus.get(review_type, review_focus['general'])
        
        return f"""## Code Review Request

{focus}

## Code to Review
```{language}
{code}
```

## Provide
1. Overall assessment (1-10 score)
2. Issues found (list with severity: high/medium/low)
3. Improvement suggestions
4. Positive aspects of the code

Format your response as JSON:
{{
    "score": 8,
    "issues": [
        {{"severity": "high", "line": 10, "message": "..."}}
    ],
    "suggestions": ["..."],
    "positives": ["..."]
}}
"""


class LibraryItemPromptBuilder:
    """
    Builds prompts for library item operations.
    """
    
    def build_documentation_prompt(
        self,
        code: str,
        language: str,
        name: str
    ) -> str:
        """
        Build a prompt to generate documentation for code.
        """
        return f"""Generate documentation for the following {language} code named "{name}":

```{language}
{code}
```

Provide:
1. A brief description (1-2 sentences)
2. Detailed documentation explaining:
   - Purpose and functionality
   - Parameters/props
   - Return values
   - Usage example
3. List of keywords/tags (as a JSON array)

Format your response as:
DESCRIPTION:
<description here>

DOCUMENTATION:
<detailed docs here>

KEYWORDS:
["keyword1", "keyword2", ...]
"""

    def build_improvement_prompt(
        self,
        code: str,
        language: str,
        issues: list = None
    ) -> str:
        """
        Build a prompt to improve existing code.
        """
        issues_text = ""
        if issues:
            issues_text = "\n\nKnown Issues:\n" + "\n".join(f"- {i}" for i in issues)
        
        return f"""Improve the following {language} code:

```{language}
{code}
```
{issues_text}

Requirements:
1. Fix any bugs or issues
2. Improve code quality and readability
3. Add missing error handling
4. Optimize where appropriate
5. Keep the same functionality

Return the improved code in a markdown code block.
"""









