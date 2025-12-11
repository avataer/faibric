import api from './api'

export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  bio: string
  avatar?: string
  max_apps: number
  created_at: string
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface RegisterData {
  username: string
  email: string
  password: string
  password2: string
  first_name?: string
  last_name?: string
}

export interface AuthResponse {
  access: string
  refresh: string
  user: User
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await api.post('/api/auth/login/', credentials)
    const { access, refresh } = response.data
    
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    
    // Get user data
    const userResponse = await api.get('/api/auth/me/')
    
    return {
      access,
      refresh,
      user: userResponse.data,
    }
  },

  async register(data: RegisterData): Promise<AuthResponse> {
    const response = await api.post('/api/auth/register/', data)
    const { access, refresh, user } = response.data
    
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    
    return { access, refresh, user }
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get('/api/auth/me/')
    return response.data
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },
}

