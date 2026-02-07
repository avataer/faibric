import api from './api'

export interface Template {
  id: number
  name: string
  slug: string
  description: string
  category: string
  thumbnail?: string
  usage_count: number
  schema_template?: Record<string, any>
  api_template?: Record<string, any>
  ui_template?: Record<string, any>
}

export const templatesService = {
  async getTemplates(): Promise<Template[]> {
    const response = await api.get('/api/templates/')
    return response.data.results || response.data
  },

  async getTemplate(slug: string): Promise<Template> {
    const response = await api.get(`/api/templates/${slug}/`)
    return response.data
  },

  async useTemplate(slug: string, name: string, description: string): Promise<any> {
    const response = await api.post(`/api/templates/${slug}/use_template/`, {
      name,
      description,
    })
    return response.data
  },
}

