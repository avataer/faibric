import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActionArea,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
} from '@mui/material'
import { templatesService, Template } from '../services/templates'

const CATEGORY_LABELS: Record<string, string> = {
  internal_ops: 'Internal Ops Dashboards',
  client_portal: 'Client Portals',
  admin_panel: 'Admin Panels',
  ecommerce: 'E-commerce',
}

const CATEGORIES = ['all', 'internal_ops', 'client_portal', 'admin_panel', 'ecommerce']

function TemplateGallery() {
  const navigate = useNavigate()
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [previewTab, setPreviewTab] = useState(0)
  const [deploying, setDeploying] = useState(false)
  const [deployForm, setDeployForm] = useState(false)
  const [projectName, setProjectName] = useState('')
  const [projectDescription, setProjectDescription] = useState('')
  const [deployError, setDeployError] = useState('')

  useEffect(() => {
    fetchTemplates()
  }, [])

  async function fetchTemplates() {
    try {
      setLoading(true)
      const data = await templatesService.getTemplates()
      setTemplates(data)
    } catch (err) {
      setError('Failed to load templates')
    } finally {
      setLoading(false)
    }
  }

  const filteredTemplates = selectedCategory === 'all'
    ? templates
    : templates.filter(t => t.category === selectedCategory)

  async function handleCardClick(template: Template) {
    setPreviewTab(0)
    setDeployForm(false)
    setDeployError('')
    setProjectName(template.name + ' Project')
    setProjectDescription(template.description)

    if (template.schema_template) {
      setSelectedTemplate(template)
    } else {
      setDetailLoading(true)
      setSelectedTemplate(template)
      try {
        const detail = await templatesService.getTemplate(template.slug)
        setSelectedTemplate(detail)
      } catch {
        // Keep the list-level data if detail fetch fails
      } finally {
        setDetailLoading(false)
      }
    }
  }

  function handleClose() {
    setSelectedTemplate(null)
    setDeployForm(false)
    setDeployError('')
  }

  async function handleDeploy() {
    if (!selectedTemplate) return
    if (!projectName.trim()) {
      setDeployError('Project name is required')
      return
    }
    setDeploying(true)
    setDeployError('')
    try {
      const result = await templatesService.useTemplate(
        selectedTemplate.slug,
        projectName.trim(),
        projectDescription.trim()
      )
      handleClose()
      if (result?.id) {
        navigate(`/create/${result.id}`)
      } else {
        navigate('/dashboard')
      }
    } catch (err: any) {
      const message = err?.response?.data?.error || 'Failed to deploy template'
      setDeployError(message)
    } finally {
      setDeploying(false)
    }
  }

  function renderJsonSection(data: Record<string, any> | undefined, fallback: string) {
    if (!data || Object.keys(data).length === 0) {
      return (
        <Typography variant="body2" sx={{ color: '#666', fontStyle: 'italic' }}>
          {fallback}
        </Typography>
      )
    }
    return (
      <Box
        component="pre"
        sx={{
          bgcolor: '#f5f5f5',
          p: 2,
          borderRadius: 1,
          overflow: 'auto',
          maxHeight: 400,
          fontSize: 13,
          fontFamily: 'monospace',
          color: '#000',
        }}
      >
        {JSON.stringify(data, null, 2)}
      </Box>
    )
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh', bgcolor: '#fff' }}>
        <CircularProgress sx={{ color: '#000' }} />
      </Box>
    )
  }

  if (error) {
    return (
      <Box sx={{ p: 4, bgcolor: '#fff', minHeight: '60vh' }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 4, bgcolor: '#fff', minHeight: '100vh' }}>
      <Typography variant="h4" sx={{ mb: 1, color: '#000', fontWeight: 700 }}>
        Template Gallery
      </Typography>
      <Typography variant="body1" sx={{ mb: 3, color: '#444' }}>
        Choose a template to quickly deploy a new application.
      </Typography>

      {/* Category Filter Chips */}
      <Box sx={{ display: 'flex', gap: 1, mb: 4, flexWrap: 'wrap' }}>
        {CATEGORIES.map(cat => (
          <Chip
            key={cat}
            label={cat === 'all' ? 'All' : CATEGORY_LABELS[cat]}
            onClick={() => setSelectedCategory(cat)}
            variant={selectedCategory === cat ? 'filled' : 'outlined'}
            sx={{
              bgcolor: selectedCategory === cat ? '#000' : 'transparent',
              color: selectedCategory === cat ? '#fff' : '#000',
              borderColor: '#000',
              '&:hover': {
                bgcolor: selectedCategory === cat ? '#222' : '#f0f0f0',
              },
            }}
          />
        ))}
      </Box>

      {/* Template Cards Grid */}
      {filteredTemplates.length === 0 ? (
        <Typography variant="body1" sx={{ color: '#666', textAlign: 'center', py: 8 }}>
          No templates found in this category.
        </Typography>
      ) : (
        <Grid container spacing={3}>
          {filteredTemplates.map(template => (
            <Grid item xs={12} sm={6} md={4} key={template.id}>
              <Card
                variant="outlined"
                sx={{
                  height: '100%',
                  borderColor: '#ddd',
                  '&:hover': { borderColor: '#000', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' },
                }}
              >
                <CardActionArea
                  onClick={() => handleCardClick(template)}
                  sx={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'stretch' }}
                >
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Typography variant="h6" sx={{ color: '#000', fontWeight: 600, mb: 1 }}>
                      {template.name}
                    </Typography>
                    <Chip
                      label={CATEGORY_LABELS[template.category] || template.category}
                      size="small"
                      sx={{
                        mb: 1.5,
                        bgcolor: '#f5f5f5',
                        color: '#000',
                        fontSize: 12,
                      }}
                    />
                    <Typography variant="body2" sx={{ color: '#444', mb: 2 }}>
                      {template.description}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#888' }}>
                      Used {template.usage_count} {template.usage_count === 1 ? 'time' : 'times'}
                    </Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Preview Dialog */}
      <Dialog
        open={!!selectedTemplate}
        onClose={handleClose}
        maxWidth="md"
        fullWidth
        PaperProps={{ sx: { bgcolor: '#fff', color: '#000' } }}
      >
        {selectedTemplate && (
          <>
            <DialogTitle sx={{ fontWeight: 700, color: '#000' }}>
              {selectedTemplate.name}
            </DialogTitle>
            <DialogContent dividers>
              <Typography variant="body1" sx={{ mb: 2, color: '#444' }}>
                {selectedTemplate.description}
              </Typography>

              {detailLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                  <CircularProgress sx={{ color: '#000' }} />
                </Box>
              ) : (
                <>
                  <Tabs
                    value={previewTab}
                    onChange={(_, v) => setPreviewTab(v)}
                    sx={{
                      mb: 2,
                      '& .MuiTab-root': { color: '#666' },
                      '& .Mui-selected': { color: '#000' },
                      '& .MuiTabs-indicator': { bgcolor: '#000' },
                    }}
                  >
                    <Tab label="Data Models" />
                    <Tab label="API Endpoints" />
                    <Tab label="UI Components" />
                  </Tabs>

                  {previewTab === 0 && renderJsonSection(selectedTemplate.schema_template, 'No schema data available.')}
                  {previewTab === 1 && renderJsonSection(selectedTemplate.api_template, 'No API data available.')}
                  {previewTab === 2 && renderJsonSection(selectedTemplate.ui_template, 'No UI data available.')}
                </>
              )}

              {deployForm && (
                <Box sx={{ mt: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <TextField
                    label="Project Name"
                    value={projectName}
                    onChange={e => setProjectName(e.target.value)}
                    fullWidth
                    variant="outlined"
                    InputProps={{ sx: { color: '#000' } }}
                    InputLabelProps={{ sx: { color: '#666' } }}
                  />
                  <TextField
                    label="Project Description"
                    value={projectDescription}
                    onChange={e => setProjectDescription(e.target.value)}
                    fullWidth
                    multiline
                    rows={3}
                    variant="outlined"
                    InputProps={{ sx: { color: '#000' } }}
                    InputLabelProps={{ sx: { color: '#666' } }}
                  />
                  {deployError && <Alert severity="error">{deployError}</Alert>}
                </Box>
              )}
            </DialogContent>
            <DialogActions sx={{ p: 2 }}>
              <Button onClick={handleClose} sx={{ color: '#666' }}>
                Cancel
              </Button>
              {!deployForm ? (
                <Button
                  variant="contained"
                  onClick={() => setDeployForm(true)}
                  sx={{ bgcolor: '#000', color: '#fff', '&:hover': { bgcolor: '#222' } }}
                >
                  Deploy
                </Button>
              ) : (
                <Button
                  variant="contained"
                  onClick={handleDeploy}
                  disabled={deploying}
                  sx={{ bgcolor: '#000', color: '#fff', '&:hover': { bgcolor: '#222' } }}
                >
                  {deploying ? 'Deploying...' : 'Confirm Deploy'}
                </Button>
              )}
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  )
}

export default TemplateGallery
