import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { Project } from '../../services/projects'

interface ProjectsState {
  projects: Project[]
  currentProject: any | null
  loading: boolean
  error: string | null
}

const initialState: ProjectsState = {
  projects: [],
  currentProject: null,
  loading: false,
  error: null,
}

const projectsSlice = createSlice({
  name: 'projects',
  initialState,
  reducers: {
    setProjects: (state, action: PayloadAction<Project[]>) => {
      state.projects = action.payload
      state.error = null
    },
    setCurrentProject: (state, action: PayloadAction<any>) => {
      state.currentProject = action.payload
      state.error = null
    },
    addProject: (state, action: PayloadAction<Project>) => {
      state.projects.unshift(action.payload)
    },
    updateProject: (state, action: PayloadAction<Project>) => {
      const index = state.projects.findIndex(p => p.id === action.payload.id)
      if (index !== -1) {
        state.projects[index] = action.payload
      }
      if (state.currentProject?.id === action.payload.id) {
        state.currentProject = action.payload
      }
    },
    removeProject: (state, action: PayloadAction<number>) => {
      state.projects = state.projects.filter(p => p.id !== action.payload)
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload
    },
    setError: (state, action: PayloadAction<string>) => {
      state.error = action.payload
      state.loading = false
    },
  },
})

export const {
  setProjects,
  setCurrentProject,
  addProject,
  updateProject,
  removeProject,
  setLoading,
  setError,
} = projectsSlice.actions

export default projectsSlice.reducer

