import { useSelector, useDispatch } from 'react-redux'
import { useEffect, useState } from 'react'
import { RootState } from '../store'
import { setUser, setLoading, logout as logoutAction } from '../features/auth/authSlice'
import { authService } from '../services/auth'

export const useAuth = () => {
  const dispatch = useDispatch()
  const { user, isAuthenticated, loading } = useSelector((state: RootState) => state.auth)
  const [initialized, setInitialized] = useState(false)

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('access_token')
      if (token && !user) {
        try {
          dispatch(setLoading(true))
          const userData = await authService.getCurrentUser()
          dispatch(setUser(userData))
        } catch (error) {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        } finally {
          dispatch(setLoading(false))
          setInitialized(true)
        }
      } else {
        setInitialized(true)
      }
    }

    initAuth()
  }, [dispatch, user])

  const logout = () => {
    authService.logout()
    dispatch(logoutAction())
  }

  return {
    user,
    isAuthenticated,
    loading,
    initialized,
    logout,
  }
}

