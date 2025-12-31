import { api } from './api'

// Project Services API - Analytics, Domains, Versions, etc.

export interface AnalyticsData {
  total_pageviews: number
  total_visitors: number
  pageviews_today: number
  visitors_today: number
  top_pages: { path: string; views: number }[]
  traffic_sources: Record<string, number>
  pageviews_by_day: { date: string; views: number }[]
}

export interface Version {
  version_number: number
  created_at: string
  change_description: string
  is_deployed: boolean
  code_preview: string
}

export interface Domain {
  domain: string
  is_primary: boolean
  is_verified: boolean
  ssl_status: string
  dns_records: { type: string; name: string; value: string }[]
}

export interface AuthConfig {
  email_password: boolean
  magic_link: boolean
  google_oauth: boolean
  github_oauth: boolean
  status: string
}

export const projectServicesApi = {
  // Analytics
  getAnalytics: async (projectId: number | string, range = '7d'): Promise<AnalyticsData> => {
    const response = await api.get(`/api/project-services/analytics/${projectId}/?range=${range}`)
    return response.data
  },

  trackEvent: async (projectId: number | string, eventData: Record<string, any>) => {
    const response = await api.post(`/api/project-services/analytics/${projectId}/track/`, eventData)
    return response.data
  },

  // Versions
  getVersions: async (projectId: number | string): Promise<{ versions: Version[] }> => {
    const response = await api.get(`/api/project-services/versions/${projectId}/`)
    return response.data
  },

  getVersionDiff: async (projectId: number | string, fromVersion: number, toVersion: number) => {
    const response = await api.get(
      `/api/project-services/versions/${projectId}/diff/?from=${fromVersion}&to=${toVersion}`
    )
    return response.data
  },

  rollbackVersion: async (projectId: number | string, versionNumber: number) => {
    const response = await api.post(`/api/project-services/versions/${projectId}/rollback/`, {
      version: versionNumber,
    })
    return response.data
  },

  // Domains
  getDomains: async (projectId: number | string): Promise<{ domains: Domain[] }> => {
    const response = await api.get(`/api/project-services/domains/${projectId}/`)
    return response.data
  },

  addDomain: async (projectId: number | string, domain: string) => {
    const response = await api.post(`/api/project-services/domains/${projectId}/add/`, { domain })
    return response.data
  },

  verifyDomain: async (projectId: number | string, domain: string) => {
    const response = await api.post(`/api/project-services/domains/${projectId}/${domain}/verify/`)
    return response.data
  },

  removeDomain: async (projectId: number | string, domain: string) => {
    const response = await api.delete(`/api/project-services/domains/${projectId}/${domain}/remove/`)
    return response.data
  },

  // Auth Config
  getAuthConfig: async (projectId: number | string): Promise<AuthConfig | { configured: false }> => {
    const response = await api.get(`/api/project-services/auth/${projectId}/configure/`)
    return response.data
  },

  configureAuth: async (projectId: number | string, config: Partial<AuthConfig>) => {
    const response = await api.post(`/api/project-services/auth/${projectId}/configure/`, config)
    return response.data
  },

  getAuthProviders: async (projectId: number | string) => {
    const response = await api.get(`/api/project-services/auth/${projectId}/providers/`)
    return response.data
  },

  // Database
  provisionDatabase: async (projectId: number | string, projectName: string) => {
    const response = await api.post(`/api/project-services/database/provision/`, {
      project_id: projectId,
      project_name: projectName,
    })
    return response.data
  },

  getTables: async (projectId: number | string) => {
    const response = await api.get(`/api/project-services/database/${projectId}/tables/`)
    return response.data
  },

  // Payments
  connectStripe: async (projectId: number | string, email?: string) => {
    const response = await api.post(`/api/project-services/payments/${projectId}/connect/`, { 
      email: email || 'admin@faibric.com' 
    })
    return response.data
  },

  getProducts: async (projectId: number | string) => {
    const response = await api.get(`/api/project-services/payments/${projectId}/products/`)
    return response.data
  },

  // Storage
  getBuckets: async (projectId: number | string) => {
    const response = await api.get(`/api/project-services/storage/${projectId}/buckets/`)
    return response.data
  },
}

export default projectServicesApi

