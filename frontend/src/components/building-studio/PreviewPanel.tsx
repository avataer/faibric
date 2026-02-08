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
import DashboardCustomizeIcon from '@mui/icons-material/DashboardCustomize'
import ViewQuiltIcon from '@mui/icons-material/ViewQuilt'
import LanguageIcon from '@mui/icons-material/Language'
import WebIcon from '@mui/icons-material/Web'
import ProgressivePreview from '../ProgressivePreview'
import PropertyPanel from '../builder/PropertyPanel'
import type { Section } from '../builder/sectionTypes'

interface PreviewPanelProps {
  deploymentUrl: string | null
  buildProgress: number
  buildPhase: string
  initialRequest: string
  iframeKey: number
  aiUnavailable?: boolean
  onRefresh: () => void
  onEditRequest?: (editRequest: string) => void
  sections?: Section[]
  sectionEditorOpen?: boolean
  onToggleSectionEditor?: () => void
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
  aiUnavailable = false,
  onRefresh,
  onEditRequest,
  sections = [],
  sectionEditorOpen = false,
  onToggleSectionEditor,
}: PreviewPanelProps) {
  const [editMode, setEditMode] = useState(false)
  const [sectionEditMode, setSectionEditMode] = useState(false)
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

  // Send section data to iframe when section edit mode changes
  useEffect(() => {
    if (iframeRef.current && iframeRef.current.contentWindow) {
      if (sectionEditMode) {
        iframeRef.current.contentWindow.postMessage(
          { type: 'enable_section_editing', sections },
          '*'
        )
      } else {
        iframeRef.current.contentWindow.postMessage(
          { type: 'disable_section_editing' },
          '*'
        )
      }
    }
  }, [sectionEditMode, sections])

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
      backgroundColor: '#f5f5f5',
    }}>
      {/* Browser Chrome */}
      <Box sx={{
        backgroundColor: '#fff',
        borderBottom: '1px solid #e5e7eb',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
      }}>
        {/* Top bar with traffic lights, URL bar, and actions */}
        <Box sx={{
          px: 2,
          py: 1,
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
        }}>
          {/* Traffic light dots */}
          <Box sx={{ display: 'flex', gap: 0.75, flexShrink: 0, alignItems: 'center' }}>
            <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#ff5f57', border: '0.5px solid rgba(0,0,0,0.12)' }} />
            <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#febc2e', border: '0.5px solid rgba(0,0,0,0.12)' }} />
            <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#28c840', border: '0.5px solid rgba(0,0,0,0.12)' }} />
          </Box>

          {/* URL bar */}
          <Box sx={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            backgroundColor: '#f5f5f5',
            border: '1px solid #e5e7eb',
            borderRadius: 2,
            px: 1.5,
            py: 0.5,
            gap: 1,
            minWidth: 0,
          }}>
            <LanguageIcon sx={{ fontSize: 14, color: '#9ca3af', flexShrink: 0 }} />
            <Typography
              variant="body2"
              sx={{
                color: '#6b7280',
                fontSize: '0.75rem',
                fontFamily: '"SF Mono", "Fira Code", "Fira Mono", Menlo, monospace',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {deploymentUrl || 'about:blank'}
            </Typography>
          </Box>

          {/* Browser action buttons */}
          <Box sx={{ display: 'flex', gap: 0.5, flexShrink: 0 }}>
            <Tooltip title="Refresh preview">
              <IconButton
                size="small"
                onClick={onRefresh}
                sx={{
                  width: 30,
                  height: 30,
                  color: '#6b7280',
                  '&:hover': { backgroundColor: '#e5e7eb', color: '#374151' },
                }}
              >
                <RefreshIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </Tooltip>
            {deploymentUrl && (
              <Tooltip title="Open in new tab">
                <IconButton
                  size="small"
                  onClick={() => window.open(deploymentUrl, '_blank')}
                  sx={{
                    width: 30,
                    height: 30,
                    color: '#6b7280',
                    '&:hover': { backgroundColor: '#e5e7eb', color: '#374151' },
                  }}
                >
                  <OpenInNewIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Box>

        {/* Toolbar row: edit mode, section editor, status badges */}
        <Box sx={{
          px: 2,
          pb: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {editMode && (
              <Typography
                variant="caption"
                sx={{
                  bgcolor: '#2563eb',
                  color: 'white',
                  px: 1,
                  py: 0.25,
                  borderRadius: 1,
                  fontWeight: 600,
                  fontSize: '0.65rem',
                }}
              >
                EDIT MODE
              </Typography>
            )}
            {sectionEditMode && (
              <Typography
                variant="caption"
                sx={{
                  bgcolor: '#7c3aed',
                  color: 'white',
                  px: 1,
                  py: 0.25,
                  borderRadius: 1,
                  fontWeight: 600,
                  fontSize: '0.65rem',
                }}
              >
                SECTION MODE
              </Typography>
            )}
          </Box>
          <Box sx={{ display: 'flex', gap: 0.75 }}>
            {deploymentUrl && (
              <Tooltip title={editMode ? "Exit Edit Mode" : "Click-to-Edit Mode"}>
                <ToggleButton
                  value="edit"
                  selected={editMode}
                  onChange={() => setEditMode(!editMode)}
                  size="small"
                  sx={{
                    width: 30,
                    height: 30,
                    border: editMode ? '2px solid #2563eb' : '1px solid #d1d5db',
                    bgcolor: editMode ? '#eff6ff' : 'transparent',
                  }}
                >
                  <TouchAppIcon sx={{ fontSize: 16, color: editMode ? '#2563eb' : '#6b7280' }} />
                </ToggleButton>
              </Tooltip>
            )}
            {deploymentUrl && (
              <Tooltip title={sectionEditMode ? "Exit Section Edit Mode" : "Section Edit Mode"}>
                <ToggleButton
                  value="sectionEdit"
                  selected={sectionEditMode}
                  onChange={() => setSectionEditMode(!sectionEditMode)}
                  size="small"
                  sx={{
                    width: 30,
                    height: 30,
                    border: sectionEditMode ? '2px solid #7c3aed' : '1px solid #d1d5db',
                    bgcolor: sectionEditMode ? '#f5f3ff' : 'transparent',
                  }}
                >
                  <ViewQuiltIcon sx={{ fontSize: 16, color: sectionEditMode ? '#7c3aed' : '#6b7280' }} />
                </ToggleButton>
              </Tooltip>
            )}
            {onToggleSectionEditor && (
              <Button
                size="small"
                variant={sectionEditorOpen ? "contained" : "outlined"}
                onClick={onToggleSectionEditor}
                startIcon={<DashboardCustomizeIcon sx={{ fontSize: 14 }} />}
                sx={{
                  textTransform: 'none',
                  fontSize: '0.7rem',
                  minWidth: 'auto',
                  px: 1.25,
                  py: 0.25,
                  height: 30,
                  ...(sectionEditorOpen ? {
                    backgroundColor: '#3b82f6',
                    color: '#ffffff',
                    '&:hover': { backgroundColor: '#2563eb' },
                  } : {
                    borderColor: '#d1d5db',
                    color: '#6b7280',
                    '&:hover': { backgroundColor: '#f3f4f6' },
                  }),
                }}
              >
                {sectionEditorOpen ? "Close" : "Sections"}
              </Button>
            )}
          </Box>
        </Box>
      </Box>

      {/* Preview Content */}
      <Box
        sx={{
          flex: 1,
          position: 'relative',
          overflow: 'hidden',
          m: 1.5,
          borderRadius: 2.5,
          border: '1px solid #e5e7eb',
          boxShadow: '0 4px 24px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04)',
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

        {/* Section edit mode border indicator */}
        {sectionEditMode && deploymentUrl && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 5,
              border: '3px dashed #7c3aed',
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
        ) : aiUnavailable ? (
          <Box sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            gap: 3,
            p: 4,
            backgroundColor: '#fff',
          }}>
            <DashboardCustomizeIcon sx={{ fontSize: 64, color: '#94a3b8' }} />
            <Typography variant="h5" fontWeight={600} color="text.primary" textAlign="center">
              AI build service is currently unavailable
            </Typography>
            <Typography variant="body1" color="text.secondary" textAlign="center" maxWidth={480}>
              You can use the Section Editor to manually build your page by adding, reordering, and customizing sections. Click the Section Editor button above to get started.
            </Typography>
            {onToggleSectionEditor && !sectionEditorOpen && (
              <Button
                variant="contained"
                startIcon={<DashboardCustomizeIcon />}
                onClick={onToggleSectionEditor}
                sx={{ textTransform: 'none', mt: 1 }}
              >
                Open Section Editor
              </Button>
            )}
          </Box>
        ) : buildProgress === 0 && !buildPhase ? (
          <Box sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            gap: 2.5,
            p: 4,
            backgroundColor: '#fff',
          }}>
            <WebIcon sx={{
              fontSize: 56,
              color: '#d1d5db',
              '@keyframes gentle-pulse': {
                '0%, 100%': { opacity: 0.6 },
                '50%': { opacity: 1 },
              },
              animation: 'gentle-pulse 2.5s ease-in-out infinite',
            }} />
            <Typography variant="h6" sx={{ fontWeight: 500, color: '#6b7280' }} textAlign="center">
              Your website preview will appear here
            </Typography>
            <Typography variant="body2" sx={{ color: '#9ca3af', maxWidth: 360 }} textAlign="center">
              Describe what you want to build in the chat and we will generate a live preview for you.
            </Typography>
          </Box>
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
