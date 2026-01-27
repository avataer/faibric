import { useState } from 'react'
import {
  Box,
  Typography,
  IconButton,
  ToggleButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Tooltip,
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import EditIcon from '@mui/icons-material/Edit'
import TouchAppIcon from '@mui/icons-material/TouchApp'
import ProgressivePreview from '../ProgressivePreview'

interface PreviewPanelProps {
  deploymentUrl: string | null
  buildProgress: number
  buildPhase: string
  initialRequest: string
  iframeKey: number
  onRefresh: () => void
  onEditRequest?: (editRequest: string) => void
}

export function PreviewPanel({
  deploymentUrl,
  buildProgress,
  buildPhase,
  initialRequest,
  iframeKey,
  onRefresh,
  onEditRequest,
}: PreviewPanelProps) {
  const [editMode, setEditMode] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editText, setEditText] = useState('')
  const [clickPosition, setClickPosition] = useState<{ x: number; y: number } | null>(null)

  const handlePreviewClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!editMode || !deploymentUrl) return

    // Get click position relative to the preview area
    const rect = e.currentTarget.getBoundingClientRect()
    const x = Math.round(((e.clientX - rect.left) / rect.width) * 100)
    const y = Math.round(((e.clientY - rect.top) / rect.height) * 100)

    setClickPosition({ x, y })
    setEditDialogOpen(true)
  }

  const handleEditSubmit = () => {
    if (!editText.trim()) return

    // Add position context to the edit request
    const positionHint = clickPosition
      ? ` (clicked at approximately ${clickPosition.x}% from left, ${clickPosition.y}% from top of the page)`
      : ''

    const fullRequest = editText + positionHint

    if (onEditRequest) {
      onEditRequest(fullRequest)
    }

    // Reset state
    setEditDialogOpen(false)
    setEditText('')
    setClickPosition(null)
    setEditMode(false)
  }

  const handleDialogClose = () => {
    setEditDialogOpen(false)
    setEditText('')
    setClickPosition(null)
  }

  return (
    <Box sx={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: '#f9fafb',
    }}>
      {/* Preview Header */}
      <Box sx={{
        p: 2,
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: '#ffffff',
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="subtitle1" fontWeight={500}>
            Live Preview
          </Typography>
          {editMode && (
            <Typography
              variant="caption"
              sx={{
                bgcolor: '#2563eb',
                color: 'white',
                px: 1,
                py: 0.5,
                borderRadius: 1,
                fontWeight: 600,
              }}
            >
              EDIT MODE - Click anywhere to modify
            </Typography>
          )}
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {deploymentUrl && (
            <Tooltip title={editMode ? "Exit Edit Mode" : "Click-to-Edit Mode"}>
              <ToggleButton
                value="edit"
                selected={editMode}
                onChange={() => setEditMode(!editMode)}
                size="small"
                sx={{
                  border: editMode ? '2px solid #2563eb' : '1px solid #e0e0e0',
                  bgcolor: editMode ? '#eff6ff' : 'transparent',
                }}
              >
                <TouchAppIcon sx={{ color: editMode ? '#2563eb' : 'inherit' }} />
              </ToggleButton>
            </Tooltip>
          )}
          <IconButton size="small" onClick={onRefresh} title="Refresh preview">
            <RefreshIcon />
          </IconButton>
          {deploymentUrl && (
            <IconButton
              size="small"
              onClick={() => window.open(deploymentUrl, '_blank')}
              title="Open in new tab"
            >
              <OpenInNewIcon />
            </IconButton>
          )}
        </Box>
      </Box>

      {/* Preview Content */}
      <Box
        sx={{
          flex: 1,
          position: 'relative',
          overflow: 'hidden',
          backgroundColor: '#fff',
          cursor: editMode ? 'crosshair' : 'default',
        }}
        onClick={handlePreviewClick}
      >
        {/* Edit mode overlay */}
        {editMode && deploymentUrl && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 10,
              backgroundColor: 'rgba(37, 99, 235, 0.05)',
              border: '3px dashed #2563eb',
              pointerEvents: 'auto',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Box
              sx={{
                position: 'absolute',
                top: 16,
                left: '50%',
                transform: 'translateX(-50%)',
                bgcolor: '#2563eb',
                color: 'white',
                px: 3,
                py: 1.5,
                borderRadius: 2,
                boxShadow: 3,
                display: 'flex',
                alignItems: 'center',
                gap: 1,
              }}
            >
              <TouchAppIcon />
              <Typography fontWeight={600}>
                Click anywhere on the preview to edit that area
              </Typography>
            </Box>
          </Box>
        )}

        {deploymentUrl ? (
          <iframe
            key={`iframe-${deploymentUrl}-${iframeKey}`}
            src={deploymentUrl}
            style={{
              width: '100%',
              height: '100%',
              border: 'none',
              backgroundColor: '#fff',
              pointerEvents: editMode ? 'none' : 'auto',
            }}
            title="Your Deployed Website"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          />
        ) : (
          <ProgressivePreview
            progress={buildProgress}
            phase={buildPhase}
            projectName={initialRequest.slice(0, 30)}
            userRequest={initialRequest}
          />
        )}
      </Box>

      {/* Edit Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={handleDialogClose}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <EditIcon color="primary" />
          What would you like to change?
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Describe the change you want to make to this part of the page.
          </Typography>
          <TextField
            autoFocus
            fullWidth
            multiline
            rows={3}
            placeholder="e.g., Change the heading to 'Welcome to My Site', make the button blue, add a phone number..."
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleEditSubmit()
              }
            }}
          />
          {clickPosition && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Clicked at: {clickPosition.x}% from left, {clickPosition.y}% from top
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogClose}>Cancel</Button>
          <Button
            onClick={handleEditSubmit}
            variant="contained"
            disabled={!editText.trim()}
          >
            Apply Change
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
