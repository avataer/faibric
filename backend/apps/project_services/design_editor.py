"""
Visual Design Editor
Live CSS editing without rebuild.
"""
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class DesignToken:
    """A customizable design token."""
    name: str
    css_var: str
    default_value: str
    type: str  # 'color', 'size', 'font', 'spacing'
    category: str  # 'colors', 'typography', 'layout'


class DesignEditor:
    """
    Manages live design editing for deployed projects.
    """
    
    # Default design tokens
    DEFAULT_TOKENS = [
        # Colors
        DesignToken('Primary Color', '--color-primary', '#4F46E5', 'color', 'colors'),
        DesignToken('Primary Hover', '--color-primary-hover', '#4338CA', 'color', 'colors'),
        DesignToken('Secondary Color', '--color-secondary', '#10B981', 'color', 'colors'),
        DesignToken('Background', '--color-bg', '#FFFFFF', 'color', 'colors'),
        DesignToken('Surface', '--color-surface', '#F9FAFB', 'color', 'colors'),
        DesignToken('Text Primary', '--color-text', '#111827', 'color', 'colors'),
        DesignToken('Text Secondary', '--color-text-muted', '#6B7280', 'color', 'colors'),
        DesignToken('Border', '--color-border', '#E5E7EB', 'color', 'colors'),
        DesignToken('Error', '--color-error', '#EF4444', 'color', 'colors'),
        DesignToken('Success', '--color-success', '#10B981', 'color', 'colors'),
        
        # Typography
        DesignToken('Font Family', '--font-family', 'Inter, system-ui, sans-serif', 'font', 'typography'),
        DesignToken('Heading Font', '--font-heading', 'Inter, system-ui, sans-serif', 'font', 'typography'),
        DesignToken('Base Size', '--font-size-base', '16px', 'size', 'typography'),
        DesignToken('Line Height', '--line-height', '1.5', 'size', 'typography'),
        
        # Spacing
        DesignToken('Border Radius', '--radius', '8px', 'size', 'layout'),
        DesignToken('Container Width', '--container-width', '1280px', 'size', 'layout'),
        DesignToken('Spacing Unit', '--spacing', '16px', 'spacing', 'layout'),
    ]
    
    def generate_css_variables(self, tokens: Dict[str, str] = None) -> str:
        """
        Generate CSS with custom variables.
        """
        token_values = {}
        for token in self.DEFAULT_TOKENS:
            token_values[token.css_var] = token.default_value
        
        if tokens:
            token_values.update(tokens)
        
        css = ':root {\n'
        for var, value in token_values.items():
            css += f'  {var}: {value};\n'
        css += '}\n'
        
        return css
    
    def generate_editor_script(self, project_id: str) -> str:
        """
        Generate the design editor overlay script.
        """
        tokens_json = '[' + ','.join([
            f'{{"name":"{t.name}","var":"{t.css_var}","default":"{t.default_value}","type":"{t.type}","category":"{t.category}"}}'
            for t in self.DEFAULT_TOKENS
        ]) + ']'
        
        return f'''
// ═══════════════════════════════════════════════════════════════════════════════
// FAIBRIC DESIGN EDITOR
// ═══════════════════════════════════════════════════════════════════════════════
(function() {{
  const PROJECT_ID = "{project_id}";
  const TOKENS = {tokens_json};
  
  // Check if in edit mode
  const urlParams = new URLSearchParams(window.location.search);
  if (!urlParams.has("edit")) return;
  
  // Load saved design
  const savedDesign = JSON.parse(localStorage.getItem("faibric_design_" + PROJECT_ID) || "{{}}");
  
  // Apply saved design
  Object.entries(savedDesign).forEach(([varName, value]) => {{
    document.documentElement.style.setProperty(varName, value);
  }});
  
  // Create editor panel
  const panel = document.createElement("div");
  panel.id = "faibric-design-editor";
  panel.innerHTML = `
    <style>
      #faibric-design-editor {{
        position: fixed;
        top: 0;
        right: 0;
        width: 320px;
        height: 100vh;
        background: white;
        box-shadow: -2px 0 10px rgba(0,0,0,0.1);
        z-index: 99999;
        font-family: system-ui, sans-serif;
        overflow-y: auto;
      }}
      #faibric-design-editor .header {{
        padding: 16px;
        background: #4F46E5;
        color: white;
        font-weight: bold;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }}
      #faibric-design-editor .section {{
        padding: 16px;
        border-bottom: 1px solid #eee;
      }}
      #faibric-design-editor .section-title {{
        font-weight: 600;
        margin-bottom: 12px;
        text-transform: uppercase;
        font-size: 12px;
        color: #666;
      }}
      #faibric-design-editor .token {{
        margin-bottom: 12px;
      }}
      #faibric-design-editor .token label {{
        display: block;
        font-size: 13px;
        margin-bottom: 4px;
      }}
      #faibric-design-editor .token input[type="color"] {{
        width: 100%;
        height: 36px;
        border: 1px solid #ddd;
        border-radius: 4px;
        cursor: pointer;
      }}
      #faibric-design-editor .token input[type="text"] {{
        width: 100%;
        padding: 8px;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 14px;
      }}
      #faibric-design-editor .actions {{
        padding: 16px;
        display: flex;
        gap: 8px;
      }}
      #faibric-design-editor .btn {{
        flex: 1;
        padding: 10px;
        border: none;
        border-radius: 6px;
        font-weight: 500;
        cursor: pointer;
      }}
      #faibric-design-editor .btn-primary {{
        background: #4F46E5;
        color: white;
      }}
      #faibric-design-editor .btn-secondary {{
        background: #f3f4f6;
        color: #333;
      }}
    </style>
    <div class="header">
      <span>Design Editor</span>
      <button onclick="document.getElementById('faibric-design-editor').remove()" style="background:none;border:none;color:white;cursor:pointer;font-size:20px">&times;</button>
    </div>
    <div id="editor-content"></div>
    <div class="actions">
      <button class="btn btn-secondary" onclick="faibricResetDesign()">Reset</button>
      <button class="btn btn-primary" onclick="faibricSaveDesign()">Save Design</button>
    </div>
  `;
  document.body.appendChild(panel);
  
  // Group tokens by category
  const grouped = {{}};
  TOKENS.forEach(token => {{
    if (!grouped[token.category]) grouped[token.category] = [];
    grouped[token.category].push(token);
  }});
  
  // Render editor content
  const content = document.getElementById("editor-content");
  Object.entries(grouped).forEach(([category, tokens]) => {{
    let html = `<div class="section"><div class="section-title">${{category}}</div>`;
    tokens.forEach(token => {{
      const currentValue = getComputedStyle(document.documentElement).getPropertyValue(token.var).trim() || token.default;
      if (token.type === "color") {{
        html += `
          <div class="token">
            <label>${{token.name}}</label>
            <input type="color" value="${{currentValue}}" data-var="${{token.var}}" onchange="faibricUpdateToken(this)">
          </div>
        `;
      }} else {{
        html += `
          <div class="token">
            <label>${{token.name}}</label>
            <input type="text" value="${{currentValue}}" data-var="${{token.var}}" onchange="faibricUpdateToken(this)">
          </div>
        `;
      }}
    }});
    html += "</div>";
    content.innerHTML += html;
  }});
  
  // Update token
  window.faibricUpdateToken = function(input) {{
    const varName = input.dataset.var;
    const value = input.value;
    document.documentElement.style.setProperty(varName, value);
    
    // Update saved design
    savedDesign[varName] = value;
  }};
  
  // Save design
  window.faibricSaveDesign = function() {{
    localStorage.setItem("faibric_design_" + PROJECT_ID, JSON.stringify(savedDesign));
    
    // Also save to server
    fetch("/api/project-services/design/" + PROJECT_ID + "/", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{ tokens: savedDesign }})
    }}).then(() => {{
      alert("Design saved!");
    }}).catch(err => {{
      console.error("Failed to save design:", err);
      alert("Design saved locally only (server save failed)");
    }});
  }};
  
  // Reset design
  window.faibricResetDesign = function() {{
    if (!confirm("Reset all design changes?")) return;
    
    TOKENS.forEach(token => {{
      document.documentElement.style.setProperty(token.var, token.default);
    }});
    
    Object.keys(savedDesign).forEach(key => delete savedDesign[key]);
    localStorage.removeItem("faibric_design_" + PROJECT_ID);
    
    // Reload editor
    document.getElementById("editor-content").innerHTML = "";
    Object.entries(grouped).forEach(([category, tokens]) => {{
      // Rebuild content...
    }});
    
    alert("Design reset to defaults");
  }};
}})();
'''
    
    def generate_editor_component(self) -> str:
        """
        Generate React component for in-app design editing.
        """
        return '''
// Design Editor Component (for in-app editing)
const DesignEditor = ({ projectId, onSave }) => {
  const [tokens, setTokens] = React.useState({});
  const [isOpen, setIsOpen] = React.useState(false);
  
  const defaultTokens = [
    { name: "Primary Color", var: "--color-primary", default: "#4F46E5", type: "color" },
    { name: "Background", var: "--color-bg", default: "#FFFFFF", type: "color" },
    { name: "Text", var: "--color-text", default: "#111827", type: "color" },
    { name: "Border Radius", var: "--radius", default: "8px", type: "text" },
    { name: "Font Family", var: "--font-family", default: "Inter, sans-serif", type: "text" },
  ];
  
  const updateToken = (varName, value) => {
    document.documentElement.style.setProperty(varName, value);
    setTokens({ ...tokens, [varName]: value });
  };
  
  const saveDesign = async () => {
    localStorage.setItem(`design_${projectId}`, JSON.stringify(tokens));
    if (onSave) await onSave(tokens);
    alert("Design saved!");
  };
  
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 p-3 bg-indigo-600 text-white rounded-full shadow-lg hover:bg-indigo-700 z-50"
        title="Open Design Editor"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
        </svg>
      </button>
    );
  }
  
  return (
    <div className="fixed top-0 right-0 w-80 h-full bg-white shadow-xl z-50 overflow-y-auto">
      <div className="p-4 bg-indigo-600 text-white flex justify-between items-center">
        <span className="font-bold">Design Editor</span>
        <button onClick={() => setIsOpen(false)} className="text-2xl">&times;</button>
      </div>
      
      <div className="p-4 space-y-4">
        {defaultTokens.map(token => (
          <div key={token.var}>
            <label className="block text-sm font-medium mb-1">{token.name}</label>
            {token.type === "color" ? (
              <input
                type="color"
                defaultValue={token.default}
                onChange={(e) => updateToken(token.var, e.target.value)}
                className="w-full h-10 rounded border cursor-pointer"
              />
            ) : (
              <input
                type="text"
                defaultValue={token.default}
                onChange={(e) => updateToken(token.var, e.target.value)}
                className="w-full px-3 py-2 border rounded"
              />
            )}
          </div>
        ))}
      </div>
      
      <div className="p-4 border-t">
        <button
          onClick={saveDesign}
          className="w-full py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
        >
          Save Design
        </button>
      </div>
    </div>
  );
};
'''


# Singleton
design_editor = DesignEditor()



