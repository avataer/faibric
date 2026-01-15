import { useState, useEffect, useRef, useCallback } from 'react'
import { Message } from '../components/building-studio/types'

interface UseMessagesParams {
  initialRequest: string
}

interface UseMessagesReturn {
  messages: Message[]
  messagesEndRef: React.RefObject<HTMLDivElement>
  addUserMessage: (content: string) => void
  addAssistantMessage: (content: string) => void
  addSystemMessage: (content: string, eventId?: string) => void
  addErrorMessage: (error: string) => void
  addDeploymentMessage: (url: string) => void
}

export function useMessages({ initialRequest }: UseMessagesParams): UseMessagesReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Initialize with the user's request
  useEffect(() => {
    setMessages([
      {
        id: '1',
        role: 'user',
        content: initialRequest,
        timestamp: new Date(),
      },
      {
        id: '2',
        role: 'assistant',
        content: "I'm building your app now. Watch it come to life in the preview on the right!",
        timestamp: new Date(),
      },
    ])
  }, [initialRequest])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const addUserMessage = useCallback((content: string) => {
    setMessages(prev => [...prev, {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
    }])
  }, [])

  const addAssistantMessage = useCallback((content: string) => {
    setMessages(prev => [...prev, {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content,
      timestamp: new Date(),
    }])
  }, [])

  const addSystemMessage = useCallback((content: string, eventId?: string) => {
    setMessages(prev => {
      const id = eventId || `system-${Date.now()}`
      const exists = prev.some(m => m.id === id || m.content === content)
      if (exists) return prev
      return [...prev, {
        id,
        role: 'system',
        content,
        timestamp: new Date(),
      }]
    })
  }, [])

  const addErrorMessage = useCallback((error: string) => {
    setMessages(prev => {
      const errorMsg = `Error: ${error}`
      const exists = prev.some(m => m.content === errorMsg)
      if (exists) return prev
      return [...prev, {
        id: `error-${Date.now()}`,
        role: 'system',
        content: errorMsg,
        timestamp: new Date(),
      }]
    })
  }, [])

  const addDeploymentMessage = useCallback((url: string) => {
    setMessages(prev => [...prev, {
      id: `deploy-${Date.now()}`,
      role: 'system',
      content: `Your app is live at ${url}`,
      timestamp: new Date(),
    }])
  }, [])

  return {
    messages,
    messagesEndRef,
    addUserMessage,
    addAssistantMessage,
    addSystemMessage,
    addErrorMessage,
    addDeploymentMessage,
  }
}
