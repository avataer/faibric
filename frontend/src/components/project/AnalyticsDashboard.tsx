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
  Skeleton,
} from '@mui/material'
import { projectServicesApi, AnalyticsData } from '../../services/projectServices'

interface AnalyticsDashboardProps {
  projectId: number | string
}

const StatCard = ({ title, value, subtitle }: { title: string; value: string | number; subtitle?: string }) => (
  <Paper sx={{ p: 3, height: '100%' }}>
    <Typography variant="body2" color="text.secondary" gutterBottom>
      {title}
    </Typography>
    <Typography variant="h4" fontWeight={700}>
      {typeof value === 'number' ? value.toLocaleString() : value}
    </Typography>
    {subtitle && (
      <Typography variant="caption" color="text.secondary">
        {subtitle}
      </Typography>
    )}
  </Paper>
)

const SimpleChart = ({ data }: { data: { date: string; views: number }[] }) => {
  if (!data || data.length === 0) {
    return (
      <Box sx={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="text.secondary">No data yet</Typography>
      </Box>
    )
  }

  const max = Math.max(...data.map((d) => d.views), 1)
  const width = 100 / data.length

  return (
    <Box sx={{ height: 200, display: 'flex', alignItems: 'flex-end', gap: 0.5, px: 1 }}>
      {data.map((d, i) => (
        <Box
          key={i}
          sx={{
            width: `${width}%`,
            height: `${(d.views / max) * 100}%`,
            minHeight: 4,
            bgcolor: 'primary.main',
            borderRadius: '4px 4px 0 0',
            transition: 'height 0.3s',
            '&:hover': {
              bgcolor: 'primary.dark',
            },
          }}
          title={`${d.date}: ${d.views} views`}
        />
      ))}
    </Box>
  )
}

export const AnalyticsDashboard = ({ projectId }: AnalyticsDashboardProps) => {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState('7d')

  useEffect(() => {
    const fetchAnalytics = async () => {
      setLoading(true)
      try {
        const result = await projectServicesApi.getAnalytics(projectId, timeRange)
        setData(result)
      } catch (error) {
        console.error('Failed to fetch analytics:', error)
      }
      setLoading(false)
    }

    fetchAnalytics()
    const interval = setInterval(fetchAnalytics, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [projectId, timeRange])

  if (loading) {
    return (
      <Box>
        <Grid container spacing={3}>
          {[1, 2, 3, 4].map((i) => (
            <Grid item xs={6} md={3} key={i}>
              <Skeleton variant="rounded" height={100} />
            </Grid>
          ))}
        </Grid>
      </Box>
    )
  }

  return (
    <Box>
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
          <StatCard
            title="Total Pageviews"
            value={data?.total_pageviews || 0}
            subtitle={`${data?.pageviews_today || 0} today`}
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            title="Unique Visitors"
            value={data?.total_visitors || 0}
            subtitle={`${data?.visitors_today || 0} today`}
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            title="Avg. per Day"
            value={
              data?.pageviews_by_day?.length
                ? Math.round(
                    data.pageviews_by_day.reduce((sum, d) => sum + d.views, 0) /
                      data.pageviews_by_day.length
                  )
                : 0
            }
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard title="Top Pages" value={data?.top_pages?.length || 0} subtitle="unique pages" />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Traffic Over Time
            </Typography>
            <SimpleChart data={data?.pageviews_by_day || []} />
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1, px: 1 }}>
              {data?.pageviews_by_day?.slice(0, 7).map((d, i) => (
                <Typography key={i} variant="caption" color="text.secondary">
                  {new Date(d.date).toLocaleDateString('en', { weekday: 'short' })}
                </Typography>
              ))}
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Top Pages
            </Typography>
            {data?.top_pages?.length ? (
              <Box>
                {data.top_pages.slice(0, 5).map((page, i) => (
                  <Box
                    key={i}
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      py: 1,
                      borderBottom: '1px solid',
                      borderColor: 'divider',
                    }}
                  >
                    <Typography variant="body2" sx={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {page.path}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {page.views}
                    </Typography>
                  </Box>
                ))}
              </Box>
            ) : (
              <Typography color="text.secondary" variant="body2">
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

