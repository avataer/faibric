import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  IconButton,
  CircularProgress,
  Chip,
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import StopIcon from '@mui/icons-material/Stop'
import { Message } from './types'

interface ChatPanelProps {
  messages: Message[]
  messagesEndRef: React.RefObject<HTMLDivElement>
  isBuilding: boolean
  isStopping: boolean
  buildProgress: number
  input: string
  onInputChange: (value: string) => void
  onSend: () => void
  onStop: () => void
  onNewProject?: () => void
}

export function ChatPanel({
  messages,
  messagesEndRef,
  isBuilding,
  isStopping,
  buildProgress,
  input,
  onInputChange,
  onSend,
  onStop,
  onNewProject,
}: ChatPanelProps) {
  return (
    <Box sx={{
      width: '40%',
      minWidth: 400,
      display: 'flex',
      flexDirection: 'column',
      borderRight: '1px solid #e5e7eb',
      backgroundColor: '#ffffff',
    }}>
      {/* Header */}
      <Box sx={{
        p: 2,
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <Typography variant="h6" fontWeight={600}>
          Faibric Studio
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          {isBuilding ? (
            <>
              <Chip
                label={`Building... ${buildProgress}%`}
                color="primary"
                size="small"
                icon={<CircularProgress size={14} color="inherit" />}
              />
              <Button
                variant="outlined"
                color="error"
                size="small"
                startIcon={<StopIcon />}
                onClick={onStop}
                disabled={isStopping}
                sx={{ ml: 1 }}
              >
                {isStopping ? 'Stopping...' : 'Stop'}
              </Button>
            </>
          ) : (
            <Chip
              label="Deployed"
              color="success"
              size="small"
            />
          )}
          {onNewProject && (
            <Button
              variant="outlined"
              size="small"
              onClick={onNewProject}
              sx={{ ml: 1 }}
            >
              Start New
            </Button>
          )}
        </Box>
      </Box>

      {/* Messages */}
      <Box sx={{
        flex: 1,
        overflow: 'auto',
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
      }}>
        {messages.map((msg) => (
          <Box
            key={msg.id}
            sx={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <Paper
              sx={{
                p: 2,
                maxWidth: '80%',
                backgroundColor:
                  msg.role === 'user' ? '#3b82f6' :
                  msg.role === 'system' ? '#f3f4f6' : '#ffffff',
                color: msg.role === 'user' ? '#ffffff' : '#000000',
                border: msg.role === 'assistant' ? '1px solid #e5e7eb' : 'none',
              }}
              elevation={msg.role === 'system' ? 0 : 1}
            >
              {msg.role === 'system' ? (
                <Typography variant="body2" sx={{ fontStyle: 'italic', color: '#6b7280' }}>
                  {msg.content}
                </Typography>
              ) : (
                <Typography variant="body1">{msg.content}</Typography>
              )}
            </Paper>
          </Box>
        ))}
        <div ref={messagesEndRef} />
      </Box>

      {/* Input */}
      <Box sx={{
        p: 2,
        borderTop: '1px solid #e5e7eb',
        display: 'flex',
        gap: 1,
      }}>
        <TextField
          fullWidth
          placeholder={isBuilding ? "Building in progress..." : "Describe changes or request a new website..."}
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && !isBuilding && onSend()}
          size="small"
          disabled={isBuilding}
        />
        <IconButton
          color="primary"
          onClick={onSend}
          disabled={!input.trim() || isBuilding}
        >
          <SendIcon />
        </IconButton>
      </Box>
    </Box>
  )
}
