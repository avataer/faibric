import unittest
import re

class TestVercelRegex(unittest.TestCase):
    def _convert_to_browser_react_improved(self, code: str) -> str:
        # Improved import removal
        # 1. Multi-line imports with 'from'
        code = re.sub(r'import\s+.*?from\s+[\'"].*?[\'"];?\s*', '', code, flags=re.DOTALL)
        # 2. Simple imports
        code = re.sub(r'import\s+[\'"].*?[\'"];?\s*', '', code, flags=re.DOTALL)
        
        # Remove export statements
        code = re.sub(r'export\s+default\s+\w+;?\s*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'export\s+default\s+function', 'function', code)
        code = re.sub(r'^export\s+(?=const|let|var|function|class)', '', code, flags=re.MULTILINE)
        
        return code.strip()

    def test_multiline_import_bug(self):
        code = """import {
  useState,
  useEffect
} from 'react';

function App() {
  return <div>Hello</div>;
}

export default App;"""
        
        converted = self._convert_to_browser_react_improved(code)
        
        self.assertNotIn("useState", converted)
        self.assertNotIn("useEffect", converted)
        self.assertNotIn("from 'react'", converted)
        self.assertIn("function App", converted)
        self.assertEqual(converted, "function App() {\n  return <div>Hello</div>;\n}")

if __name__ == '__main__':
    unittest.main()
