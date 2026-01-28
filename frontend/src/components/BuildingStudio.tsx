import { useState, useCallback, useEffect } from 'react'
import { Box } from '@mui/material'
import { api } from '../services/api'
import { useBuildStatus } from '../hooks/useBuildStatus'
import { useBuildProgress } from '../hooks/useBuildProgress'
import { useMessages } from '../hooks/useMessages'
import { ChatPanel, PreviewPanel, BuildingStudioProps } from './building-studio'

interface ModelConfig {
  key: string
  name: string
  credits_per_request: number
}

const BuildingStudio = ({ sessionToken, initialRequest, onDeployed, onNewProject }: BuildingStudioProps) => {
  // Local UI state
  const [input, setInput] = useState('')
  const [isStopping, setIsStopping] = useState(false)
  const [iframeKey, setIframeKey] = useState(0)

  // Model selection state
  const [models, setModels] = useState<ModelConfig[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [modelsLoading, setModelsLoading] = useState(true)

  // Fetch available models on mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await api.get('/api/ai/models/')
        if (response.data.models) {
          setModels(response.data.models)
          // Set default model to the first one
          if (response.data.models.length > 0 && !selectedModel) {
            setSelectedModel(response.data.models[0].key)
          }
        }
      } catch (err) {
        console.error('Failed to load models:', err)
      } finally {
        setModelsLoading(false)
      }
    }
    fetchModels()
  }, [])

  // Message management
  const {
    messages,
    messagesEndRef,
    addUserMessage,
    addAssistantMessage,
    addSystemMessage,
    addErrorMessage,
    addDeploymentMessage,
  } = useMessages({ initialRequest })

  // Build status polling
  const {
    isBuilding,
    buildPhase,
    deploymentUrl,
    targetProgress,
    stopBuilding,
    resetForNewBuild,
  } = useBuildStatus({
    sessionToken,
    onDeployed: (url) => {
      addDeploymentMessage(url)
      setIframeKey(prev => prev + 1)  // Auto-refresh preview after modification
      onDeployed?.(url)
    },
    onProgressEvent: (msg, eventId) => addSystemMessage(msg, eventId),
    onErrorEvent: (err) => addErrorMessage(err),
  })

  // Animated progress
  const { buildProgress } = useBuildProgress({ targetProgress, isBuilding })

  // Send message handler
  const handleSend = useCallback(async () => {
    if (!input.trim()) return

    addUserMessage(input)
    const newRequest = input
    setInput('')

    try {
      const res = await api.post('/api/onboarding/modify/', {
        session_token: sessionToken,
        request: newRequest,
        model: selectedModel || undefined,
      })

      const mode = res.data.mode
      addAssistantMessage(
        mode === 'modify'
          ? "Got it! Applying your changes quickly..."
          : "Starting fresh with your new request..."
      )

      resetForNewBuild(mode)
    } catch {
      addErrorMessage('Failed to apply changes. Please try again.')
    }
  }, [input, sessionToken, selectedModel, addUserMessage, addAssistantMessage, addErrorMessage, resetForNewBuild])

  // Stop build handler
  const handleStop = useCallback(async () => {
    setIsStopping(true)
    try {
      await stopBuilding()
      addSystemMessage('Build stopped. You can start a new build or make changes.')
    } catch {
      addSystemMessage('Could not stop build on server. Click "Start New" to begin fresh.')
    }
    setIsStopping(false)
  }, [stopBuilding, addSystemMessage])

  // Refresh preview handler
  const handleRefresh = useCallback(() => {
    setIframeKey(prev => prev + 1)
  }, [])

  // Retry handler - resends the last user request
  const handleRetry = useCallback(async () => {
    // Find the last user message (before any errors)
    const userMessages = messages.filter(m => m.role === 'user')
    const lastUserMessage = userMessages[userMessages.length - 1]

    if (!lastUserMessage) return

    addAssistantMessage("Trying again...")

    try {
      const res = await api.post('/api/onboarding/modify/', {
        session_token: sessionToken,
        request: lastUserMessage.content,
        model: selectedModel || undefined,
      })

      const mode = res.data.mode
      addAssistantMessage(
        mode === 'modify'
          ? "Got it! Applying your changes..."
          : "Starting fresh..."
      )

      resetForNewBuild(mode)
    } catch {
      addErrorMessage('Still having trouble. Try simplifying your request or start a new project.')
    }
  }, [messages, sessionToken, selectedModel, addAssistantMessage, addErrorMessage, resetForNewBuild])

  return (
    <Box sx={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden' }}>
      <ChatPanel
        messages={messages}
        messagesEndRef={messagesEndRef}
        isBuilding={isBuilding}
        isStopping={isStopping}
        buildProgress={buildProgress}
        input={input}
        onInputChange={setInput}
        onSend={handleSend}
        onStop={handleStop}
        onNewProject={onNewProject}
        onRetry={handleRetry}
        models={models}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
        modelsLoading={modelsLoading}
      />
      <PreviewPanel
        deploymentUrl={deploymentUrl}
        buildProgress={buildProgress}
        buildPhase={buildPhase}
        initialRequest={initialRequest}
        iframeKey={iframeKey}
        onRefresh={handleRefresh}
        onEditRequest={(editRequest) => {
          // Use visual edit request as input and send it
          addUserMessage(editRequest)
          api.post('/api/onboarding/modify/', {
            session_token: sessionToken,
            request: editRequest,
            model: selectedModel || undefined,
          }).then((res) => {
            const mode = res.data.mode
            addAssistantMessage(
              mode === 'modify'
                ? "Got it! Applying your visual edit..."
                : "Starting fresh with your new request..."
            )
            resetForNewBuild(mode)
          }).catch(() => {
            addErrorMessage('Failed to apply visual edit. Please try again.')
          })
        }}
      />
    </Box>
  )
}

export default BuildingStudio
