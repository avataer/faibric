"""
Agent Mode - Autonomous development with debugging and web search.
"""
import logging
from anthropic import Anthropic

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = '''You are an autonomous development agent. You can:
1. Generate and modify code
2. Debug errors by analyzing stack traces
3. Search documentation when needed
4. Make multiple iterations to fix issues

When given a task:
- Analyze the requirements thoroughly
- Generate code step by step
- If you encounter an error, debug it autonomously
- Continue iterating until the task is complete or you need user input

Always explain your reasoning and what you are doing at each step.
'''

class AgentModeService:
    def __init__(self, project_id):
        self.project_id = project_id
        self.client = Anthropic()
        self.conversation_history = []
        self.iteration_count = 0
        self.max_iterations = 10

    def run_agent_task(self, task_description, current_code=None):
        """Run an autonomous agent task."""
        self.conversation_history.append({
            'role': 'user',
            'content': f"Task: {task_description}\n\nCurrent code:\n{current_code or 'No code yet'}"
        })

        while self.iteration_count < self.max_iterations:
            response = self._call_ai()

            if self._is_task_complete(response):
                return {'status': 'complete', 'result': response, 'iterations': self.iteration_count}

            if self._has_error(response):
                self._handle_error(response)

            self.iteration_count += 1

        return {'status': 'max_iterations', 'result': response, 'iterations': self.iteration_count}

    def _call_ai(self):
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=AGENT_SYSTEM_PROMPT,
            messages=self.conversation_history
        )
        content = response.content[0].text
        self.conversation_history.append({'role': 'assistant', 'content': content})
        return content

    def _is_task_complete(self, response):
        return 'TASK_COMPLETE' in response or 'task is complete' in response.lower()

    def _has_error(self, response):
        return 'error' in response.lower() or 'failed' in response.lower()

    def _handle_error(self, response):
        self.conversation_history.append({
            'role': 'user',
            'content': 'Please debug the error and try again.'
        })
