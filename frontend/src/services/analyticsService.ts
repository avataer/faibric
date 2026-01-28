import { api } from './api'

// TypeScript interfaces for analytics data

export interface EventStats {
  total_events: number
  unique_users: number
  by_event_name: { event_name: string; count: number }[]
  by_day: { date: string; count: number }[]
}

export interface FunnelStep {
  id: number
  order: number
  name: string
  event_name: string
  property_filters: Record<string, unknown>
}

export interface Funnel {
  id: number
  name: string
  description: string
  template_name: string | null
  steps: FunnelStep[]
  created_at: string
  updated_at: string
}

export interface FunnelStepStats {
  step_name: string
  event_name: string
  entered: number
  completed: number
  conversion_rate: number
  drop_off_rate: number
}

export interface FunnelStats {
  funnel_id: number
  funnel_name: string
  total_started: number
  total_completed: number
  overall_conversion_rate: number
  steps: FunnelStepStats[]
}

export interface FunnelTemplate {
  template_name: string
  name: string
  description: string
  steps: { name: string; event_name: string; property_filters?: Record<string, unknown> }[]
}

export const analyticsService = {
  // Event Statistics
  getEventStats: async (days = 7): Promise<EventStats> => {
    const response = await api.get(`/api/analytics/events/stats/?days=${days}`)
    return response.data
  },

  getRecentEvents: async () => {
    const response = await api.get('/api/analytics/events/recent/')
    return response.data
  },

  // Funnels
  getFunnels: async (): Promise<Funnel[]> => {
    const response = await api.get('/api/analytics/funnels/')
    return response.data
  },

  getFunnel: async (id: number): Promise<Funnel> => {
    const response = await api.get(`/api/analytics/funnels/${id}/`)
    return response.data
  },

  getFunnelStats: async (id: number, days = 30): Promise<FunnelStats> => {
    const response = await api.get(`/api/analytics/funnels/${id}/stats/?days=${days}`)
    return response.data
  },

  createFunnel: async (data: { name: string; description?: string; steps: { name: string; event_name: string; property_filters?: Record<string, unknown> }[] }): Promise<Funnel> => {
    const response = await api.post('/api/analytics/funnels/', data)
    return response.data
  },

  deleteFunnel: async (id: number): Promise<void> => {
    await api.delete(`/api/analytics/funnels/${id}/`)
  },

  // Funnel Templates
  getFunnelTemplates: async (): Promise<FunnelTemplate[]> => {
    const response = await api.get('/api/analytics/funnels/templates/')
    return response.data
  },

  createFunnelFromTemplate: async (templateName: string): Promise<Funnel> => {
    const response = await api.post('/api/analytics/funnels/create_from_template/', {
      template_name: templateName,
    })
    return response.data
  },

  // Analytics Config
  getConfig: async () => {
    const response = await api.get('/api/analytics/config/')
    return response.data
  },

  updateConfig: async (config: Record<string, unknown>) => {
    const response = await api.patch('/api/analytics/update_config/', config)
    return response.data
  },
}

export default analyticsService
