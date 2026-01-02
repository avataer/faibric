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
  Skeleton,
  Alert,
} from '@mui/material'
import RestoreIcon from '@mui/icons-material/Restore'
import { projectServicesApi, Version } from '../../services/projectServices'

interface VersionsPanelProps {
  projectId: number | string
  onRollback?: () => void
}

export const VersionsPanel = ({ projectId, onRollback }: VersionsPanelProps) => {
  const [versions, setVersions] = useState<Version[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedVersion, setSelectedVersion] = useState<Version | null>(null)
  const [rollbackDialog, setRollbackDialog] = useState(false)
  const [rolling, setRolling] = useState(false)
  const [diff, setDiff] = useState<{ added_lines: number; removed_lines: number; diff_html: string } | null>(null)

  useEffect(() => {
    fetchVersions()
  }, [projectId])

  const fetchVersions = async () => {
    setLoading(true)
    try {
      const result = await projectServicesApi.getVersions(projectId)
      setVersions(result.versions || [])
    } catch (error) {
      console.error('Failed to fetch versions:', error)
    }
    setLoading(false)
  }

  const handleViewDiff = async (version: Version) => {
    setSelectedVersion(version)
    if (versions.length > 0 && version.version_number !== versions[0].version_number) {
      try {
        const result = await projectServicesApi.getVersionDiff(
          projectId,
          version.version_number,
          versions[0].version_number
        )
        setDiff(result)
      } catch (error) {
        console.error('Failed to fetch diff:', error)
      }
    } else {
      setDiff(null)
    }
  }

  const handleRollback = async () => {
    if (!selectedVersion) return
    setRolling(true)
    try {
      await projectServicesApi.rollbackVersion(projectId, selectedVersion.version_number)
      setRollbackDialog(false)
      fetchVersions()
      if (onRollback) onRollback()
    } catch (error) {
      console.error('Rollback failed:', error)
    }
    setRolling(false)
  }

  if (loading) {
    return (
      <Box>
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} variant="rounded" height={80} sx={{ mb: 2 }} />
        ))}
      </Box>
    )
  }

  if (versions.length === 0) {
    return (
      <Alert severity="info">
        No version history yet. Versions are created when you make changes to your app.
      </Alert>
    )
  }

  return (
    <Box>
      <Typography variant="h6" fontWeight={600} gutterBottom>
        Version History
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        View changes and restore previous versions of your app.
      </Typography>

      <Box sx={{ display: 'flex', gap: 3 }}>
        {/* Version List */}
        <Paper sx={{ flex: 1, maxHeight: 400, overflow: 'auto' }}>
          <List disablePadding>
            {versions.map((version, index) => (
              <ListItem
                key={version.version_number}
                button
                selected={selectedVersion?.version_number === version.version_number}
                onClick={() => handleViewDiff(version)}
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
                        v{version.version_number}
                      </Typography>
                      {index === 0 && <Chip label="Current" size="small" color="primary" />}
                      {version.is_deployed && <Chip label="Live" size="small" color="success" />}
                    </Box>
                  }
                  secondary={
                    <>
                      <Typography variant="body2" color="text.secondary">
                        {version.change_description}
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
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedVersion(version)
                      setRollbackDialog(true)
                    }}
                  >
                    Restore
                  </Button>
                )}
              </ListItem>
            ))}
          </List>
        </Paper>

        {/* Diff View */}
        <Paper sx={{ flex: 1, p: 3, maxHeight: 400, overflow: 'auto' }}>
          {selectedVersion ? (
            <>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                {selectedVersion.version_number === versions[0]?.version_number
                  ? 'Current Version'
                  : `Changes in v${selectedVersion.version_number}`}
              </Typography>
              {diff ? (
                <>
                  <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                    <Chip
                      label={`+${diff.added_lines} added`}
                      size="small"
                      sx={{ bgcolor: '#dcfce7', color: '#166534' }}
                    />
                    <Chip
                      label={`-${diff.removed_lines} removed`}
                      size="small"
                      sx={{ bgcolor: '#fee2e2', color: '#991b1b' }}
                    />
                  </Box>
                  <Box
                    sx={{
                      fontFamily: 'monospace',
                      fontSize: '12px',
                      bgcolor: '#f8fafc',
                      p: 2,
                      borderRadius: 1,
                      overflow: 'auto',
                      '& .diff-added': { bgcolor: '#dcfce7', display: 'block' },
                      '& .diff-removed': { bgcolor: '#fee2e2', display: 'block' },
                      '& .diff-hunk': { color: '#6366f1', display: 'block' },
                    }}
                    dangerouslySetInnerHTML={{ __html: diff.diff_html }}
                  />
                </>
              ) : (
                <Box sx={{ fontFamily: 'monospace', fontSize: '12px', bgcolor: '#f8fafc', p: 2, borderRadius: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    {selectedVersion.code_preview}
                  </Typography>
                </Box>
              )}
            </>
          ) : (
            <Typography color="text.secondary">Select a version to view details</Typography>
          )}
        </Paper>
      </Box>

      {/* Rollback Confirmation Dialog */}
      <Dialog open={rollbackDialog} onClose={() => setRollbackDialog(false)}>
        <DialogTitle>Restore Version?</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to restore to version {selectedVersion?.version_number}? This will
            create a new version with the old code.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRollbackDialog(false)}>Cancel</Button>
          <Button onClick={handleRollback} variant="contained" disabled={rolling}>
            {rolling ? 'Restoring...' : 'Restore'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default VersionsPanel


