"""
Visual Project Map for Faibric Platform.
Interactive SVG-based diagram showing architecture and data flows.
"""

def generate_project_map_html():
    """Generate the interactive visual project map with SVG graphics."""
    
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Faibric Visual Architecture Map</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
        }
        body {
            background: #0a0a1a;
            color: #e2e8f0;
            min-height: 100vh;
            overflow-x: hidden;
        }
        .header {
            text-align: center;
            padding: 30px;
            background: linear-gradient(180deg, rgba(59,130,246,0.1), transparent);
        }
        h1 {
            font-size: 32px;
            font-weight: 700;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        .subtitle {
            color: #64748b;
            font-size: 14px;
        }
        .controls {
            display: flex;
            justify-content: center;
            gap: 12px;
            margin-top: 20px;
        }
        .btn {
            padding: 8px 20px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #3b82f6;
            color: white;
        }
        .btn-secondary {
            background: #1e293b;
            color: #94a3b8;
            border: 1px solid #334155;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .map-container {
            position: relative;
            width: 100%;
            height: calc(100vh - 150px);
            overflow: auto;
        }
        #canvas {
            display: block;
        }
        .tooltip {
            position: absolute;
            background: #1e293b;
            border: 1px solid #3b82f6;
            border-radius: 12px;
            padding: 16px;
            max-width: 300px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            z-index: 1000;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        }
        .tooltip.visible {
            opacity: 1;
        }
        .tooltip-title {
            font-weight: 600;
            font-size: 16px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .tooltip-desc {
            font-size: 13px;
            color: #94a3b8;
            line-height: 1.5;
        }
        .tooltip-badge {
            background: #fbbf24;
            color: #000;
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 10px;
            font-weight: 700;
        }
        .legend {
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: rgba(30, 41, 59, 0.95);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #334155;
        }
        .legend-title {
            font-size: 12px;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
            font-size: 13px;
        }
        .legend-dot {
            width: 14px;
            height: 14px;
            border-radius: 4px;
        }
        .back-link {
            position: fixed;
            top: 20px;
            left: 20px;
            color: #94a3b8;
            text-decoration: none;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            z-index: 100;
        }
        .back-link:hover {
            color: #3b82f6;
        }
        .stats-panel {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(30, 41, 59, 0.95);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #334155;
        }
        .stat-row {
            display: flex;
            justify-content: space-between;
            gap: 20px;
            margin-bottom: 8px;
        }
        .stat-label {
            color: #64748b;
            font-size: 12px;
        }
        .stat-value {
            font-weight: 700;
            color: #3b82f6;
        }
    </style>
</head>
<body>
    <a href="/api/analytics/dashboard/" class="back-link">← Dashboard</a>
    
    <div class="header">
        <h1>Faibric Architecture Map</h1>
        <p class="subtitle">Interactive visualization of platform components and data flows</p>
        <div class="controls">
            <button class="btn btn-primary" onclick="resetView()">Reset View</button>
            <button class="btn btn-secondary" onclick="toggleAnimation()">Toggle Animation</button>
            <button class="btn btn-secondary" onclick="toggleLabels()">Toggle Labels</button>
        </div>
    </div>
    
    <div class="map-container">
        <canvas id="canvas"></canvas>
    </div>
    
    <div class="tooltip" id="tooltip">
        <div class="tooltip-title">
            <span id="tooltip-icon"></span>
            <span id="tooltip-name"></span>
            <span class="tooltip-badge" id="tooltip-badge" style="display:none">NEW</span>
        </div>
        <div class="tooltip-desc" id="tooltip-desc"></div>
    </div>
    
    <div class="legend">
        <div class="legend-title">Components</div>
        <div class="legend-item"><div class="legend-dot" style="background: #22d3ee;"></div> Frontend</div>
        <div class="legend-item"><div class="legend-dot" style="background: #a78bfa;"></div> Backend</div>
        <div class="legend-item"><div class="legend-dot" style="background: #f472b6;"></div> AI Engine</div>
        <div class="legend-item"><div class="legend-dot" style="background: #4ade80;"></div> Database</div>
        <div class="legend-item"><div class="legend-dot" style="background: #fb923c;"></div> External</div>
        <div class="legend-item"><div class="legend-dot" style="background: #fbbf24;"></div> ✨ New</div>
    </div>
    
    <div class="stats-panel">
        <div class="stat-row"><span class="stat-label">Components</span><span class="stat-value">24</span></div>
        <div class="stat-row"><span class="stat-label">Connections</span><span class="stat-value">32</span></div>
        <div class="stat-row"><span class="stat-label">New Features</span><span class="stat-value">15</span></div>
    </div>
    
    <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        const tooltip = document.getElementById('tooltip');
        
        let width, height;
        let animationEnabled = true;
        let labelsEnabled = true;
        let hoveredNode = null;
        let time = 0;
        
        // Colors
        const colors = {
            frontend: '#22d3ee',
            backend: '#a78bfa',
            ai: '#f472b6',
            database: '#4ade80',
            external: '#fb923c',
            new: '#fbbf24',
            connection: 'rgba(59, 130, 246, 0.3)',
            connectionActive: 'rgba(59, 130, 246, 0.8)',
            flow: '#3b82f6'
        };
        
        // Nodes definition
        const nodes = [
            // Frontend Layer (top)
            { id: 'react', x: 0.15, y: 0.12, type: 'frontend', icon: '⚛️', name: 'React Frontend', desc: 'Vite + TypeScript. User interface, landing page, chat.', size: 50 },
            { id: 'studio', x: 0.35, y: 0.12, type: 'frontend', icon: '🏗️', name: 'BuildingStudio', desc: 'Split-screen builder. Chat on left, preview on right.', size: 45, isNew: true },
            { id: 'preview', x: 0.55, y: 0.12, type: 'frontend', icon: '🎬', name: 'ProgressivePreview', desc: 'Animated build visualization with contextual content.', size: 45, isNew: true },
            { id: 'sandpack', x: 0.75, y: 0.12, type: 'frontend', icon: '📦', name: 'Sandpack', desc: 'Live in-browser React preview before deployment.', size: 40 },
            
            // Backend Layer
            { id: 'django', x: 0.25, y: 0.32, type: 'backend', icon: '🐍', name: 'Django API', desc: 'REST API. Handles requests, auth, data, routing.', size: 55 },
            { id: 'onboarding', x: 0.45, y: 0.28, type: 'backend', icon: '📝', name: 'Onboarding', desc: 'Session management, email verification, magic links.', size: 42 },
            { id: 'build', x: 0.65, y: 0.32, type: 'backend', icon: '🔨', name: 'Build Service', desc: 'In-process builds. No Celery needed. Fast.', size: 45, isNew: true },
            { id: 'cost', x: 0.85, y: 0.28, type: 'backend', icon: '💰', name: 'Cost Tracker', desc: 'Per-user API costs. Forecasting. Model breakdown.', size: 40, isNew: true },
            
            // AI Layer
            { id: 'generator', x: 0.20, y: 0.50, type: 'ai', icon: '🧠', name: 'AI Generator', desc: 'Claude Opus for new code. Haiku for reuse. Smart selection.', size: 55, isNew: true },
            { id: 'library', x: 0.40, y: 0.48, type: 'ai', icon: '📚', name: 'Code Library', desc: 'Reusable components. Semantic search. Quality scores.', size: 48 },
            { id: 'prompts', x: 0.60, y: 0.50, type: 'ai', icon: '📊', name: 'Prompt Analytics', desc: 'Success rates by type and industry. Optimization.', size: 42, isNew: true },
            { id: 'gaps', x: 0.80, y: 0.48, type: 'ai', icon: '🔍', name: 'Gap Analysis', desc: 'Detect missing components. Priority recommendations.', size: 40, isNew: true },
            
            // Analytics Layer
            { id: 'dashboard', x: 0.15, y: 0.68, type: 'backend', icon: '📈', name: 'Admin Dashboard', desc: '12 pages. Real-time activity, users, costs, alerts.', size: 55, isNew: true },
            { id: 'health', x: 0.32, y: 0.72, type: 'backend', icon: '❤️', name: 'Health Scores', desc: '0-100 customer health. Churn prediction.', size: 42, isNew: true },
            { id: 'funnel', x: 0.48, y: 0.68, type: 'backend', icon: '📉', name: 'Funnel', desc: 'Conversion tracking. Drop-off analysis.', size: 42, isNew: true },
            { id: 'cohorts', x: 0.64, y: 0.72, type: 'backend', icon: '👥', name: 'Cohorts', desc: 'Weekly retention. Cohort comparison.', size: 40, isNew: true },
            { id: 'alerts', x: 0.80, y: 0.68, type: 'backend', icon: '🔔', name: 'Alerts', desc: 'Configurable rules. Email notifications.', size: 42, isNew: true },
            
            // Data Layer
            { id: 'postgres', x: 0.25, y: 0.88, type: 'database', icon: '🐘', name: 'PostgreSQL', desc: 'Production database. All persistent data.', size: 45 },
            { id: 'redis', x: 0.45, y: 0.88, type: 'database', icon: '⚡', name: 'Redis', desc: 'Cache. Real-time message broadcasting.', size: 40 },
            
            // External Services
            { id: 'anthropic', x: 0.60, y: 0.88, type: 'external', icon: '🤖', name: 'Anthropic', desc: 'Claude Opus 4.5 + Haiku 3.5. AI backbone.', size: 50 },
            { id: 'render', x: 0.75, y: 0.88, type: 'external', icon: '🚀', name: 'Render', desc: 'Deployment platform. Hosts generated sites.', size: 45 },
            { id: 'github', x: 0.88, y: 0.88, type: 'external', icon: '🐙', name: 'GitHub', desc: 'Code storage. Branch per project.', size: 42 },
        ];
        
        // Connections (data flow)
        const connections = [
            // User flow
            { from: 'react', to: 'django', animated: true },
            { from: 'studio', to: 'onboarding' },
            { from: 'preview', to: 'build' },
            { from: 'sandpack', to: 'build' },
            
            // Backend internal
            { from: 'django', to: 'onboarding' },
            { from: 'django', to: 'build' },
            { from: 'onboarding', to: 'build', animated: true },
            { from: 'build', to: 'cost' },
            
            // AI connections
            { from: 'build', to: 'generator', animated: true },
            { from: 'generator', to: 'library' },
            { from: 'generator', to: 'prompts' },
            { from: 'library', to: 'gaps' },
            
            // Analytics
            { from: 'django', to: 'dashboard' },
            { from: 'cost', to: 'dashboard' },
            { from: 'dashboard', to: 'health' },
            { from: 'dashboard', to: 'funnel' },
            { from: 'dashboard', to: 'cohorts' },
            { from: 'dashboard', to: 'alerts' },
            { from: 'prompts', to: 'dashboard' },
            
            // Data layer
            { from: 'django', to: 'postgres' },
            { from: 'django', to: 'redis' },
            { from: 'dashboard', to: 'postgres' },
            
            // External
            { from: 'generator', to: 'anthropic', animated: true },
            { from: 'build', to: 'render', animated: true },
            { from: 'build', to: 'github' },
            { from: 'render', to: 'github' },
            { from: 'alerts', to: 'anthropic' },
        ];
        
        function resize() {
            width = window.innerWidth;
            height = window.innerHeight - 150;
            canvas.width = width * window.devicePixelRatio;
            canvas.height = height * window.devicePixelRatio;
            canvas.style.width = width + 'px';
            canvas.style.height = height + 'px';
            ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        }
        
        function getNodePos(node) {
            return {
                x: node.x * width,
                y: node.y * height
            };
        }
        
        function drawConnection(from, to, animated = false) {
            const fromNode = nodes.find(n => n.id === from);
            const toNode = nodes.find(n => n.id === to);
            if (!fromNode || !toNode) return;
            
            const p1 = getNodePos(fromNode);
            const p2 = getNodePos(toNode);
            
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            
            // Curved line
            const midX = (p1.x + p2.x) / 2;
            const midY = (p1.y + p2.y) / 2;
            const offsetY = (p2.y - p1.y) * 0.3;
            
            ctx.quadraticCurveTo(midX, midY - offsetY, p2.x, p2.y);
            
            ctx.strokeStyle = colors.connection;
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // Animated flow particle
            if (animated && animationEnabled) {
                const t = (Math.sin(time * 2 + from.charCodeAt(0)) + 1) / 2;
                const flowX = p1.x + (p2.x - p1.x) * t;
                const flowY = p1.y + (p2.y - p1.y) * t - offsetY * Math.sin(t * Math.PI);
                
                ctx.beginPath();
                ctx.arc(flowX, flowY, 4, 0, Math.PI * 2);
                ctx.fillStyle = colors.flow;
                ctx.fill();
                
                // Glow
                const gradient = ctx.createRadialGradient(flowX, flowY, 0, flowX, flowY, 12);
                gradient.addColorStop(0, 'rgba(59, 130, 246, 0.5)');
                gradient.addColorStop(1, 'rgba(59, 130, 246, 0)');
                ctx.beginPath();
                ctx.arc(flowX, flowY, 12, 0, Math.PI * 2);
                ctx.fillStyle = gradient;
                ctx.fill();
            }
        }
        
        function drawNode(node) {
            const pos = getNodePos(node);
            const isHovered = hoveredNode === node;
            const baseSize = node.size;
            const size = isHovered ? baseSize * 1.15 : baseSize;
            
            // Glow for new items
            if (node.isNew) {
                const glowIntensity = (Math.sin(time * 3) + 1) / 2 * 0.3 + 0.2;
                const gradient = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, size * 1.5);
                gradient.addColorStop(0, `rgba(251, 191, 36, ${glowIntensity})`);
                gradient.addColorStop(1, 'rgba(251, 191, 36, 0)');
                ctx.beginPath();
                ctx.arc(pos.x, pos.y, size * 1.5, 0, Math.PI * 2);
                ctx.fillStyle = gradient;
                ctx.fill();
            }
            
            // Node circle
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, size, 0, Math.PI * 2);
            
            // Gradient fill
            const color = node.isNew ? colors.new : colors[node.type];
            const gradient = ctx.createRadialGradient(pos.x - size/3, pos.y - size/3, 0, pos.x, pos.y, size);
            gradient.addColorStop(0, color);
            gradient.addColorStop(1, shadeColor(color, -40));
            ctx.fillStyle = gradient;
            ctx.fill();
            
            // Border
            ctx.strokeStyle = isHovered ? '#fff' : 'rgba(255,255,255,0.3)';
            ctx.lineWidth = isHovered ? 3 : 2;
            ctx.stroke();
            
            // Icon
            ctx.font = `${size * 0.6}px Arial`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#fff';
            ctx.fillText(node.icon, pos.x, pos.y);
            
            // Label
            if (labelsEnabled) {
                ctx.font = '12px -apple-system, sans-serif';
                ctx.fillStyle = isHovered ? '#fff' : '#94a3b8';
                ctx.fillText(node.name, pos.x, pos.y + size + 16);
            }
        }
        
        function shadeColor(color, percent) {
            const num = parseInt(color.replace('#', ''), 16);
            const amt = Math.round(2.55 * percent);
            const R = (num >> 16) + amt;
            const G = (num >> 8 & 0x00FF) + amt;
            const B = (num & 0x0000FF) + amt;
            return '#' + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 + 
                (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 + 
                (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
        }
        
        function draw() {
            ctx.clearRect(0, 0, width, height);
            
            // Draw connections first
            connections.forEach(c => drawConnection(c.from, c.to, c.animated));
            
            // Draw nodes
            nodes.forEach(node => drawNode(node));
            
            time += 0.016;
            requestAnimationFrame(draw);
        }
        
        function handleMouseMove(e) {
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            hoveredNode = null;
            for (const node of nodes) {
                const pos = getNodePos(node);
                const dist = Math.sqrt((x - pos.x) ** 2 + (y - pos.y) ** 2);
                if (dist < node.size) {
                    hoveredNode = node;
                    break;
                }
            }
            
            if (hoveredNode) {
                canvas.style.cursor = 'pointer';
                tooltip.classList.add('visible');
                tooltip.style.left = (e.clientX + 20) + 'px';
                tooltip.style.top = (e.clientY + 20) + 'px';
                document.getElementById('tooltip-icon').textContent = hoveredNode.icon;
                document.getElementById('tooltip-name').textContent = hoveredNode.name;
                document.getElementById('tooltip-desc').textContent = hoveredNode.desc;
                document.getElementById('tooltip-badge').style.display = hoveredNode.isNew ? 'inline' : 'none';
            } else {
                canvas.style.cursor = 'default';
                tooltip.classList.remove('visible');
            }
        }
        
        function resetView() {
            // Could implement zoom/pan reset here
        }
        
        function toggleAnimation() {
            animationEnabled = !animationEnabled;
        }
        
        function toggleLabels() {
            labelsEnabled = !labelsEnabled;
        }
        
        // Initialize
        resize();
        window.addEventListener('resize', resize);
        canvas.addEventListener('mousemove', handleMouseMove);
        draw();
    </script>
</body>
</html>
"""
