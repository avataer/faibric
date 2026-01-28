import { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Divider,
} from '@mui/material'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { projectServicesApi, AnalyticsData } from '../../services/projectServices'
import {
  analyticsService,
  EventStats,
  Funnel,
  FunnelStats,
} from '../../services/analyticsService'

interface AnalyticsDashboardProps {
  projectId: number | string
}

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  loading?: boolean
}

const MetricCard = ({ title, value, subtitle, loading }: MetricCardProps) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        {title}
      </Typography>
      {loading ? (
        <CircularProgress size={24} />
      ) : (
        <>
          <Typography variant="h4" fontWeight={700}>
            {typeof value === 'number' ? value.toLocaleString() : value}
          </Typography>
          {subtitle && (
            <Typography variant="caption" color="text.secondary">
              {subtitle}
            </Typography>
          )}
        </>
      )}
    </CardContent>
  </Card>
)

interface FunnelVisualizationProps {
  stats: FunnelStats | null
  loading: boolean
}

const FunnelVisualization = ({ stats, loading }: FunnelVisualizationProps) => {
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (!stats || !stats.steps || stats.steps.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ py: 2 }}>
        No funnel data available
      </Typography>
    )
  }

  const maxEntered = Math.max(...stats.steps.map((s) => s.entered), 1)

  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Overall Conversion: {stats.overall_conversion_rate.toFixed(1)}%
        </Typography>
      </Box>
      {stats.steps.map((step, index) => {
        const widthPercent = (step.entered / maxEntered) * 100
        return (
          <Box key={index} sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
              <Typography variant="body2" fontWeight={500}>
                {step.step_name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {step.entered.toLocaleString()} users ({step.conversion_rate.toFixed(1)}%)
              </Typography>
            </Box>
            <Box
              sx={{
                width: `${widthPercent}%`,
                minWidth: '20%',
                height: 32,
                bgcolor: 'primary.main',
                borderRadius: 1,
                transition: 'width 0.3s ease',
              }}
            />
            {index < stats.steps.length - 1 && (
              <Typography variant="caption" color="error.main" sx={{ mt: 0.5, display: 'block' }}>
                Drop-off: {step.drop_off_rate.toFixed(1)}%
              </Typography>
            )}
          </Box>
        )
      })}
    </Box>
  )
}

export const AnalyticsDashboard = ({ projectId }: AnalyticsDashboardProps) => {
  const [pageviewData, setPageviewData] = useState<AnalyticsData | null>(null)
  const [eventStats, setEventStats] = useState<EventStats | null>(null)
  const [funnels, setFunnels] = useState<Funnel[]>([])
  const [selectedFunnel, setSelectedFunnel] = useState<number | ''>('')
  const [funnelStats, setFunnelStats] = useState<FunnelStats | null>(null)
  const [timeRange, setTimeRange] = useState('7d')
  const [loading, setLoading] = useState({
    pageviews: true,
    events: true,
    funnels: true,
    funnelStats: false,
  })
  const [error, setError] = useState<string | null>(null)

  const getDaysFromRange = (range: string): number => {
    switch (range) {
      case '24h':
        return 1
      case '7d':
        return 7
      case '30d':
        return 30
      case '90d':
        return 90
      default:
        return 7
    }
  }

  useEffect(() => {
    const fetchPageviews = async () => {
      setLoading((prev) => ({ ...prev, pageviews: true }))
      try {
        const result = await projectServicesApi.getAnalytics(projectId, timeRange)
        setPageviewData(result)
      } catch {
        setError('Failed to load pageview data')
      }
      setLoading((prev) => ({ ...prev, pageviews: false }))
    }

    const fetchEventStats = async () => {
      setLoading((prev) => ({ ...prev, events: true }))
      try {
        const days = getDaysFromRange(timeRange)
        const result = await analyticsService.getEventStats(days)
        setEventStats(result)
      } catch {
        // Event stats may not be available for all projects
      }
      setLoading((prev) => ({ ...prev, events: false }))
    }

    const fetchFunnels = async () => {
      setLoading((prev) => ({ ...prev, funnels: true }))
      try {
        const result = await analyticsService.getFunnels()
        setFunnels(result)
        if (result.length > 0 && selectedFunnel === '') {
          setSelectedFunnel(result[0].id)
        }
      } catch {
        // Funnels may not be available
      }
      setLoading((prev) => ({ ...prev, funnels: false }))
    }

    fetchPageviews()
    fetchEventStats()
    fetchFunnels()

    const interval = setInterval(() => {
      fetchPageviews()
      fetchEventStats()
    }, 60000)
    return () => clearInterval(interval)
  }, [projectId, timeRange])

  useEffect(() => {
    const fetchFunnelStats = async () => {
      if (!selectedFunnel) {
        setFunnelStats(null)
        return
      }

      setLoading((prev) => ({ ...prev, funnelStats: true }))
      try {
        const days = getDaysFromRange(timeRange)
        const result = await analyticsService.getFunnelStats(selectedFunnel as number, days)
        setFunnelStats(result)
      } catch {
        setFunnelStats(null)
      }
      setLoading((prev) => ({ ...prev, funnelStats: false }))
    }

    fetchFunnelStats()
  }, [selectedFunnel, timeRange])

  const isLoading = loading.pageviews && loading.events

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  const chartData =
    eventStats?.by_day?.map((item) => ({
      date: new Date(item.date).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
      events: item.count,
    })) ||
    pageviewData?.pageviews_by_day?.map((item) => ({
      date: new Date(item.date).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
      events: item.views,
    })) ||
    []

  const eventBreakdownData =
    eventStats?.by_event_name?.slice(0, 10).map((item) => ({
      name: item.event_name.length > 15 ? item.event_name.substring(0, 15) + '...' : item.event_name,
      fullName: item.event_name,
      count: item.count,
    })) || []

  const conversionRate =
    funnelStats?.overall_conversion_rate ??
    (pageviewData?.total_visitors && pageviewData?.total_pageviews
      ? ((pageviewData.total_visitors / pageviewData.total_pageviews) * 100)
      : 0)

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" fontWeight={600}>
          Analytics
        </Typography>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Time Range</InputLabel>
          <Select
            value={timeRange}
            label="Time Range"
            onChange={(e) => setTimeRange(e.target.value)}
          >
            <MenuItem value="24h">Last 24 hours</MenuItem>
            <MenuItem value="7d">Last 7 days</MenuItem>
            <MenuItem value="30d">Last 30 days</MenuItem>
            <MenuItem value="90d">Last 90 days</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={6} md={3}>
          <MetricCard
            title="Total Events"
            value={eventStats?.total_events ?? pageviewData?.total_pageviews ?? 0}
            subtitle={`${pageviewData?.pageviews_today ?? 0} today`}
            loading={loading.events && loading.pageviews}
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <MetricCard
            title="Unique Users"
            value={eventStats?.unique_users ?? pageviewData?.total_visitors ?? 0}
            subtitle={`${pageviewData?.visitors_today ?? 0} today`}
            loading={loading.events && loading.pageviews}
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <MetricCard
            title="Conversion Rate"
            value={`${conversionRate.toFixed(1)}%`}
            subtitle={funnelStats ? 'Funnel completion' : 'Visitor ratio'}
            loading={loading.funnelStats}
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <MetricCard
            title="Avg Events/Day"
            value={
              chartData.length > 0
                ? Math.round(chartData.reduce((sum, d) => sum + d.events, 0) / chartData.length)
                : 0
            }
            subtitle={`Over ${timeRange}`}
            loading={loading.events && loading.pageviews}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Events Over Time
            </Typography>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="events"
                    stroke="#1976d2"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <Box
                sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <Typography color="text.secondary">No event data available</Typography>
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Event Breakdown
            </Typography>
            {eventBreakdownData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={eventBreakdownData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={100} />
                  <Tooltip
                    formatter={(value: number) => [value.toLocaleString(), 'Count']}
                    labelFormatter={(label: string) => {
                      const item = eventBreakdownData.find((d) => d.name === label)
                      return item?.fullName || label
                    }}
                  />
                  <Bar dataKey="count" fill="#1976d2" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Box
                sx={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <Typography color="text.secondary">No event breakdown available</Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="subtitle1" fontWeight={600}>
                Funnel Analysis
              </Typography>
              {funnels.length > 0 && (
                <FormControl size="small" sx={{ minWidth: 200 }}>
                  <InputLabel>Select Funnel</InputLabel>
                  <Select
                    value={selectedFunnel}
                    label="Select Funnel"
                    onChange={(e) => setSelectedFunnel(e.target.value as number)}
                  >
                    {funnels.map((funnel) => (
                      <MenuItem key={funnel.id} value={funnel.id}>
                        {funnel.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}
            </Box>
            <Divider sx={{ mb: 2 }} />
            {loading.funnels ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
              </Box>
            ) : funnels.length === 0 ? (
              <Typography color="text.secondary" sx={{ py: 2 }}>
                No funnels configured. Create a funnel to track user conversion.
              </Typography>
            ) : (
              <FunnelVisualization stats={funnelStats} loading={loading.funnelStats} />
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Top Pages
            </Typography>
            {pageviewData?.top_pages?.length ? (
              <Box>
                {pageviewData.top_pages.slice(0, 8).map((page, i) => (
                  <Box
                    key={i}
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      py: 1.5,
                      borderBottom: i < 7 ? '1px solid' : 'none',
                      borderColor: 'divider',
                    }}
                  >
                    <Typography
                      variant="body2"
                      sx={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxWidth: '70%',
                      }}
                      title={page.path}
                    >
                      {page.path}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" fontWeight={500}>
                      {page.views.toLocaleString()}
                    </Typography>
                  </Box>
                ))}
              </Box>
            ) : (
              <Typography color="text.secondary" variant="body2" sx={{ py: 2 }}>
                No page data yet
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}

export default AnalyticsDashboard
