import { Box, Typography, IconButton } from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import ProgressivePreview from '../ProgressivePreview'

interface PreviewPanelProps {
  deploymentUrl: string | null
  buildProgress: number
  buildPhase: string
  initialRequest: string
  iframeKey: number
  onRefresh: () => void
}

export function PreviewPanel({
  deploymentUrl,
  buildProgress,
  buildPhase,
  initialRequest,
  iframeKey,
  onRefresh,
}: PreviewPanelProps) {
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
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
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
      <Box sx={{ flex: 1, position: 'relative', overflow: 'hidden', backgroundColor: '#fff' }}>
        {deploymentUrl ? (
          <iframe
            key={`iframe-${deploymentUrl}-${iframeKey}`}
            src={deploymentUrl}
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
    </Box>
  )
}
