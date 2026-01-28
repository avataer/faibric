import { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material'
import GitHubIcon from '@mui/icons-material/GitHub'
import SyncIcon from '@mui/icons-material/Sync'
import CloudDownloadIcon from '@mui/icons-material/CloudDownload'
import { api } from '../../services/api'

interface GitHubSyncProps {
  projectId: number | string
}

interface SyncStatus {
  connected: boolean
  last_sha?: string
  has_updates?: boolean
  latest_sha?: string
}

export const GitHubSync = ({ projectId }: GitHubSyncProps) => {
  const [repoUrl, setRepoUrl] = useState('')
  const [status, setStatus] = useState<SyncStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    fetchStatus()
  }, [projectId])

  const fetchStatus = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get(`/api/projects/${projectId}/github_status/`)
      setStatus(response.data)
    } catch (err) {
      setError('Failed to load GitHub sync status')
    }
    setLoading(false)
  }

  const handleConnect = async () => {
    setError(null)
    setSuccess(null)
    setSyncing(true)
    try {
      await api.patch(`/api/projects/${projectId}/`, { github_repo: repoUrl })
      await fetchStatus()
      setSuccess('Repository connected successfully')
    } catch (err) {
      setError('Failed to connect repository')
    }
    setSyncing(false)
  }

  const handlePull = async () => {
    setError(null)
    setSuccess(null)
    setSyncing(true)
    try {
      await api.post(`/api/projects/${projectId}/github_pull/`)
      await fetchStatus()
      setSuccess('Changes pulled successfully')
    } catch (err) {
      setError('Failed to pull changes from GitHub')
    }
    setSyncing(false)
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <GitHubIcon />
        <Typography variant="h6" fontWeight={600}>
          GitHub Sync
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Connect your project to a GitHub repository to sync changes.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {!status?.connected ? (
        <Box>
          <TextField
            fullWidth
            label="GitHub Repository URL"
            placeholder="https://github.com/username/repo"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            sx={{ mb: 2 }}
          />
          <Button
            variant="contained"
            startIcon={syncing ? <CircularProgress size={20} /> : <GitHubIcon />}
            onClick={handleConnect}
            disabled={!repoUrl || syncing}
          >
            {syncing ? 'Connecting...' : 'Connect Repository'}
          </Button>
        </Box>
      ) : (
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Chip
              label="Connected"
              color="success"
              size="small"
              icon={<SyncIcon />}
            />
          </Box>

          {status.last_sha && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Last sync: {status.last_sha.substring(0, 8)}
            </Typography>
          )}

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
            <Typography variant="body2">Sync Status:</Typography>
            {status.has_updates ? (
              <Chip label="Updates Available" color="warning" size="small" />
            ) : (
              <Chip label="Up to date" color="success" size="small" />
            )}
          </Box>

          <Button
            variant="contained"
            startIcon={syncing ? <CircularProgress size={20} /> : <CloudDownloadIcon />}
            onClick={handlePull}
            disabled={!status.has_updates || syncing}
          >
            {syncing ? 'Pulling...' : 'Pull Changes'}
          </Button>
        </Box>
      )}
    </Paper>
  )
}

export default GitHubSync
