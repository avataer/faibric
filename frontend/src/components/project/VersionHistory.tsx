import { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  Button,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert,
} from '@mui/material'
import RestoreIcon from '@mui/icons-material/Restore'
import { api } from '../../services/api'

interface Version {
  id: number
  version: string
  notes: string
  created_at: string
  snapshot: {
    frontend_code?: string
    api_code?: string
    database_schema?: Record<string, unknown>
  }
}

interface VersionHistoryProps {
  projectId: number | string
  onRollback?: () => void
}

export const VersionHistory = ({ projectId, onRollback }: VersionHistoryProps) => {
  const [versions, setVersions] = useState<Version[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedVersion, setSelectedVersion] = useState<Version | null>(null)
  const [rollbackDialog, setRollbackDialog] = useState(false)
  const [rolling, setRolling] = useState(false)

  useEffect(() => {
    fetchVersions()
  }, [projectId])

  const fetchVersions = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get(`/api/projects/${projectId}/versions/`)
      setVersions(response.data || [])
    } catch (err) {
      setError('Failed to load version history')
    }
    setLoading(false)
  }

  const handleRollback = async () => {
    if (!selectedVersion) return
    setRolling(true)
    try {
      await api.post(`/api/projects/${projectId}/rollback/${selectedVersion.id}/`)
      setRollbackDialog(false)
      fetchVersions()
      if (onRollback) onRollback()
    } catch (err) {
      setError('Failed to rollback to selected version')
    }
    setRolling(false)
  }

  const openRollbackDialog = (version: Version) => {
    setSelectedVersion(version)
    setRollbackDialog(true)
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    )
  }

  if (versions.length === 0) {
    return (
      <Alert severity="info">
        No version history yet. Versions are created automatically when you generate or modify your app.
      </Alert>
    )
  }

  return (
    <Box>
      <Typography variant="h6" fontWeight={600} gutterBottom>
        Version History
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        View and restore previous versions of your app.
      </Typography>

      <Paper sx={{ maxHeight: 500, overflow: 'auto' }}>
        <List disablePadding>
          {versions.map((version, index) => (
            <ListItem
              key={version.id}
              sx={{
                borderBottom: '1px solid',
                borderColor: 'divider',
                '&:last-child': { borderBottom: 'none' },
              }}
            >
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="subtitle2" fontWeight={600}>
                      v{version.version}
                    </Typography>
                    {index === 0 && <Chip label="Current" size="small" color="primary" />}
                  </Box>
                }
                secondary={
                  <>
                    <Typography variant="body2" color="text.secondary">
                      {version.notes || 'No description'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(version.created_at).toLocaleString()}
                    </Typography>
                  </>
                }
              />
              {index !== 0 && (
                <Button
                  size="small"
                  startIcon={<RestoreIcon />}
                  onClick={() => openRollbackDialog(version)}
                >
                  Rollback
                </Button>
              )}
            </ListItem>
          ))}
        </List>
      </Paper>

      <Dialog open={rollbackDialog} onClose={() => setRollbackDialog(false)}>
        <DialogTitle>Rollback to Version?</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to rollback to version {selectedVersion?.version}? This will
            restore your app to that previous state and create a new version entry.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRollbackDialog(false)}>Cancel</Button>
          <Button onClick={handleRollback} variant="contained" disabled={rolling}>
            {rolling ? 'Rolling back...' : 'Rollback'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default VersionHistory
