import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Container,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardActions,
  Chip,
  Box,
  CircularProgress,
} from '@mui/material'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../store'
import { setProjects, setLoading } from '../features/projects/projectsSlice'
import { projectsService } from '../services/projects'

const Dashboard = () => {
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { projects, loading } = useSelector((state: RootState) => state.projects)

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    dispatch(setLoading(true))
    try {
      const data = await projectsService.getProjects()
      dispatch(setProjects(data))
    } catch (error) {
      console.error('Failed to load projects:', error)
    } finally {
      dispatch(setLoading(false))
    }
  }

  const getStatusColor = (status: string) => {
    const colors: { [key: string]: any } = {
      draft: 'default',
      generating: 'info',
      ready: 'success',
      deployed: 'primary',
      failed: 'error',
    }
    return colors[status] || 'default'
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Container maxWidth="lg" sx={{ bgcolor: '#ffffff' }}>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" sx={{ color: '#000000', fontWeight: 600 }}>
          My Projects
        </Typography>
        <Button
          variant="contained"
          onClick={() => navigate('/create')}
        >
          New Project
        </Button>
      </Box>

      {projects.length === 0 ? (
        <Card sx={{ p: 6, textAlign: 'center' }}>
          <Typography variant="h6" sx={{ color: '#374151', mb: 1 }}>
            No projects yet
          </Typography>
          <Typography variant="body2" sx={{ color: '#6b7280', mb: 3 }}>
            Create your first project to get started
          </Typography>
          <Button variant="contained" onClick={() => navigate('/create')}>
            Create Project
          </Button>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {projects.map((project) => (
            <Grid item xs={12} md={6} lg={4} key={project.id}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Typography variant="h6" sx={{ color: '#000000', mb: 1 }}>
                    {project.name}
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#374151', mb: 2 }}>
                    {project.description}
                  </Typography>
                  <Chip
                    label={project.status}
                    color={getStatusColor(project.status)}
                    size="small"
                  />
                </CardContent>
                <CardActions>
                  <Button size="small" onClick={() => navigate(`/projects/${project.id}`)}>
                    View Details
                  </Button>
                  {(project.status === 'ready' || project.status === 'deployed') && (
                    <Button 
                      size="small" 
                      color="primary"
                      onClick={() => navigate(`/live-creation/${project.id}`)}
                    >
                      Builder
                    </Button>
                  )}
                  {project.deployment_url && (
                    <Button 
                      size="small" 
                      color="success"
                      onClick={() => window.open(project.deployment_url, '_blank')}
                    >
                      Live
                    </Button>
                  )}
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Container>
  )
}

export default Dashboard
