import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  IconButton,
  LinearProgress,
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
import ViewQuiltIcon from '@mui/icons-material/ViewQuilt'
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'
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

function formatTimestamp(date: Date): string {
  const hours = date.getHours()
  const minutes = date.getMinutes()
  const ampm = hours >= 12 ? 'PM' : 'AM'
  const h = hours % 12 || 12
  const m = minutes.toString().padStart(2, '0')
  return `${h}:${m} ${ampm}`
}

function shouldShowTimestamp(current: Message, previous: Message | undefined): boolean {
  if (!previous) return true
  const diff = new Date(current.timestamp).getTime() - new Date(previous.timestamp).getTime()
  return diff > 120000
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
        px: 2.5,
        py: 2,
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: '#ffffff',
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AutoAwesomeIcon sx={{ color: '#1976d2', fontSize: 22 }} />
          <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.1rem', color: '#111827' }}>
            Faibric Studio
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          {isBuilding ? (
            <>
              <Chip
                label="Building"
                size="small"
                sx={{
                  backgroundColor: '#eff6ff',
                  color: '#1976d2',
                  fontWeight: 600,
                  fontSize: '0.75rem',
                  '& .MuiChip-icon': { color: '#1976d2' },
                  '@keyframes pulse-dot': {
                    '0%, 100%': { opacity: 1 },
                    '50%': { opacity: 0.4 },
                  },
                  '&::before': {
                    content: '""',
                    display: 'inline-block',
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    backgroundColor: '#1976d2',
                    marginRight: '6px',
                    animation: 'pulse-dot 1.2s ease-in-out infinite',
                  },
                }}
              />
              <Button
                variant="outlined"
                color="error"
                size="small"
                startIcon={<StopIcon />}
                onClick={onStop}
                disabled={isStopping}
                sx={{
                  ml: 0.5,
                  textTransform: 'none',
                  fontSize: '0.75rem',
                  borderRadius: 1.5,
                }}
              >
                {isStopping ? 'Stopping...' : 'Stop'}
              </Button>
            </>
          ) : (
            <Chip
              label="Ready"
              size="small"
              sx={{
                backgroundColor: '#f0fdf4',
                color: '#16a34a',
                fontWeight: 600,
                fontSize: '0.75rem',
              }}
            />
          )}
          {onNewProject && (
            <Button
              variant="outlined"
              size="small"
              onClick={onNewProject}
              sx={{
                ml: 0.5,
                textTransform: 'none',
                fontSize: '0.75rem',
                borderRadius: 1.5,
                borderColor: '#d1d5db',
                color: '#374151',
                '&:hover': {
                  borderColor: '#9ca3af',
                  backgroundColor: '#f9fafb',
                },
              }}
            >
              New Project
            </Button>
          )}
        </Box>
      </Box>

      {/* Build Progress Bar */}
      {isBuilding && (
        <Box sx={{ px: 2.5, py: 1.5, backgroundColor: '#f8f9fa' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="caption" sx={{ color: '#6b7280', fontWeight: 500 }}>
              Building your website...
            </Typography>
            <Typography variant="caption" sx={{ color: '#1976d2', fontWeight: 600 }}>
              {buildProgress}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={buildProgress}
            sx={{
              height: 5,
              borderRadius: 2,
              backgroundColor: '#e5e7eb',
              '& .MuiLinearProgress-bar': {
                borderRadius: 2,
                backgroundColor: '#1976d2',
                '@keyframes shimmer': {
                  '0%': { opacity: 1 },
                  '50%': { opacity: 0.7 },
                  '100%': { opacity: 1 },
                },
                animation: 'shimmer 1.5s ease-in-out infinite',
              },
            }}
          />
        </Box>
      )}

      {/* Messages */}
      <Box sx={{
        flex: 1,
        overflow: 'auto',
        px: 2,
        py: 2,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        backgroundColor: '#f8f9fa',
      }}>
        {messages.map((msg, index) => {
          const isError = msg.content?.startsWith('Error:')
          const isLastError = isError && msg.id === lastMessage?.id
          const previousMessage = index > 0 ? messages[index - 1] : undefined
          const showTimestamp = shouldShowTimestamp(msg, previousMessage)

          return (
            <Box key={msg.id}>
              {/* Timestamp separator */}
              {showTimestamp && (
                <Box sx={{
                  display: 'flex',
                  justifyContent: 'center',
                  my: 1,
                }}>
                  <Typography
                    variant="caption"
                    sx={{
                      color: '#9ca3af',
                      fontSize: '0.7rem',
                      letterSpacing: '0.02em',
                    }}
                  >
                    {formatTimestamp(new Date(msg.timestamp))}
                  </Typography>
                </Box>
              )}

              {/* Message bubble */}
              <Box
                sx={{
                  display: 'flex',
                  justifyContent:
                    msg.role === 'system' ? 'center' :
                    msg.role === 'user' ? 'flex-end' : 'flex-start',
                  mb: 0.5,
                }}
              >
                {msg.role === 'system' ? (
                  /* System messages: subtle centered style */
                  <Box sx={{ maxWidth: '90%' }}>
                    {isError ? (
                      <Paper
                        elevation={0}
                        sx={{
                          p: 2,
                          backgroundColor: '#fef2f2',
                          border: '1px solid #fecaca',
                          borderRadius: 2.5,
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <ErrorOutlineIcon sx={{ fontSize: 18, color: '#dc2626' }} />
                          <Typography variant="body2" sx={{ fontWeight: 600, color: '#dc2626' }}>
                            Something went wrong
                          </Typography>
                        </Box>
                        <Typography variant="body2" sx={{ color: '#991b1b', mb: isLastError ? 1.5 : 0 }}>
                          {msg.content.replace('Error: ', '')}
                        </Typography>
                        {isLastError && onRetry && (
                          <Box sx={{ display: 'flex', gap: 1, mt: 1, alignItems: 'center' }}>
                            <Button
                              size="small"
                              variant="contained"
                              startIcon={<RefreshIcon />}
                              onClick={onRetry}
                              sx={{
                                textTransform: 'none',
                                borderRadius: 1.5,
                                backgroundColor: '#dc2626',
                                '&:hover': { backgroundColor: '#b91c1c' },
                                fontSize: '0.75rem',
                              }}
                            >
                              Try Again
                            </Button>
                            <Typography variant="caption" sx={{ color: '#9ca3af' }}>
                              or describe a simpler request
                            </Typography>
                          </Box>
                        )}
                      </Paper>
                    ) : msg.content.toLowerCase().includes('section') ? (
                      <Box sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 0.75,
                        px: 1.5,
                        py: 0.5,
                      }}>
                        <ViewQuiltIcon sx={{ fontSize: 14, color: '#7c3aed' }} />
                        <Typography variant="caption" sx={{ fontStyle: 'italic', color: '#7c3aed', fontSize: '0.75rem' }}>
                          {msg.content}
                        </Typography>
                      </Box>
                    ) : (
                      <Typography variant="caption" sx={{
                        fontStyle: 'italic',
                        color: '#9ca3af',
                        fontSize: '0.75rem',
                        px: 1.5,
                        py: 0.5,
                      }}>
                        {msg.content}
                      </Typography>
                    )}
                  </Box>
                ) : (
                  /* User and Assistant messages */
                  <Paper
                    elevation={0}
                    sx={{
                      px: 2,
                      py: 1.5,
                      maxWidth: '80%',
                      borderRadius: msg.role === 'user'
                        ? '16px 16px 4px 16px'
                        : '16px 16px 16px 4px',
                      backgroundColor:
                        msg.role === 'user' ? '#1976d2' : '#f5f5f5',
                      color:
                        msg.role === 'user' ? '#ffffff' : '#1f2937',
                      border: msg.role === 'assistant' ? '1px solid #ebebeb' : 'none',
                      boxShadow: msg.role === 'assistant'
                        ? '0 1px 3px rgba(0,0,0,0.04)'
                        : '0 1px 3px rgba(25,118,210,0.2)',
                    }}
                  >
                    <Typography
                      variant="body2"
                      sx={{
                        lineHeight: 1.5,
                        fontSize: '0.875rem',
                      }}
                    >
                      {msg.content}
                    </Typography>
                  </Paper>
                )}
              </Box>
            </Box>
          )
        })}
        <div ref={messagesEndRef} />
      </Box>

      {/* Input Area */}
      <Box sx={{
        p: 2,
        borderTop: '1px solid #e5e7eb',
        backgroundColor: '#ffffff',
        display: 'flex',
        flexDirection: 'column',
        gap: 1.5,
      }}>
        {/* Model Selector - compact */}
        {models.length > 0 && onModelChange && (
          <FormControl
            size="small"
            fullWidth
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 1.5,
                fontSize: '0.8rem',
                backgroundColor: '#f9fafb',
                '& fieldset': { borderColor: '#e5e7eb' },
                '&:hover fieldset': { borderColor: '#d1d5db' },
              },
              '& .MuiInputLabel-root': {
                fontSize: '0.8rem',
              },
            }}
          >
            <InputLabel id="model-select-label">Model</InputLabel>
            <Select
              labelId="model-select-label"
              id="model-select"
              value={selectedModel}
              label="Model"
              onChange={(e) => onModelChange(e.target.value)}
              disabled={isBuilding || modelsLoading}
            >
              {models.map((model) => (
                <MenuItem key={model.key} value={model.key}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                    <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>{model.name}</Typography>
                    <Typography variant="caption" sx={{ color: '#9ca3af', ml: 2, fontSize: '0.7rem' }}>
                      {model.credits_per_request} credit{model.credits_per_request !== 1 ? 's' : ''}
                    </Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}

        {/* Text input + send button */}
        <Box sx={{
          display: 'flex',
          gap: 1,
          alignItems: 'flex-end',
          backgroundColor: '#f9fafb',
          borderRadius: 3,
          border: '1px solid #e5e7eb',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          px: 2,
          py: 1,
          transition: 'border-color 0.2s, box-shadow 0.2s',
          '&:focus-within': {
            borderColor: '#1976d2',
            boxShadow: '0 2px 8px rgba(25,118,210,0.12)',
          },
        }}>
          <TextField
            fullWidth
            placeholder={isBuilding ? "Building in progress..." : "Describe your website or request changes..."}
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !isBuilding && onSend()}
            size="small"
            disabled={isBuilding}
            variant="standard"
            sx={{
              '& .MuiInput-root': {
                fontSize: '0.875rem',
                py: 0.5,
                '&:before, &:after': { display: 'none' },
              },
              '& .MuiInputBase-input': {
                padding: '8px 0',
              },
            }}
          />
          <IconButton
            onClick={onSend}
            disabled={!input.trim() || isBuilding}
            sx={{
              backgroundColor: !input.trim() || isBuilding ? '#e5e7eb' : '#1976d2',
              color: !input.trim() || isBuilding ? '#9ca3af' : '#ffffff',
              width: 36,
              height: 36,
              borderRadius: 2,
              flexShrink: 0,
              '&:hover': {
                backgroundColor: !input.trim() || isBuilding ? '#e5e7eb' : '#1565c0',
              },
              '&.Mui-disabled': {
                backgroundColor: '#e5e7eb',
                color: '#9ca3af',
              },
            }}
          >
            <SendIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </Box>
      </Box>
    </Box>
  )
}
