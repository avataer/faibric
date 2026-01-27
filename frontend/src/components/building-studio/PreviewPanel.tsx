import { useState, useRef, useEffect, useCallback } from 'react'
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
  Snackbar,
  Alert,
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import EditIcon from '@mui/icons-material/Edit'
import TouchAppIcon from '@mui/icons-material/TouchApp'
import ProgressivePreview from '../ProgressivePreview'
import PropertyPanel from '../builder/PropertyPanel'

interface PreviewPanelProps {
  deploymentUrl: string | null
  buildProgress: number
  buildPhase: string
  initialRequest: string
  iframeKey: number
  onRefresh: () => void
  onEditRequest?: (editRequest: string) => void
}

interface PropertyValue {
  text?: string
  src?: string
  backgroundColor?: string
  color?: string
  fontSize?: number
}

interface SelectedElement {
  selector: string
  elementType: string
  currentValue: PropertyValue
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

  // Advanced visual editing state
  const [selectedElement, setSelectedElement] = useState<SelectedElement | null>(null)
  const [showPropertyPanel, setShowPropertyPanel] = useState(false)
  const [editSuccess, setEditSuccess] = useState<string | null>(null)
  const iframeRef = useRef<HTMLIFrameElement | null>(null)

  // Handle messages from iframe (element selection)
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const data = event.data
      if (!data || !data.type) return

      if (data.type === 'element_click' && editMode) {
        // Element was clicked - show property panel
        let parsedValue: PropertyValue = {}
        if (data.elementType === 'text' || data.elementType === 'button') {
          parsedValue = { text: data.currentValue || '' }
        } else if (data.elementType === 'image') {
          parsedValue = { src: data.currentValue || '' }
        }

        setSelectedElement({
          selector: data.selector,
          elementType: data.elementType,
          currentValue: parsedValue,
        })
        setShowPropertyPanel(true)
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [editMode])

  // Enable/disable visual editing in iframe
  useEffect(() => {
    if (iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        { type: editMode ? 'enable_visual_editing' : 'disable_visual_editing' },
        '*'
      )
    }
  }, [editMode, deploymentUrl])

  // Apply edit via PropertyPanel
  const handlePropertyApply = useCallback(async (newValue: PropertyValue) => {
    if (!selectedElement || !onEditRequest) return

    // Build edit request from property changes
    let editRequest = ''
    if (selectedElement.elementType === 'text' || selectedElement.elementType === 'button') {
      const oldText = selectedElement.currentValue.text || ''
      const newText = newValue.text || ''
      if (oldText !== newText) {
        editRequest = `Change the text "${oldText.slice(0, 50)}" to "${newText}"`
      }
    } else if (selectedElement.elementType === 'image') {
      editRequest = `Change the image to use URL: ${newValue.src}`
    }

    if (editRequest) {
      onEditRequest(editRequest)
      setEditSuccess('Edit applied! Building changes...')
    }

    // Reset state
    setShowPropertyPanel(false)
    setSelectedElement(null)
    setEditMode(false)
  }, [selectedElement, onEditRequest])

  const handlePropertyCancel = useCallback(() => {
    setShowPropertyPanel(false)
    setSelectedElement(null)
    // Clear highlight in iframe
    if (iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage({ type: 'clear_highlight' }, '*')
    }
  }, [])

  // Fallback: click position based editing
  const handlePreviewClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!editMode || !deploymentUrl) return

    // Only use position-based dialog if no element was selected via postMessage
    if (showPropertyPanel) return

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
        {/* Edit mode hint - floating above iframe */}
        {editMode && deploymentUrl && (
          <Box
            sx={{
              position: 'absolute',
              top: 16,
              left: '50%',
              transform: 'translateX(-50%)',
              zIndex: 20,
              bgcolor: '#2563eb',
              color: 'white',
              px: 3,
              py: 1.5,
              borderRadius: 2,
              boxShadow: 3,
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              pointerEvents: 'none',
            }}
          >
            <TouchAppIcon />
            <Typography fontWeight={600}>
              Click any element to edit it directly
            </Typography>
          </Box>
        )}

        {/* Edit mode border indicator */}
        {editMode && deploymentUrl && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 5,
              border: '3px dashed #2563eb',
              pointerEvents: 'none',
            }}
          />
        )}

        {deploymentUrl ? (
          <iframe
            ref={iframeRef}
            key={`iframe-${deploymentUrl}-${iframeKey}`}
            src={deploymentUrl}
            onLoad={() => {
              // Enable visual editing if already in edit mode
              if (editMode && iframeRef.current?.contentWindow) {
                iframeRef.current.contentWindow.postMessage(
                  { type: 'enable_visual_editing' },
                  '*'
                )
              }
            }}
            style={{
              width: '100%',
              height: '100%',
              border: 'none',
              backgroundColor: '#fff',
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

      {/* Advanced Property Panel for direct element editing */}
      {showPropertyPanel && selectedElement && (
        <PropertyPanel
          elementType={selectedElement.elementType}
          currentValue={selectedElement.currentValue}
          onApply={handlePropertyApply}
          onCancel={handlePropertyCancel}
        />
      )}

      {/* Success notification */}
      <Snackbar
        open={!!editSuccess}
        autoHideDuration={3000}
        onClose={() => setEditSuccess(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="success" onClose={() => setEditSuccess(null)}>
          {editSuccess}
        </Alert>
      </Snackbar>
    </Box>
  )
}
