import api from './api'

export interface Project {
  id: number
  user: string
  name: string
  description: string
  status: 'draft' | 'generating' | 'ready' | 'deployed' | 'failed'
  deployment_url: string
  created_at: string
  updated_at: string
}

export interface ProjectDetail extends Project {
  user_prompt: string
  ai_analysis: any
  database_schema: any
  api_code: string
  frontend_code: string
  subdomain: string
  container_id: string
  deployed_at: string
  models: any[]
  apis: any[]
}

export interface CreateProjectData {
  name: string
  description: string
  user_prompt: string
  template?: number
}

export const projectsService = {
  async getProjects(): Promise<Project[]> {
    const response = await api.get('/api/projects/')
    return response.data.results || response.data
  },

  async getProject(id: number): Promise<ProjectDetail> {
    const response = await api.get(`/api/projects/${id}/`)
    return response.data
  },

  async createProject(data: CreateProjectData): Promise<Project> {
    const response = await api.post('/api/projects/', data)
    return response.data
  },

  async updateProject(id: number, data: Partial<CreateProjectData>): Promise<Project> {
    const response = await api.patch(`/api/projects/${id}/`, data)
    return response.data
  },

  async deleteProject(id: number): Promise<void> {
    await api.delete(`/api/projects/${id}/`)
  },

  async regenerateProject(id: number, userPrompt: string): Promise<void> {
    await api.post(`/api/projects/${id}/regenerate/`, { user_prompt: userPrompt })
  },

  async quickUpdate(id: number, userPrompt: string): Promise<void> {
    await api.post(`/api/projects/${id}/quick_update/`, { user_prompt: userPrompt })
  },

  async publishProject(id: number): Promise<void> {
    await api.post(`/api/projects/${id}/publish/`)
  },

  async unpublishProject(id: number): Promise<void> {
    await api.post(`/api/projects/${id}/unpublish/`)
  },

  async getProgress(id: number): Promise<any> {
    const response = await api.get(`/api/projects/${id}/progress/`)
    return response.data
  },
}

