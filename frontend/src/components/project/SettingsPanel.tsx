import { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  Switch,
  FormControlLabel,
  Button,
  TextField,
  Divider,
  Alert,
  Chip,
  Grid,
  Skeleton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { projectServicesApi, AuthConfig } from '../../services/projectServices'

interface SettingsPanelProps {
  projectId: number | string
}

export const SettingsPanel = ({ projectId }: SettingsPanelProps) => {
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // OAuth credentials (only shown if enabled)
  const [googleClientId, setGoogleClientId] = useState('')
  const [googleClientSecret, setGoogleClientSecret] = useState('')
  const [githubClientId, setGithubClientId] = useState('')
  const [githubClientSecret, setGithubClientSecret] = useState('')

  useEffect(() => {
    fetchAuthConfig()
  }, [projectId])

  const fetchAuthConfig = async () => {
    setLoading(true)
    try {
      const result = await projectServicesApi.getAuthConfig(projectId)
      if ('configured' in result && result.configured === false) {
        // Not configured yet, use defaults
        setAuthConfig({
          email_password: true,
          magic_link: true,
          google_oauth: false,
          github_oauth: false,
          status: 'pending',
        })
      } else {
        setAuthConfig(result as AuthConfig)
      }
    } catch (error) {
      console.error('Failed to fetch auth config:', error)
    }
    setLoading(false)
  }

  const handleSave = async () => {
    if (!authConfig) return
    setSaving(true)
    try {
      await projectServicesApi.configureAuth(projectId, {
        email_password: authConfig.email_password,
        magic_link: authConfig.magic_link,
        google_oauth: authConfig.google_oauth,
        github_oauth: authConfig.github_oauth,
      })
      alert('Settings saved!')
    } catch (error) {
      console.error('Failed to save:', error)
      alert('Failed to save settings')
    }
    setSaving(false)
  }

  const toggleAuth = (key: keyof AuthConfig) => {
    if (!authConfig) return
    setAuthConfig({
      ...authConfig,
      [key]: !authConfig[key],
    })
  }

  if (loading) {
    return (
      <Box>
        <Skeleton variant="rounded" height={200} sx={{ mb: 2 }} />
        <Skeleton variant="rounded" height={150} />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h6" fontWeight={600} gutterBottom>
        Project Settings
      </Typography>

      {/* Authentication Section */}
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="subtitle1" fontWeight={600}>
              Authentication
            </Typography>
            <Chip
              label={authConfig?.status === 'active' ? 'Active' : 'Not configured'}
              size="small"
              color={authConfig?.status === 'active' ? 'success' : 'default'}
            />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Alert severity="info" sx={{ mb: 3 }}>
            Enable authentication to add user login/signup to your app. This uses Supabase Auth.
          </Alert>

          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={authConfig?.email_password || false}
                      onChange={() => toggleAuth('email_password')}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="subtitle2">Email & Password</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Traditional email/password login
                      </Typography>
                    </Box>
                  }
                />
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={authConfig?.magic_link || false}
                      onChange={() => toggleAuth('magic_link')}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="subtitle2">Magic Link</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Passwordless email login
                      </Typography>
                    </Box>
                  }
                />
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={authConfig?.google_oauth || false}
                      onChange={() => toggleAuth('google_oauth')}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="subtitle2">Google OAuth</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Sign in with Google
                      </Typography>
                    </Box>
                  }
                />
                {authConfig?.google_oauth && (
                  <Box sx={{ mt: 2, pl: 4 }}>
                    <TextField
                      fullWidth
                      size="small"
                      label="Client ID"
                      value={googleClientId}
                      onChange={(e) => setGoogleClientId(e.target.value)}
                      sx={{ mb: 1 }}
                    />
                    <TextField
                      fullWidth
                      size="small"
                      label="Client Secret"
                      type="password"
                      value={googleClientSecret}
                      onChange={(e) => setGoogleClientSecret(e.target.value)}
                    />
                  </Box>
                )}
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={authConfig?.github_oauth || false}
                      onChange={() => toggleAuth('github_oauth')}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="subtitle2">GitHub OAuth</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Sign in with GitHub
                      </Typography>
                    </Box>
                  }
                />
                {authConfig?.github_oauth && (
                  <Box sx={{ mt: 2, pl: 4 }}>
                    <TextField
                      fullWidth
                      size="small"
                      label="Client ID"
                      value={githubClientId}
                      onChange={(e) => setGithubClientId(e.target.value)}
                      sx={{ mb: 1 }}
                    />
                    <TextField
                      fullWidth
                      size="small"
                      label="Client Secret"
                      type="password"
                      value={githubClientSecret}
                      onChange={(e) => setGithubClientSecret(e.target.value)}
                    />
                  </Box>
                )}
              </Paper>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Database Section */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1" fontWeight={600}>
            Database
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Alert severity="info" sx={{ mb: 2 }}>
            Your app can use Supabase for data storage. Database is auto-provisioned when your app
            needs it.
          </Alert>
          <Button variant="outlined" onClick={() => projectServicesApi.provisionDatabase(projectId, 'app')}>
            Provision Database
          </Button>
        </AccordionDetails>
      </Accordion>

      {/* Payments Section */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1" fontWeight={600}>
            Payments (Stripe)
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Alert severity="info" sx={{ mb: 2 }}>
            Connect Stripe to accept payments in your app.
          </Alert>
          <Button variant="outlined">Connect Stripe</Button>
        </AccordionDetails>
      </Accordion>

      <Divider sx={{ my: 3 }} />

      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button variant="contained" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Settings'}
        </Button>
      </Box>
    </Box>
  )
}

export default SettingsPanel

