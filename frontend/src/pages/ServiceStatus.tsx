import { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Alert,
} from '@mui/material'
import { api } from '../services/api'

interface ServiceInfo {
  provider: string
  mock: boolean
  keys_needed: string[]
}

interface TestResult {
  success: boolean
  mock: boolean
  [key: string]: any
}

const ServiceStatus = () => {
  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState(false)
  const [services, setServices] = useState<Record<string, ServiceInfo>>({})
  const [summary, setSummary] = useState({ total_services: 0, mock_mode: 0, live_mode: 0 })
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadStatus()
  }, [])

  const loadStatus = async () => {
    setLoading(true)
    try {
      const res = await api.get('/api/services/status/')
      setServices(res.data.services)
      setSummary(res.data.summary)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load service status')
    } finally {
      setLoading(false)
    }
  }

  const runTests = async () => {
    setTesting(true)
    try {
      const res = await api.post('/api/services/test/', { service: 'all' })
      setTestResults(res.data.results)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to run tests')
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4, bgcolor: '#ffffff' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ color: '#000000', fontWeight: 700 }}>
            External Services Status
          </Typography>
          <Typography variant="body1" sx={{ color: '#374151' }}>
            API keys and mock mode status
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" onClick={loadStatus}>
            Refresh
          </Button>
          <Button 
            variant="contained" 
            onClick={runTests}
            disabled={testing}
          >
            {testing ? 'Testing...' : 'Run All Tests'}
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>{error}</Alert>
      )}

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h3" sx={{ color: '#000000' }}>{summary.total_services}</Typography>
              <Typography sx={{ color: '#374151' }}>Total Services</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h3" sx={{ color: '#d97706' }}>{summary.mock_mode}</Typography>
              <Typography sx={{ color: '#374151' }}>Mock Mode</Typography>
              <Typography variant="caption" sx={{ color: '#6b7280' }}>No API keys needed for testing</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h3" sx={{ color: '#16a34a' }}>{summary.live_mode}</Typography>
              <Typography sx={{ color: '#374151' }}>Live Mode</Typography>
              <Typography variant="caption" sx={{ color: '#6b7280' }}>API keys configured</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Alert for mock mode */}
      {summary.mock_mode > 0 && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <strong>{summary.mock_mode} service(s) running in mock mode.</strong> The system returns realistic fake data for testing.
          Add API keys to enable live mode.
        </Alert>
      )}

      {/* Services Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ color: '#000000', mb: 2 }}>Service Details</Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Service</TableCell>
                  <TableCell>Provider</TableCell>
                  <TableCell>Mode</TableCell>
                  <TableCell>Required Keys</TableCell>
                  <TableCell>Test Result</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {Object.entries(services).map(([name, info]) => (
                  <TableRow key={name}>
                    <TableCell>
                      <Typography sx={{ fontWeight: 600, color: '#000000', textTransform: 'capitalize' }}>
                        {name.replace('_', ' ')}
                      </Typography>
                    </TableCell>
                    <TableCell>{info.provider}</TableCell>
                    <TableCell>
                      {info.mock ? (
                        <Chip 
                          label="Mock Mode" 
                          color="warning" 
                          size="small" 
                        />
                      ) : (
                        <Chip 
                          label="Live" 
                          color="success" 
                          size="small" 
                        />
                      )}
                    </TableCell>
                    <TableCell>
                      {info.keys_needed.map((key) => (
                        <Chip 
                          key={key} 
                          label={key} 
                          size="small" 
                          variant="outlined"
                          sx={{ mr: 0.5, mb: 0.5, fontFamily: 'monospace', fontSize: 11 }}
                        />
                      ))}
                    </TableCell>
                    <TableCell>
                      {testResults[name] ? (
                        testResults[name].success ? (
                          <Chip 
                            label={testResults[name].mock ? "Mock OK" : "Live OK"} 
                            color="success" 
                            size="small" 
                          />
                        ) : (
                          <Chip label="Failed" color="error" size="small" />
                        )
                      ) : (
                        <Typography variant="caption" sx={{ color: '#6b7280' }}>Not tested</Typography>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Test Results Detail */}
      {Object.keys(testResults).length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ color: '#000000', mb: 2 }}>Test Results</Typography>
            <Grid container spacing={2}>
              {Object.entries(testResults).map(([name, result]) => (
                <Grid item xs={12} md={6} key={name}>
                  <Paper sx={{ p: 2, border: '1px solid #e5e7eb' }}>
                    <Typography variant="subtitle2" sx={{ color: '#000000', textTransform: 'capitalize', mb: 1 }}>
                      {name.replace('_', ' ')}
                    </Typography>
                    <Box sx={{ fontFamily: 'monospace', fontSize: 12, color: '#374151' }}>
                      {Object.entries(result).map(([key, value]) => (
                        <Box key={key}>
                          <strong>{key}:</strong> {typeof value === 'string' ? value.substring(0, 100) : JSON.stringify(value)}
                        </Box>
                      ))}
                    </Box>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Instructions */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ color: '#000000', mb: 2 }}>How to Add API Keys</Typography>
          <Typography variant="body2" sx={{ color: '#374151', mb: 1 }}>
            1. Create a .env file in the backend directory
          </Typography>
          <Typography variant="body2" sx={{ color: '#374151', mb: 1 }}>
            2. Add the required API keys (see API_KEYS_CONFIG.md)
          </Typography>
          <Typography variant="body2" sx={{ color: '#374151', mb: 1 }}>
            3. Restart the backend: docker-compose restart backend
          </Typography>
          <Typography variant="body2" sx={{ color: '#374151' }}>
            4. Refresh this page to verify the services are now in live mode
          </Typography>
        </CardContent>
      </Card>
    </Container>
  )
}

export default ServiceStatus
