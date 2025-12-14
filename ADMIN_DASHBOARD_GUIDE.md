# Faibric Admin Dashboard Guide

## Overview

The Faibric Admin Dashboard is a comprehensive analytics and monitoring system for the AI website builder platform. It provides real-time insights into user behavior, costs, system health, and operational metrics.

**Main URL:** `http://localhost:8000/api/analytics/dashboard/`

---

## Dashboard Pages

### 1. Overview (`/api/analytics/dashboard/`)
The main landing page showing:
- **Live stats**: Active users, building now, queue depth
- **Today's metrics**: Users, deploys, costs
- **Activity feed**: Real-time stream of user actions
- **At-risk users**: Users with low health scores

Auto-refreshes every 30 seconds.

### 2. Live Activity (`/api/analytics/dashboard/activity/`)
Real-time event stream showing:
- New users joining
- Builds starting/completing/failing
- Deployments
- Errors and alerts

Auto-refreshes every 10 seconds.

### 3. Users (`/api/analytics/dashboard/users/`)
Complete user list with:
- Email and initial request
- Current status
- API calls count
- Total cost per user
- Click any row to see full details

### 4. User Detail (`/api/analytics/dashboard/user/{session_token}`)
Deep dive into individual users:
- All messages sent
- Complete event log
- API usage with token counts
- Health score breakdown
- Link to deployed site
- **Operational buttons**: Retry Build, Force Redeploy

### 5. Health Scores (`/api/analytics/dashboard/health/`)
Customer health monitoring:
- **Healthy (70+)**: Green - engaged, successful builds
- **At Risk (40-69)**: Yellow - declining engagement
- **Churning (<40)**: Red - likely to abandon

Score components:
- Build success rate (30%)
- Engagement score (25%)
- Return rate (20%)
- Feature adoption (15%)
- Satisfaction score (10%)

### 6. Funnel (`/api/analytics/dashboard/funnel/`)
Conversion funnel visualization:
```
Visitors → Requests → Emails → Verified → Builds → Deployed
```
- Per-stage conversion rates
- Drop-off analysis
- Daily breakdown table
- 7-day aggregates

### 7. Cohorts (`/api/analytics/dashboard/cohorts/`)
Retention analysis by weekly cohort:
- Users grouped by signup week
- Retention % for weeks 0-4
- Conversion rates per cohort
- Color-coded heatmap

### 8. Costs (`/api/analytics/dashboard/costs/`)
Complete cost analysis:
- Total spend (30 days)
- Daily cost breakdown
- Cost by model (Opus vs Haiku)
- **7-day forecast**
- **30-day forecast**
- Cost optimization insights

### 9. Components (`/api/analytics/dashboard/components/`)
Code library gallery:
- All stored components
- Usage count per component
- Quality scores
- Code previews

### 10. Prompt Analytics (`/api/analytics/dashboard/prompts/`)
AI prompt performance:
- Total prompts processed
- Success rate
- Average generation time
- Library usage rate
- Breakdown by site type
- Breakdown by industry

### 11. Alerts (`/api/analytics/dashboard/alerts/`)
Alert management:
- Active alerts with severity
- Alert history
- Configured rules
- Trigger counts

Default alert rules:
| Rule | Metric | Threshold |
|------|--------|-----------|
| High Daily Cost | daily_cost | > $50 |
| Error Rate Spike | error_rate | > 15% |
| Build Queue Backup | build_queue | > 10 |
| Slow Builds | build_time | > 120s |

### 12. Reports (`/api/analytics/dashboard/reports/`)
AI-generated reports:
- Daily summaries
- Key metrics snapshot
- AI insights and recommendations
- Email delivery status

### 13. Settings (`/api/analytics/dashboard/settings/`)
Admin configuration:
- Admin email: `amptiness@icloud.com`
- Alert thresholds
- Daily report schedule
- Notification preferences

---

## Smart Model Selection

The system uses different AI models to optimize costs:

| Task | Model | Cost per Million Tokens |
|------|-------|------------------------|
| Classification | Claude Haiku 3.5 | $0.80 / $4 |
| Summaries | Claude Haiku 3.5 | $0.80 / $4 |
| Reusing library code | Claude Haiku 3.5 | $0.80 / $4 |
| **New code generation** | Claude Opus 4.5 | $15 / $75 |

When library has similar components → Uses cheap model to customize
When generating from scratch → Uses expensive model

---

## API Endpoints

### Action Endpoints

```bash
# Recalculate all health scores
POST /api/analytics/dashboard/health/recalculate/

# Generate daily report and send email
POST /api/analytics/dashboard/reports/generate/

# Run all daily tasks
POST /api/analytics/dashboard/run-daily/

# Retry a failed build
POST /api/analytics/dashboard/user/{session_token}/retry/

# Force redeploy a project
POST /api/analytics/dashboard/user/{session_token}/redeploy/
```

---

## Database Models

### Analytics Models
- `APIUsageLog` - Every AI API call with tokens and cost
- `UserSummary` - AI-generated user profiles

### Dashboard Models
- `CustomerHealthScore` - Health metrics per user
- `UserSegment` - User groupings
- `Cohort` - Weekly/monthly cohorts
- `FunnelSnapshot` - Daily funnel metrics
- `AlertRule` - Configurable alert rules
- `Alert` - Triggered alert instances
- `ScheduledReport` - Report configurations
- `GeneratedReport` - Generated report content
- `PromptAnalytics` - Prompt performance data
- `AIInsight` - AI-generated insights
- `ActivityFeed` - Real-time activity log
- `SystemMetric` - System health metrics
- `BuildQueueItem` - Build queue tracking
- `ComponentGapAnalysis` - Library gaps
- `AdminConfig` - Global configuration

---

## Notifications

Alerts and reports are sent to: **amptiness@icloud.com**

Email notifications include:
- Alert triggers (cost, errors, queue)
- Daily summary reports
- Critical system events

---

## Running Daily Tasks

To calculate all metrics manually:

```bash
curl -X POST http://localhost:8000/api/analytics/dashboard/run-daily/
```

This runs:
1. Calculate yesterday's funnel snapshot
2. Recalculate all health scores
3. Update weekly cohorts
4. Analyze component gaps
5. Generate AI daily summary
6. Send report email
7. Check all alert rules

---

## Accessing the Dashboard

**Local:** http://localhost:8000/api/analytics/dashboard/

**Production (Render):** https://your-app.onrender.com/api/analytics/dashboard/

No authentication required (add authentication for production!)
