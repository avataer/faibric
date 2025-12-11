import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Container,
  Typography,
  Box,
  Paper,
  Chip,
  Button,
  Grid,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  LinearProgress,
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import { useDispatch } from 'react-redux'
import { setCurrentProject } from '../features/projects/projectsSlice'
import { projectsService, ProjectDetail as ProjectDetailType } from '../services/projects'

const ProjectDetail = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const [project, setProject] = useState<ProjectDetailType | null>(null)
  const [loading, setLoading] = useState(true)
  const [regenerating, setRegenerating] = useState(false)
  const [deleteDialog, setDeleteDialog] = useState(false)
  const [progress, setProgress] = useState<{step: number, message: string, progress: number} | null>(null)

  useEffect(() => {
    loadProject()
    
    // Poll for progress if project is generating
    let progressInterval: NodeJS.Timeout
    if (project?.status === 'generating') {
      progressInterval = setInterval(async () => {
        try {
          const progressData = await projectsService.getProgress(project.id)
          setProgress(progressData)
          
          // Also refresh project to check if status changed
          const updatedProject = await projectsService.getProject(project.id)
          setProject(updatedProject)
          
          if (updatedProject.status !== 'generating') {
            clearInterval(progressInterval)
            setProgress(null)
          }
        } catch (error) {
          console.error('Failed to get progress:', error)
        }
      }, 1000) // Poll every second
    }
    
    return () => {
      if (progressInterval) clearInterval(progressInterval)
    }
  }, [id, project?.status])

  const loadProject = async () => {
    try {
      const data = await projectsService.getProject(Number(id))
      setProject(data)
      dispatch(setCurrentProject(data))
    } catch (error) {
      console.error('Failed to load project:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDeploy = async () => {
    if (!project) return
    try {
      await projectsService.publishProject(project.id)
      alert('Deployment started! Refresh to see status.')
      loadProject()
    } catch (error) {
      console.error('Failed to deploy:', error)
    }
  }

  const handleDelete = async () => {
    if (!project) return
    try {
      await projectsService.deleteProject(project.id)
      navigate('/dashboard')
    } catch (error) {
      console.error('Failed to delete:', error)
    }
  }

  const handleRegenerate = async () => {
    if (!project || !project.user_prompt) return
    setRegenerating(true)
    try {
      await projectsService.regenerateProject(project.id, project.user_prompt)
      // Reload project to show "generating" status
      await loadProject()
      // Set up auto-refresh to check status
      const interval = setInterval(async () => {
        const updatedProject = await projectsService.getProject(project.id)
        setProject(updatedProject)
        if (updatedProject.status !== 'generating') {
          clearInterval(interval)
          setRegenerating(false)
        }
      }, 5000)
    } catch (error) {
      console.error('Failed to regenerate:', error)
      setRegenerating(false)
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

  if (!project) {
    return (
      <Container>
        <Typography variant="h6">Project not found</Typography>
      </Container>
    )
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4" fontWeight={600}>
            {project.name}
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            {project.status === 'ready' && (
              <>
                <Button variant="outlined" onClick={() => navigate(`/builder/${project.id}`)}>
                  Open Builder
                </Button>
                <Button variant="contained" onClick={handleDeploy}>
                  Deploy
                </Button>
              </>
            )}
            {project.status === 'deployed' && project.deployment_url && (
              <>
                <Button
                  variant="contained"
                  onClick={() => window.open(project.deployment_url, '_blank')}
                >
                  View Live App
                </Button>
                <Button
                  variant="outlined"
                  onClick={async () => {
                    if (confirm('Undeploy this app?')) {
                      await projectsService.unpublishProject(project.id)
                      loadProject()
                    }
                  }}
                >
                  Undeploy
                </Button>
              </>
            )}
            {project.status === 'failed' && (
              <Button
                variant="contained"
                color="warning"
                startIcon={<RefreshIcon />}
                onClick={handleRegenerate}
                disabled={regenerating}
              >
                {regenerating ? 'Re-generating...' : 'Re-run Generation'}
              </Button>
            )}
            <Button variant="outlined" color="error" onClick={() => setDeleteDialog(true)}>
              Delete
            </Button>
          </Box>
        </Box>
        <Chip label={project.status} color={getStatusColor(project.status)} />
        
        {/* Real-time generation progress */}
        {project.status === 'generating' && progress && (
          <Paper sx={{ mt: 2, p: 3, bgcolor: '#f0f7ff', border: '1px solid #2196f3' }}>
            <Box sx={{ mb: 2 }}>
              <Typography variant="h6" fontWeight={600} color="primary.main" gutterBottom>
                🤖 AI is Building Your App
              </Typography>
              <Typography variant="body1" sx={{ mb: 2, fontSize: '1.1rem' }}>
                {progress.message}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box sx={{ flexGrow: 1 }}>
                <LinearProgress 
                  variant="determinate" 
                  value={progress.progress} 
                  sx={{ 
                    height: 10, 
                    borderRadius: 5,
                    bgcolor: '#e3f2fd',
                    '& .MuiLinearProgress-bar': {
                      bgcolor: '#2196f3',
                      borderRadius: 5,
                    }
                  }} 
                />
              </Box>
              <Typography variant="body2" fontWeight={600} color="primary.main" sx={{ minWidth: 45 }}>
                {progress.progress}%
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Step {progress.step} of 10 • This usually takes 30-90 seconds
            </Typography>
          </Paper>
        )}

        {/* Regenerating status */}
        {project.status === 'generating' && !progress && (
          <Alert severity="info" sx={{ mt: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <CircularProgress size={20} />
              <Box>
                <Typography variant="subtitle2" fontWeight={600}>Generating Your App</Typography>
                <Typography variant="body2">
                  AI is creating your application. This usually takes 20-60 seconds...
                </Typography>
              </Box>
            </Box>
          </Alert>
        )}

        {/* Error message display */}
        {project.status === 'failed' && project.ai_analysis?.error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            <Typography variant="subtitle2" fontWeight={600}>Generation Failed</Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>{project.ai_analysis.error}</Typography>
            {project.ai_analysis.error.includes('API key') && (
              <Typography variant="body2" sx={{ mb: 1 }}>
                Please configure your OpenAI API key in the backend.
              </Typography>
            )}
            <Typography variant="body2" color="text.secondary">
              Click the "Re-run Generation" button above to try again with the same prompt.
            </Typography>
          </Alert>
        )}
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Description
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {project.description}
            </Typography>
          </Paper>

          {project.user_prompt && (
            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Original Prompt
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {project.user_prompt}
              </Typography>
            </Paper>
          )}

          {project.models && project.models.length > 0 && (
            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Database Models
              </Typography>
              {project.models.map((model: any) => (
                <Box key={model.id} sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" fontWeight={600}>
                    {model.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {model.fields.length} fields
                  </Typography>
                </Box>
              ))}
            </Paper>
          )}

          {project.apis && project.apis.length > 0 && (
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                API Endpoints
              </Typography>
              {project.apis.map((api: any) => (
                <Box key={api.id} sx={{ mb: 1 }}>
                  <Typography variant="body2">
                    <strong>{api.method}</strong> {api.path}
                  </Typography>
                </Box>
              ))}
            </Paper>
          )}
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Project Info
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Created
              </Typography>
              <Typography variant="body1">
                {new Date(project.created_at).toLocaleDateString()}
              </Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Last Updated
              </Typography>
              <Typography variant="body1">
                {new Date(project.updated_at).toLocaleDateString()}
              </Typography>
            </Box>
            {project.deployment_url && (
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Deployment URL
                </Typography>
                <Typography variant="body2" sx={{ wordBreak: 'break-all', color: '#2196f3', fontFamily: 'monospace' }}>
                  {project.deployment_url}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                  Live and accessible via Traefik reverse proxy
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      <Dialog open={deleteDialog} onClose={() => setDeleteDialog(false)}>
        <DialogTitle>Delete Project?</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete "{project.name}"? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog(false)}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}

export default ProjectDetail

