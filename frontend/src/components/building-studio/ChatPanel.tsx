import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  IconButton,
  CircularProgress,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import StopIcon from '@mui/icons-material/Stop'
import RefreshIcon from '@mui/icons-material/Refresh'
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline'
import { Message } from './types'

interface ModelOption {
  key: string
  name: string
  credits_per_request: number
}

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
  onRetry?: () => void
  models?: ModelOption[]
  selectedModel?: string
  onModelChange?: (modelKey: string) => void
  modelsLoading?: boolean
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
  onRetry,
  models = [],
  selectedModel = '',
  onModelChange,
  modelsLoading = false,
}: ChatPanelProps) {
  // Check if the last message is an error
  const lastMessage = messages[messages.length - 1]
  const hasError = lastMessage?.content?.startsWith('Error:') ?? false
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
        {messages.map((msg) => {
          const isError = msg.content?.startsWith('Error:')
          const isLastError = isError && msg.id === lastMessage?.id

          return (
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
                    isError ? '#fef2f2' :
                    msg.role === 'user' ? '#3b82f6' :
                    msg.role === 'system' ? '#f3f4f6' : '#ffffff',
                  color: isError ? '#dc2626' : msg.role === 'user' ? '#ffffff' : '#000000',
                  border: isError ? '1px solid #fca5a5' :
                    msg.role === 'assistant' ? '1px solid #e5e7eb' : 'none',
                }}
                elevation={msg.role === 'system' ? 0 : 1}
              >
                {isError ? (
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <ErrorOutlineIcon fontSize="small" />
                      <Typography variant="body2" fontWeight={600}>
                        Something went wrong
                      </Typography>
                    </Box>
                    <Typography variant="body2" sx={{ mb: isLastError ? 2 : 0 }}>
                      {msg.content.replace('Error: ', '')}
                    </Typography>
                    {isLastError && onRetry && (
                      <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                        <Button
                          size="small"
                          variant="contained"
                          color="error"
                          startIcon={<RefreshIcon />}
                          onClick={onRetry}
                        >
                          Try Again
                        </Button>
                        <Typography variant="caption" sx={{ color: '#9ca3af', alignSelf: 'center' }}>
                          or describe a simpler request
                        </Typography>
                      </Box>
                    )}
                  </Box>
                ) : msg.role === 'system' ? (
                  <Typography variant="body2" sx={{ fontStyle: 'italic', color: '#6b7280' }}>
                    {msg.content}
                  </Typography>
                ) : (
                  <Typography variant="body1">{msg.content}</Typography>
                )}
              </Paper>
            </Box>
          )
        })}
        <div ref={messagesEndRef} />
      </Box>

      {/* Input */}
      <Box sx={{
        p: 2,
        borderTop: '1px solid #e5e7eb',
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
      }}>
        {/* Model Selector */}
        {models.length > 0 && onModelChange && (
          <FormControl size="small" fullWidth>
            <InputLabel id="model-select-label">AI Model</InputLabel>
            <Select
              labelId="model-select-label"
              id="model-select"
              value={selectedModel}
              label="AI Model"
              onChange={(e) => onModelChange(e.target.value)}
              disabled={isBuilding || modelsLoading}
            >
              {models.map((model) => (
                <MenuItem key={model.key} value={model.key}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                    <Typography variant="body2">{model.name}</Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                      {model.credits_per_request} credit{model.credits_per_request !== 1 ? 's' : ''}
                    </Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
        <Box sx={{ display: 'flex', gap: 1 }}>
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
    </Box>
  )
}
