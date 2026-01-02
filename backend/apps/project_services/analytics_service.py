"""
Built-in Analytics Service
Lightweight tracking without third-party dependencies.
"""
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class AnalyticsSummary:
    total_pageviews: int
    total_visitors: int
    pageviews_today: int
    visitors_today: int
    top_pages: List[Dict[str, Any]]
    traffic_sources: Dict[str, int]
    pageviews_by_day: List[Dict[str, Any]]


class AnalyticsService:
    """
    Manages analytics tracking and reporting for projects.
    """
    
    def generate_tracking_script(self, project_id: str, api_endpoint: str) -> str:
        """
        Generate a lightweight tracking script to embed in projects.
        Under 1KB minified.
        """
        return f'''
// Faibric Analytics - Lightweight tracking (< 1KB)
(function() {{
  const PROJECT_ID = "{project_id}";
  const ENDPOINT = "{api_endpoint}";
  
  // Generate or retrieve visitor ID
  const getVisitorId = () => {{
    let vid = localStorage.getItem("_fvid");
    if (!vid) {{
      vid = Math.random().toString(36).substring(2) + Date.now().toString(36);
      localStorage.setItem("_fvid", vid);
    }}
    return vid;
  }};
  
  // Generate session ID
  const getSessionId = () => {{
    let sid = sessionStorage.getItem("_fsid");
    if (!sid) {{
      sid = Math.random().toString(36).substring(2);
      sessionStorage.setItem("_fsid", sid);
    }}
    return sid;
  }};
  
  // Track event
  const track = (eventType, data = {{}}) => {{
    const payload = {{
      project_id: PROJECT_ID,
      event_type: eventType,
      path: window.location.pathname,
      visitor_id: getVisitorId(),
      session_id: getSessionId(),
      referrer: document.referrer,
      timestamp: new Date().toISOString(),
      ...data
    }};
    
    // Use sendBeacon for reliability
    if (navigator.sendBeacon) {{
      navigator.sendBeacon(ENDPOINT, JSON.stringify(payload));
    }} else {{
      fetch(ENDPOINT, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
        keepalive: true
      }}).catch(() => {{}});
    }}
  }};
  
  // Auto-track pageviews
  track("pageview");
  
  // Track SPA navigation
  let lastPath = window.location.pathname;
  const observer = new MutationObserver(() => {{
    if (window.location.pathname !== lastPath) {{
      lastPath = window.location.pathname;
      track("pageview");
    }}
  }});
  observer.observe(document.body, {{ childList: true, subtree: true }});
  
  // Expose for custom events
  window.faibricTrack = (event, data) => track(event, data);
}})();
'''
    
    def generate_analytics_dashboard_code(self) -> str:
        """
        Generate React code for an analytics dashboard component.
        """
        return '''
// Analytics Dashboard Component
const AnalyticsDashboard = ({ projectId }) => {
  const [data, setData] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [timeRange, setTimeRange] = React.useState("7d");
  
  React.useEffect(() => {
    const fetchAnalytics = async () => {
      setLoading(true);
      try {
        const response = await fetch(`/api/analytics/${projectId}?range=${timeRange}`);
        const result = await response.json();
        setData(result);
      } catch (err) {
        console.error("Failed to fetch analytics:", err);
      }
      setLoading(false);
    };
    
    fetchAnalytics();
    // Refresh every 5 minutes
    const interval = setInterval(fetchAnalytics, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [projectId, timeRange]);
  
  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[1,2,3,4].map(i => <div key={i} className="h-24 bg-gray-200 rounded"></div>)}
        </div>
      </div>
    );
  }
  
  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Analytics</h2>
        <select 
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          className="border rounded px-3 py-2"
        >
          <option value="24h">Last 24 hours</option>
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
        </select>
      </div>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard 
          title="Page Views" 
          value={data?.total_pageviews || 0} 
          change={data?.pageviews_change}
        />
        <StatCard 
          title="Visitors" 
          value={data?.total_visitors || 0}
          change={data?.visitors_change}
        />
        <StatCard 
          title="Avg. Session" 
          value={formatDuration(data?.avg_session_duration || 0)}
        />
        <StatCard 
          title="Bounce Rate" 
          value={`${data?.bounce_rate || 0}%`}
        />
      </div>
      
      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-semibold mb-4">Traffic Over Time</h3>
          <SimpleLineChart data={data?.pageviews_by_day || []} />
        </div>
        
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-semibold mb-4">Top Pages</h3>
          <ul className="space-y-2">
            {(data?.top_pages || []).slice(0, 5).map((page, i) => (
              <li key={i} className="flex justify-between py-2 border-b">
                <span className="text-gray-700 truncate">{page.path}</span>
                <span className="text-gray-500">{page.views} views</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};

// Helper Components
const StatCard = ({ title, value, change }) => (
  <div className="bg-white p-4 rounded-lg shadow">
    <p className="text-gray-500 text-sm">{title}</p>
    <p className="text-2xl font-bold">{typeof value === "number" ? value.toLocaleString() : value}</p>
    {change !== undefined && (
      <p className={`text-sm ${change >= 0 ? "text-green-500" : "text-red-500"}`}>
        {change >= 0 ? "+" : ""}{change}%
      </p>
    )}
  </div>
);

const formatDuration = (seconds) => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs}s`;
};

const SimpleLineChart = ({ data }) => {
  if (!data.length) return <div className="h-40 flex items-center justify-center text-gray-400">No data</div>;
  
  const max = Math.max(...data.map(d => d.views));
  const height = 160;
  
  return (
    <svg className="w-full" height={height} viewBox={`0 0 ${data.length * 40} ${height}`}>
      <polyline
        fill="none"
        stroke="#4F46E5"
        strokeWidth="2"
        points={data.map((d, i) => `${i * 40 + 20},${height - (d.views / max) * (height - 20) - 10}`).join(" ")}
      />
      {data.map((d, i) => (
        <circle
          key={i}
          cx={i * 40 + 20}
          cy={height - (d.views / max) * (height - 20) - 10}
          r="4"
          fill="#4F46E5"
        />
      ))}
    </svg>
  );
};
'''
    
    def calculate_summary(self, events: List[Dict], time_range: str = '7d') -> AnalyticsSummary:
        """
        Calculate analytics summary from raw events.
        """
        now = datetime.utcnow()
        
        # Parse time range
        if time_range == '24h':
            start = now - timedelta(hours=24)
        elif time_range == '7d':
            start = now - timedelta(days=7)
        elif time_range == '30d':
            start = now - timedelta(days=30)
        else:
            start = now - timedelta(days=90)
        
        # Filter events
        filtered = [e for e in events if e.get('timestamp', now) >= start]
        
        # Calculate metrics
        pageviews = [e for e in filtered if e.get('event_type') == 'pageview']
        visitors = set(e.get('visitor_id') for e in filtered)
        
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        pageviews_today = len([e for e in pageviews if e.get('timestamp', now) >= today])
        visitors_today = len(set(e.get('visitor_id') for e in filtered if e.get('timestamp', now) >= today))
        
        # Top pages
        page_counts = {}
        for e in pageviews:
            path = e.get('path', '/')
            page_counts[path] = page_counts.get(path, 0) + 1
        
        top_pages = sorted(
            [{'path': k, 'views': v} for k, v in page_counts.items()],
            key=lambda x: x['views'],
            reverse=True
        )[:10]
        
        # Traffic sources
        sources = {}
        for e in filtered:
            referrer = e.get('referrer', '')
            if referrer:
                domain = referrer.split('/')[2] if '//' in referrer else 'direct'
            else:
                domain = 'direct'
            sources[domain] = sources.get(domain, 0) + 1
        
        # Pageviews by day
        daily = {}
        for e in pageviews:
            day = e.get('timestamp', now).strftime('%Y-%m-%d')
            daily[day] = daily.get(day, 0) + 1
        
        pageviews_by_day = [{'date': k, 'views': v} for k, v in sorted(daily.items())]
        
        return AnalyticsSummary(
            total_pageviews=len(pageviews),
            total_visitors=len(visitors),
            pageviews_today=pageviews_today,
            visitors_today=visitors_today,
            top_pages=top_pages,
            traffic_sources=sources,
            pageviews_by_day=pageviews_by_day
        )


# Singleton
analytics_service = AnalyticsService()


