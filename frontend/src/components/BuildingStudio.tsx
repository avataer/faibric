import { useState, useCallback, useEffect } from 'react'
import { Box, Typography } from '@mui/material'
import { api } from '../services/api'
import { useBuildStatus } from '../hooks/useBuildStatus'
import { useBuildProgress } from '../hooks/useBuildProgress'
import { useMessages } from '../hooks/useMessages'
import { ChatPanel, PreviewPanel, BuildingStudioProps } from './building-studio'
import { SectionLibrary, DragDropSectionEditor } from './builder'
import { SECTION_TYPES } from './builder/sectionTypes'
import type { Section } from './builder/sectionTypes'

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

  // Section editor state
  const [sectionEditorOpen, setSectionEditorOpen] = useState(false)
  const [sections, setSections] = useState<Section[]>([])
  const [sectionLibraryOpen, setSectionLibraryOpen] = useState(false)

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
    projectId,
    targetProgress,
    aiUnavailable,
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

      // Handle conversation mode (questions/feedback) - no build needed
      if (mode === 'conversation') {
        addAssistantMessage(res.data.response || "I'd be happy to help!")
        // Don't trigger any build - just show the response
        return
      }

      // Handle build modes
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

  // Section operation handlers
  const handleAddSection = useCallback(async (sectionType: string) => {
    try {
      const res = await api.post('/api/onboarding/sections/', {
        session_token: sessionToken,
        project_id: projectId || undefined,
        action: 'add_section',
        section_type: sectionType,
      })
      if (res.data.success) {
        const typeDef = SECTION_TYPES.find(t => t.type === sectionType)
        const newSection: Section = {
          id: res.data.section_id,
          type: res.data.section_type,
          label: typeDef?.label || sectionType.charAt(0).toUpperCase() + sectionType.slice(1),
          html: res.data.generated_html,
        }
        setSections(prev => [...prev, newSection])
      }
      setSectionLibraryOpen(false)
      setIframeKey(prev => prev + 1)
      addSystemMessage(`Added ${sectionType} section`)
    } catch (err) {
      console.error('Failed to add section:', err)
      addErrorMessage('Failed to add section. Please try again.')
    }
  }, [sessionToken, projectId, addSystemMessage, addErrorMessage])

  const handleRemoveSection = useCallback(async (sectionId: string) => {
    const section = sections.find(s => s.id === sectionId)
    try {
      const res = await api.post('/api/onboarding/sections/', {
        session_token: sessionToken,
        project_id: projectId || undefined,
        action: 'remove_section',
        section_id: sectionId,
      })
      if (res.data.success) {
        setSections(prev => prev.filter(s => s.id !== sectionId))
      }
      setIframeKey(prev => prev + 1)
      addSystemMessage(`Removed ${section?.label || 'section'}`)
    } catch (err) {
      console.error('Failed to remove section:', err)
      addErrorMessage('Failed to remove section. Please try again.')
    }
  }, [sessionToken, projectId, sections, addSystemMessage, addErrorMessage])

  const handleReorderSections = useCallback(async (fromIndex: number, toIndex: number) => {
    const reordered = [...sections]
    const [moved] = reordered.splice(fromIndex, 1)
    reordered.splice(toIndex, 0, moved)
    setSections(reordered)
    try {
      await api.post('/api/onboarding/sections/', {
        session_token: sessionToken,
        project_id: projectId || undefined,
        action: 'reorder_sections',
        section_ids: reordered.map(s => s.id),
      })
      setIframeKey(prev => prev + 1)
      addSystemMessage('Reordered sections')
    } catch (err) {
      console.error('Failed to reorder sections:', err)
      addErrorMessage('Failed to reorder sections. Please try again.')
    }
  }, [sessionToken, projectId, sections, addSystemMessage, addErrorMessage])

  const handleDuplicateSection = useCallback(async (sectionId: string) => {
    const section = sections.find(s => s.id === sectionId)
    try {
      const res = await api.post('/api/onboarding/sections/', {
        session_token: sessionToken,
        project_id: projectId || undefined,
        action: 'duplicate_section',
        section_id: sectionId,
      })
      if (res.data.success && section) {
        const newSection: Section = {
          id: res.data.new_section_id,
          type: section.type,
          label: `${section.label} (Copy)`,
        }
        const idx = sections.findIndex(s => s.id === sectionId)
        setSections(prev => {
          const updated = [...prev]
          updated.splice(idx + 1, 0, newSection)
          return updated
        })
      }
      setIframeKey(prev => prev + 1)
      addSystemMessage(`Duplicated ${section?.label || 'section'}`)
    } catch (err) {
      console.error('Failed to duplicate section:', err)
      addErrorMessage('Failed to duplicate section. Please try again.')
    }
  }, [sessionToken, projectId, sections, addSystemMessage, addErrorMessage])

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
    <Box sx={{
      display: 'flex',
      height: '100vh',
      width: '100vw',
      overflow: 'hidden',
      backgroundColor: '#ffffff',
      fontFamily: '"Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    }}>
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
        aiUnavailable={aiUnavailable}
        onRefresh={handleRefresh}
        onEditRequest={(editRequest) => {
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
        sections={sections}
        sectionEditorOpen={sectionEditorOpen}
        onToggleSectionEditor={() => setSectionEditorOpen(prev => !prev)}
      />
      {sectionEditorOpen && (
        <Box sx={{
          width: 280,
          flexShrink: 0,
          borderLeft: '1px solid #e5e7eb',
          backgroundColor: '#ffffff',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '-4px 0 16px rgba(0,0,0,0.06)',
        }}>
          <Box sx={{
            p: 2,
            borderBottom: '1px solid #e5e7eb',
            backgroundColor: '#ffffff',
          }}>
            <Typography variant="subtitle2" fontWeight={700} sx={{ color: '#111827', fontSize: '0.875rem', letterSpacing: '-0.01em' }}>
              Sections
            </Typography>
          </Box>
          <Box sx={{ flex: 1, overflow: 'auto', backgroundColor: '#f5f5f5' }}>
            <DragDropSectionEditor
              sections={sections}
              onReorder={handleReorderSections}
              onDuplicate={handleDuplicateSection}
              onDelete={handleRemoveSection}
              onAddSection={() => setSectionLibraryOpen(true)}
            />
          </Box>
        </Box>
      )}
      <SectionLibrary
        open={sectionLibraryOpen}
        onClose={() => setSectionLibraryOpen(false)}
        onAddSection={handleAddSection}
      />
    </Box>
  )
}

export default BuildingStudio
