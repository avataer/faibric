"""
Visual Project Map for Faibric Platform.
Interactive webpage showing all components and their relationships.
"""

def generate_project_map_html():
    """Generate the interactive project map HTML."""
    
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Faibric Project Map</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
        }
        body {
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            color: #e2e8f0;
            min-height: 100vh;
            padding: 40px;
            overflow-x: auto;
        }
        h1 {
            text-align: center;
            font-size: 36px;
            font-weight: 700;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #94a3b8;
            margin-bottom: 40px;
        }
        .legend {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 40px;
            flex-wrap: wrap;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }
        .legend-dot {
            width: 16px;
            height: 16px;
            border-radius: 4px;
        }
        .map-container {
            display: flex;
            flex-direction: column;
            gap: 60px;
            max-width: 1600px;
            margin: 0 auto;
        }
        .layer {
            position: relative;
        }
        .layer-title {
            text-align: center;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: #64748b;
            margin-bottom: 20px;
        }
        .nodes {
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
        }
        .node {
            background: #1e293b;
            border-radius: 16px;
            padding: 20px;
            min-width: 200px;
            max-width: 280px;
            border: 2px solid #334155;
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
        }
        .node:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }
        .node.frontend { border-color: #22d3ee; }
        .node.backend { border-color: #a78bfa; }
        .node.ai { border-color: #f472b6; }
        .node.database { border-color: #4ade80; }
        .node.external { border-color: #fb923c; }
        .node.new { 
            border-color: #fbbf24; 
            animation: glow 2s infinite;
        }
        @keyframes glow {
            0%, 100% { box-shadow: 0 0 20px rgba(251, 191, 36, 0.3); }
            50% { box-shadow: 0 0 40px rgba(251, 191, 36, 0.5); }
        }
        .node-icon {
            font-size: 32px;
            margin-bottom: 12px;
        }
        .node-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .node-desc {
            font-size: 12px;
            color: #94a3b8;
            line-height: 1.5;
        }
        .node-badge {
            position: absolute;
            top: -8px;
            right: -8px;
            background: #fbbf24;
            color: #000;
            font-size: 10px;
            font-weight: 700;
            padding: 4px 8px;
            border-radius: 12px;
        }
        .connections {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
        }
        .section {
            background: rgba(30, 41, 59, 0.5);
            border-radius: 24px;
            padding: 30px;
            margin-bottom: 40px;
        }
        .section-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 16px;
        }
        .feature {
            background: #0f172a;
            border-radius: 12px;
            padding: 16px;
            border-left: 4px solid #3b82f6;
        }
        .feature.new {
            border-left-color: #fbbf24;
            background: rgba(251, 191, 36, 0.1);
        }
        .feature-title {
            font-weight: 600;
            margin-bottom: 4px;
        }
        .feature-desc {
            font-size: 13px;
            color: #94a3b8;
        }
        .flow-diagram {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0;
            flex-wrap: wrap;
            padding: 20px;
        }
        .flow-step {
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border-radius: 12px;
            padding: 16px 24px;
            text-align: center;
            border: 1px solid #334155;
            min-width: 140px;
        }
        .flow-arrow {
            font-size: 24px;
            color: #3b82f6;
            padding: 0 10px;
        }
        .flow-step-num {
            font-size: 10px;
            color: #64748b;
            margin-bottom: 4px;
        }
        .flow-step-title {
            font-weight: 600;
            font-size: 14px;
        }
        .stats-bar {
            display: flex;
            justify-content: center;
            gap: 40px;
            margin: 40px 0;
            flex-wrap: wrap;
        }
        .stat {
            text-align: center;
        }
        .stat-value {
            font-size: 48px;
            font-weight: 700;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stat-label {
            font-size: 14px;
            color: #94a3b8;
        }
        .timeline {
            display: flex;
            gap: 20px;
            overflow-x: auto;
            padding: 20px 0;
        }
        .timeline-item {
            flex-shrink: 0;
            width: 200px;
            background: #1e293b;
            border-radius: 12px;
            padding: 16px;
            border-top: 4px solid #3b82f6;
        }
        .timeline-item.recent {
            border-top-color: #fbbf24;
        }
        .timeline-date {
            font-size: 11px;
            color: #64748b;
            margin-bottom: 8px;
        }
        .timeline-title {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 4px;
        }
        .timeline-desc {
            font-size: 12px;
            color: #94a3b8;
        }
        .back-link {
            position: fixed;
            top: 20px;
            left: 20px;
            color: #94a3b8;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }
        .back-link:hover { color: #3b82f6; }
    </style>
</head>
<body>
    <a href="/api/analytics/dashboard/" class="back-link">← Back to Dashboard</a>
    
    <h1>🏗️ Faibric Platform Architecture</h1>
    <p class="subtitle">Interactive map of all components, features, and improvements</p>
    
    <div class="legend">
        <div class="legend-item">
            <div class="legend-dot" style="background: #22d3ee;"></div>
            <span>Frontend</span>
        </div>
        <div class="legend-item">
            <div class="legend-dot" style="background: #a78bfa;"></div>
            <span>Backend</span>
        </div>
        <div class="legend-item">
            <div class="legend-dot" style="background: #f472b6;"></div>
            <span>AI Engine</span>
        </div>
        <div class="legend-item">
            <div class="legend-dot" style="background: #4ade80;"></div>
            <span>Database</span>
        </div>
        <div class="legend-item">
            <div class="legend-dot" style="background: #fb923c;"></div>
            <span>External Services</span>
        </div>
        <div class="legend-item">
            <div class="legend-dot" style="background: #fbbf24;"></div>
            <span>✨ New/Improved</span>
        </div>
    </div>
    
    <div class="stats-bar">
        <div class="stat">
            <div class="stat-value">12</div>
            <div class="stat-label">Dashboard Pages</div>
        </div>
        <div class="stat">
            <div class="stat-value">15</div>
            <div class="stat-label">New Models</div>
        </div>
        <div class="stat">
            <div class="stat-value">50+</div>
            <div class="stat-label">API Endpoints</div>
        </div>
        <div class="stat">
            <div class="stat-value">2</div>
            <div class="stat-label">AI Models</div>
        </div>
    </div>
    
    <div class="map-container">
        <!-- User Flow -->
        <div class="section">
            <div class="section-title">🚀 User Build Flow</div>
            <div class="flow-diagram">
                <div class="flow-step">
                    <div class="flow-step-num">STEP 1</div>
                    <div class="flow-step-title">Submit Prompt</div>
                </div>
                <div class="flow-arrow">→</div>
                <div class="flow-step">
                    <div class="flow-step-num">STEP 2</div>
                    <div class="flow-step-title">Provide Email</div>
                </div>
                <div class="flow-arrow">→</div>
                <div class="flow-step">
                    <div class="flow-step-num">STEP 3</div>
                    <div class="flow-step-title">Verify Email</div>
                </div>
                <div class="flow-arrow">→</div>
                <div class="flow-step">
                    <div class="flow-step-num">STEP 4</div>
                    <div class="flow-step-title">AI Generates</div>
                </div>
                <div class="flow-arrow">→</div>
                <div class="flow-step">
                    <div class="flow-step-num">STEP 5</div>
                    <div class="flow-step-title">Deploy to Render</div>
                </div>
                <div class="flow-arrow">→</div>
                <div class="flow-step" style="border-color: #22c55e;">
                    <div class="flow-step-num">DONE</div>
                    <div class="flow-step-title">🎉 Live Site!</div>
                </div>
            </div>
        </div>
        
        <!-- Architecture Layers -->
        <div class="layer">
            <div class="layer-title">👤 User Interface Layer</div>
            <div class="nodes">
                <div class="node frontend">
                    <div class="node-icon">🖥️</div>
                    <div class="node-title">React Frontend</div>
                    <div class="node-desc">Vite + TypeScript. Landing page, chat interface, live preview.</div>
                </div>
                <div class="node frontend new">
                    <div class="node-badge">NEW</div>
                    <div class="node-icon">🏗️</div>
                    <div class="node-title">BuildingStudio</div>
                    <div class="node-desc">Split-screen builder with chat on left, preview on right.</div>
                </div>
                <div class="node frontend new">
                    <div class="node-badge">NEW</div>
                    <div class="node-icon">🎬</div>
                    <div class="node-title">ProgressivePreview</div>
                    <div class="node-desc">Animated build visualization. Contextual placeholders.</div>
                </div>
                <div class="node frontend">
                    <div class="node-icon">📦</div>
                    <div class="node-title">Sandpack Preview</div>
                    <div class="node-desc">Live in-browser React code preview before deployment.</div>
                </div>
            </div>
        </div>
        
        <div class="layer">
            <div class="layer-title">⚙️ Backend Services Layer</div>
            <div class="nodes">
                <div class="node backend">
                    <div class="node-icon">🐍</div>
                    <div class="node-title">Django REST API</div>
                    <div class="node-desc">Core backend. Handles all API requests, authentication, data.</div>
                </div>
                <div class="node backend">
                    <div class="node-icon">📝</div>
                    <div class="node-title">Onboarding Service</div>
                    <div class="node-desc">Session management, email verification, magic links.</div>
                </div>
                <div class="node backend new">
                    <div class="node-badge">NEW</div>
                    <div class="node-icon">🔨</div>
                    <div class="node-title">Build Service</div>
                    <div class="node-desc">In-process builds (no Celery). Faster, simpler.</div>
                </div>
                <div class="node backend new">
                    <div class="node-badge">NEW</div>
                    <div class="node-icon">💰</div>
                    <div class="node-title">Cost Tracker</div>
                    <div class="node-desc">Tracks every API call. Per-user costs. Forecasting.</div>
                </div>
            </div>
        </div>
        
        <div class="layer">
            <div class="layer-title">🤖 AI Engine Layer</div>
            <div class="nodes">
                <div class="node ai new">
                    <div class="node-badge">IMPROVED</div>
                    <div class="node-icon">🧠</div>
                    <div class="node-title">AIGeneratorV2</div>
                    <div class="node-desc">Smart model selection. Opus for new code, Haiku for reuse.</div>
                </div>
                <div class="node ai">
                    <div class="node-icon">📚</div>
                    <div class="node-title">Code Library</div>
                    <div class="node-desc">Reusable components. Semantic search. Usage tracking.</div>
                </div>
                <div class="node ai new">
                    <div class="node-badge">NEW</div>
                    <div class="node-icon">📊</div>
                    <div class="node-title">Prompt Analytics</div>
                    <div class="node-desc">Track success rates, types, industries. Optimize prompts.</div>
                </div>
                <div class="node ai new">
                    <div class="node-badge">NEW</div>
                    <div class="node-icon">🔍</div>
                    <div class="node-title">Gap Analysis</div>
                    <div class="node-desc">Detect missing components. Priority recommendations.</div>
                </div>
            </div>
        </div>
        
        <div class="layer">
            <div class="layer-title">📊 Analytics & Admin Layer</div>
            <div class="nodes">
                <div class="node backend new">
                    <div class="node-badge">NEW</div>
                    <div class="node-icon">📈</div>
                    <div class="node-title">Admin Dashboard</div>
                    <div class="node-desc">12 pages. Real-time activity, users, costs, alerts.</div>
                </div>
                <div class="node backend new">
                    <div class="node-badge">NEW</div>
                    <div class="node-icon">❤️</div>
                    <div class="node-title">Health Scores</div>
                    <div class="node-desc">0-100 customer health. Churn prediction. At-risk alerts.</div>
                </div>
                <div class="node backend new">
                    <div class="node-badge">NEW</div>
                    <div class="node-icon">📉</div>
                    <div class="node-title">Funnel Analytics</div>
                    <div class="node-desc">Conversion tracking. Drop-off analysis. Daily snapshots.</div>
                </div>
                <div class="node backend new">
                    <div class="node-badge">NEW</div>
                    <div class="node-icon">👥</div>
                    <div class="node-title">Cohort Analysis</div>
                    <div class="node-desc">Weekly retention. Cohort comparison. Heatmaps.</div>
                </div>
                <div class="node backend new">
                    <div class="node-badge">NEW</div>
                    <div class="node-icon">🔔</div>
                    <div class="node-title">Alert System</div>
                    <div class="node-desc">Configurable rules. Email notifications. Auto-triggers.</div>
                </div>
                <div class="node backend new">
                    <div class="node-badge">NEW</div>
                    <div class="node-icon">📄</div>
                    <div class="node-title">AI Reports</div>
                    <div class="node-desc">Daily summaries. Insights. Recommendations. Email delivery.</div>
                </div>
            </div>
        </div>
        
        <div class="layer">
            <div class="layer-title">💾 Data Layer</div>
            <div class="nodes">
                <div class="node database">
                    <div class="node-icon">🐘</div>
                    <div class="node-title">PostgreSQL</div>
                    <div class="node-desc">Production database on Render. All persistent data.</div>
                </div>
                <div class="node database">
                    <div class="node-icon">📁</div>
                    <div class="node-title">SQLite</div>
                    <div class="node-desc">Local development database. Same schema.</div>
                </div>
                <div class="node database">
                    <div class="node-icon">⚡</div>
                    <div class="node-title">Redis</div>
                    <div class="node-desc">Session cache. Real-time message broadcasting.</div>
                </div>
            </div>
        </div>
        
        <div class="layer">
            <div class="layer-title">🌐 External Services</div>
            <div class="nodes">
                <div class="node external">
                    <div class="node-icon">🤖</div>
                    <div class="node-title">Anthropic Claude</div>
                    <div class="node-desc">Opus 4.5 for generation. Haiku 3.5 for analysis.</div>
                </div>
                <div class="node external">
                    <div class="node-icon">🚀</div>
                    <div class="node-title">Render.com</div>
                    <div class="node-desc">Deployment platform. Static sites for generated apps.</div>
                </div>
                <div class="node external">
                    <div class="node-icon">🐙</div>
                    <div class="node-title">GitHub</div>
                    <div class="node-desc">Code storage for deployed apps. Branch per project.</div>
                </div>
                <div class="node external">
                    <div class="node-icon">📧</div>
                    <div class="node-title">SendGrid</div>
                    <div class="node-desc">Email delivery. Magic links. Alert notifications.</div>
                </div>
            </div>
        </div>
        
        <!-- Recent Improvements Timeline -->
        <div class="section">
            <div class="section-title">✨ Recent Improvements Timeline</div>
            <div class="timeline">
                <div class="timeline-item recent">
                    <div class="timeline-date">Latest</div>
                    <div class="timeline-title">Admin Dashboard</div>
                    <div class="timeline-desc">12 pages with full analytics, alerts, reports</div>
                </div>
                <div class="timeline-item recent">
                    <div class="timeline-date">Latest</div>
                    <div class="timeline-title">Smart Model Selection</div>
                    <div class="timeline-desc">Use cheap model when library has matches</div>
                </div>
                <div class="timeline-item recent">
                    <div class="timeline-date">Latest</div>
                    <div class="timeline-title">Cost Tracking</div>
                    <div class="timeline-desc">Per-user costs, forecasting, model breakdown</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">Recent</div>
                    <div class="timeline-title">Code Library</div>
                    <div class="timeline-desc">Component reuse, semantic search, gap analysis</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">Recent</div>
                    <div class="timeline-title">Chat Modifications</div>
                    <div class="timeline-desc">Smart detection of new vs modify requests</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">Recent</div>
                    <div class="timeline-title">Progressive Preview</div>
                    <div class="timeline-desc">Animated build visualization with context</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">Earlier</div>
                    <div class="timeline-title">Sandpack Preview</div>
                    <div class="timeline-desc">Live in-browser code rendering</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">Earlier</div>
                    <div class="timeline-title">Split-Screen UI</div>
                    <div class="timeline-desc">Chat on left, preview on right</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">Earlier</div>
                    <div class="timeline-title">Render Deployment</div>
                    <div class="timeline-desc">Auto-deploy to Render.com</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">Earlier</div>
                    <div class="timeline-title">In-Process Builds</div>
                    <div class="timeline-desc">Removed Celery for faster builds</div>
                </div>
            </div>
        </div>
        
        <!-- Key Features Grid -->
        <div class="section">
            <div class="section-title">🎯 Key Features</div>
            <div class="features-grid">
                <div class="feature new">
                    <div class="feature-title">✨ Real-Time Activity Feed</div>
                    <div class="feature-desc">Live stream of all user actions with auto-refresh</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">✨ Customer Health Scores</div>
                    <div class="feature-desc">0-100 health with churn prediction</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">✨ Conversion Funnel</div>
                    <div class="feature-desc">Visual funnel with drop-off analysis</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">✨ Cohort Retention</div>
                    <div class="feature-desc">Weekly cohort heatmaps</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">✨ Cost Forecasting</div>
                    <div class="feature-desc">7 and 30 day predictions</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">✨ Alert System</div>
                    <div class="feature-desc">Configurable rules with email</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">✨ AI Daily Reports</div>
                    <div class="feature-desc">Auto-generated insights email</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">✨ Component Gap Analysis</div>
                    <div class="feature-desc">Detect missing library components</div>
                </div>
                <div class="feature">
                    <div class="feature-title">Split-Screen Builder</div>
                    <div class="feature-desc">Chat + live preview side by side</div>
                </div>
                <div class="feature">
                    <div class="feature-title">Smart Model Selection</div>
                    <div class="feature-desc">Opus for new, Haiku for reuse</div>
                </div>
                <div class="feature">
                    <div class="feature-title">Code Library</div>
                    <div class="feature-desc">Reusable components with search</div>
                </div>
                <div class="feature">
                    <div class="feature-title">Auto Deployment</div>
                    <div class="feature-desc">Deploy to Render.com automatically</div>
                </div>
            </div>
        </div>
        
        <!-- Database Models -->
        <div class="section">
            <div class="section-title">🗄️ Database Models (15 New)</div>
            <div class="features-grid">
                <div class="feature new">
                    <div class="feature-title">CustomerHealthScore</div>
                    <div class="feature-desc">Health metrics per user</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">Cohort</div>
                    <div class="feature-desc">Weekly/monthly cohorts</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">FunnelSnapshot</div>
                    <div class="feature-desc">Daily funnel metrics</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">AlertRule + Alert</div>
                    <div class="feature-desc">Configurable alerts</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">GeneratedReport</div>
                    <div class="feature-desc">AI summary reports</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">PromptAnalytics</div>
                    <div class="feature-desc">Prompt performance data</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">ActivityFeed</div>
                    <div class="feature-desc">Real-time activity log</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">APIUsageLog</div>
                    <div class="feature-desc">Cost tracking per call</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">ComponentGapAnalysis</div>
                    <div class="feature-desc">Library gaps detection</div>
                </div>
                <div class="feature new">
                    <div class="feature-title">AdminConfig</div>
                    <div class="feature-desc">Global admin settings</div>
                </div>
            </div>
        </div>
    </div>
    
    <div style="text-align: center; margin-top: 60px; color: #64748b; font-size: 14px;">
        <p>Faibric Platform • Built with Django + React + Claude AI</p>
        <p style="margin-top: 8px;">
            <a href="/api/analytics/dashboard/" style="color: #3b82f6; text-decoration: none;">← Back to Dashboard</a>
        </p>
    </div>
</body>
</html>
"""
