import { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  Divider,
  Paper,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
} from '@mui/material'
import { api } from '../services/api'

interface Widget {
  id: string
  type: string
  title: string
  config: any
  position: { x: number; y: number; w: number; h: number }
}

interface AdminPanel {
  id: string
  name: string
  description: string
  widgets: Widget[]
  layout: any
  is_published: boolean
}

const WIDGET_TYPES = [
  { type: 'table', label: 'Data Table' },
  { type: 'bar_chart', label: 'Bar Chart' },
  { type: 'line_chart', label: 'Line Chart' },
  { type: 'pie_chart', label: 'Pie Chart' },
  { type: 'stat_card', label: 'Stat Card' },
  { type: 'text', label: 'Text Block' },
  { type: 'image', label: 'Image' },
]

const AdminPanelBuilder = () => {
  const [loading, setLoading] = useState(true)
  const [panels, setPanels] = useState<AdminPanel[]>([])
  const [selectedPanel, setSelectedPanel] = useState<AdminPanel | null>(null)
  const [widgets, setWidgets] = useState<Widget[]>([])
  const [showWidgetDialog, setShowWidgetDialog] = useState(false)
  const [selectedWidgetType, setSelectedWidgetType] = useState<string | null>(null)
  const [tab, setTab] = useState(0)

  useEffect(() => {
    loadPanels()
  }, [])

  const loadPanels = async () => {
    setLoading(true)
    try {
      const res = await api.get('/api/admin-builder/panels/')
      setPanels(res.data.results || res.data || [])
    } catch (err) {
      console.error('Failed to load panels:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreatePanel = async () => {
    const name = prompt('Panel name:')
    if (!name) return

    try {
      const res = await api.post('/api/admin-builder/panels/', {
        name,
        description: '',
        layout: { columns: 12, rowHeight: 100 },
      })
      setPanels([...panels, res.data])
      setSelectedPanel(res.data)
      setWidgets([])
    } catch (err) {
      console.error('Failed to create panel:', err)
    }
  }

  const handleSelectPanel = async (panel: AdminPanel) => {
    setSelectedPanel(panel)
    try {
      const res = await api.get(`/api/admin-builder/panels/${panel.id}/`)
      setWidgets(res.data.widgets || [])
    } catch (err) {
      console.error('Failed to load panel:', err)
      setWidgets([])
    }
  }

  const handleAddWidget = (type: string) => {
    const newWidget: Widget = {
      id: `widget_${Date.now()}`,
      type,
      title: WIDGET_TYPES.find(w => w.type === type)?.label || 'Widget',
      config: {},
      position: { x: 0, y: widgets.length * 2, w: 6, h: 2 },
    }
    setWidgets([...widgets, newWidget])
    setShowWidgetDialog(false)
    setSelectedWidgetType(null)
  }

  const handleRemoveWidget = (id: string) => {
    setWidgets(widgets.filter(w => w.id !== id))
  }

  const handleSavePanel = async () => {
    if (!selectedPanel) return

    try {
      await api.put(`/api/admin-builder/panels/${selectedPanel.id}/`, {
        ...selectedPanel,
        widgets,
      })
      alert('Panel saved!')
    } catch (err) {
      console.error('Failed to save panel:', err)
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4, bgcolor: '#ffffff' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ color: '#000000', fontWeight: 700 }}>
            Admin Panel Builder
          </Typography>
          <Typography variant="body1" sx={{ color: '#374151' }}>
            Build custom dashboards with drag-and-drop widgets
          </Typography>
        </Box>
        <Button variant="contained" onClick={handleCreatePanel}>
          New Panel
        </Button>
      </Box>

      <Grid container spacing={3}>
        {/* Panels List */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ color: '#000000', mb: 2 }}>Your Panels</Typography>
              <List>
                {panels.length === 0 ? (
                  <ListItem>
                    <ListItemText 
                      primary="No panels yet" 
                      secondary="Create your first admin panel"
                      sx={{ '& .MuiListItemText-primary': { color: '#000000' } }}
                    />
                  </ListItem>
                ) : panels.map((panel) => (
                  <ListItem
                    key={panel.id}
                    button
                    selected={selectedPanel?.id === panel.id}
                    onClick={() => handleSelectPanel(panel)}
                  >
                    <ListItemText 
                      primary={panel.name}
                      secondary={`${panel.widgets?.length || 0} widgets`}
                      sx={{ '& .MuiListItemText-primary': { color: '#000000' } }}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Builder Area */}
        <Grid item xs={12} md={9}>
          {!selectedPanel ? (
            <Card sx={{ p: 8, textAlign: 'center' }}>
              <Typography variant="h6" sx={{ color: '#374151', mb: 2 }}>
                Select a panel to edit or create a new one
              </Typography>
              <Button variant="outlined" onClick={handleCreatePanel}>
                Create Panel
              </Button>
            </Card>
          ) : (
            <Card>
              <CardContent>
                {/* Panel Header */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
                  <Box>
                    <Typography variant="h5" sx={{ color: '#000000' }}>{selectedPanel.name}</Typography>
                    <Chip 
                      label={selectedPanel.is_published ? 'Published' : 'Draft'} 
                      size="small"
                      color={selectedPanel.is_published ? 'success' : 'default'}
                    />
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button variant="outlined">
                      Preview
                    </Button>
                    <Button variant="contained" onClick={handleSavePanel}>
                      Save
                    </Button>
                  </Box>
                </Box>

                <Divider sx={{ mb: 3 }} />

                {/* Tabs */}
                <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
                  <Tab label="Layout" />
                  <Tab label="Widgets" />
                  <Tab label="Settings" />
                  <Tab label="Code" />
                </Tabs>

                {/* Layout Tab */}
                {tab === 0 && (
                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                      <Typography variant="subtitle1" sx={{ color: '#000000' }}>
                        Widgets ({widgets.length})
                      </Typography>
                      <Button 
                        size="small" 
                        onClick={() => setShowWidgetDialog(true)}
                      >
                        Add Widget
                      </Button>
                    </Box>

                    {/* Widget Grid */}
                    <Paper 
                      variant="outlined" 
                      sx={{ 
                        minHeight: 400, 
                        p: 2,
                        bgcolor: '#ffffff',
                      }}
                    >
                      {widgets.length === 0 ? (
                        <Box sx={{ 
                          height: 400, 
                          display: 'flex', 
                          alignItems: 'center', 
                          justifyContent: 'center',
                          flexDirection: 'column',
                          gap: 2,
                        }}>
                          <Typography sx={{ color: '#374151' }}>
                            No widgets yet. Add your first widget to get started.
                          </Typography>
                          <Button 
                            variant="outlined" 
                            onClick={() => setShowWidgetDialog(true)}
                          >
                            Add Widget
                          </Button>
                        </Box>
                      ) : (
                        <Grid container spacing={2}>
                          {widgets.map((widget) => (
                            <Grid item xs={12} md={6} key={widget.id}>
                              <Paper 
                                sx={{ 
                                  p: 2, 
                                  border: '1px solid #e5e7eb',
                                  position: 'relative',
                                }}
                              >
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                  <Typography variant="subtitle2" sx={{ color: '#000000' }}>{widget.title}</Typography>
                                  <Chip label={widget.type} size="small" />
                                  <Button 
                                    size="small" 
                                    sx={{ ml: 'auto' }}
                                    onClick={() => handleRemoveWidget(widget.id)}
                                  >
                                    Remove
                                  </Button>
                                </Box>
                                <Box sx={{ 
                                  height: 100, 
                                  bgcolor: '#f9fafb', 
                                  borderRadius: 1,
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  color: '#374151',
                                }}>
                                  {widget.type}
                                </Box>
                              </Paper>
                            </Grid>
                          ))}
                        </Grid>
                      )}
                    </Paper>
                  </Box>
                )}

                {/* Widgets Tab */}
                {tab === 1 && (
                  <Box>
                    <Typography variant="subtitle1" sx={{ color: '#000000', mb: 2 }}>
                      Available Widget Types
                    </Typography>
                    <Grid container spacing={2}>
                      {WIDGET_TYPES.map((wt) => (
                        <Grid item xs={6} md={3} key={wt.type}>
                          <Card 
                            sx={{ 
                              p: 2, 
                              textAlign: 'center', 
                              cursor: 'pointer',
                              '&:hover': { bgcolor: '#f9fafb' },
                            }}
                            onClick={() => handleAddWidget(wt.type)}
                          >
                            <Typography variant="body2" sx={{ color: '#000000' }}>{wt.label}</Typography>
                          </Card>
                        </Grid>
                      ))}
                    </Grid>
                  </Box>
                )}

                {/* Settings Tab */}
                {tab === 2 && (
                  <Box>
                    <Grid container spacing={3}>
                      <Grid item xs={12} md={6}>
                        <TextField
                          fullWidth
                          label="Panel Name"
                          value={selectedPanel.name}
                          onChange={(e) => setSelectedPanel({
                            ...selectedPanel,
                            name: e.target.value,
                          })}
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth>
                          <InputLabel>Status</InputLabel>
                          <Select
                            value={selectedPanel.is_published ? 'published' : 'draft'}
                            label="Status"
                          >
                            <MenuItem value="draft">Draft</MenuItem>
                            <MenuItem value="published">Published</MenuItem>
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12}>
                        <TextField
                          fullWidth
                          multiline
                          rows={3}
                          label="Description"
                          value={selectedPanel.description || ''}
                          onChange={(e) => setSelectedPanel({
                            ...selectedPanel,
                            description: e.target.value,
                          })}
                        />
                      </Grid>
                    </Grid>
                  </Box>
                )}

                {/* Code Tab */}
                {tab === 3 && (
                  <Box>
                    <Alert severity="info" sx={{ mb: 2 }}>
                      Export this panel as React components for your own codebase.
                    </Alert>
                    <Paper 
                      sx={{ 
                        p: 2, 
                        bgcolor: '#f9fafb', 
                        color: '#000000',
                        fontFamily: 'monospace',
                        fontSize: 12,
                        overflow: 'auto',
                        maxHeight: 400,
                        border: '1px solid #e5e7eb',
                      }}
                    >
                      <pre>{`// ${selectedPanel.name} - Generated by Faibric
import React from 'react';
import { Grid, Card, CardContent, Typography } from '@mui/material';

const ${selectedPanel.name.replace(/\s+/g, '')}Panel = () => {
  return (
    <Grid container spacing={3}>
${widgets.map(w => `      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6">${w.title}</Typography>
            {/* ${w.type} widget */}
          </CardContent>
        </Card>
      </Grid>`).join('\n')}
    </Grid>
  );
};

export default ${selectedPanel.name.replace(/\s+/g, '')}Panel;`}</pre>
                    </Paper>
                    <Button 
                      variant="outlined" 
                      sx={{ mt: 2 }}
                    >
                      Download as React Component
                    </Button>
                  </Box>
                )}
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>

      {/* Add Widget Dialog */}
      <Dialog open={showWidgetDialog} onClose={() => setShowWidgetDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ color: '#000000' }}>Add Widget</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ color: '#374151', mb: 2 }}>
            Select a widget type to add to your panel
          </Typography>
          <Grid container spacing={2}>
            {WIDGET_TYPES.map((wt) => (
              <Grid item xs={6} key={wt.type}>
                <Card 
                  sx={{ 
                    p: 2, 
                    textAlign: 'center', 
                    cursor: 'pointer',
                    border: selectedWidgetType === wt.type ? '2px solid #2563eb' : '1px solid #e5e7eb',
                    '&:hover': { bgcolor: '#f9fafb' },
                  }}
                  onClick={() => setSelectedWidgetType(wt.type)}
                >
                  <Typography variant="body2" sx={{ color: '#000000' }}>{wt.label}</Typography>
                </Card>
              </Grid>
            ))}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowWidgetDialog(false)}>Cancel</Button>
          <Button 
            variant="contained" 
            disabled={!selectedWidgetType}
            onClick={() => selectedWidgetType && handleAddWidget(selectedWidgetType)}
          >
            Add Widget
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}

export default AdminPanelBuilder
