export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
}

export interface BuildEvent {
  id?: string
  timestamp: string
  event_type: 'build_progress' | 'error'
  event_data: {
    message?: string
    error?: string
  }
}

export interface BuildStatusResponse {
  status: string
  build_progress?: number
  deployment_url?: string
  project_id?: string
  events?: BuildEvent[]
}

export interface BuildingStudioProps {
  sessionToken: string
  initialRequest: string
  onDeployed?: (url: string) => void
  onNewProject?: () => void
}
