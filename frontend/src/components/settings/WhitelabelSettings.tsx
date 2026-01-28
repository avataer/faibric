import { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  Switch,
  FormControlLabel,
  Button,
  TextField,
  Grid,
  Skeleton,
  Alert,
  Chip,
  Divider,
} from '@mui/material'
import api from '../../services/api'

interface WhitelabelConfig {
  company_name: string
  logo_url: string
  favicon_url: string
  primary_color: string
  secondary_color: string
  accent_color: string
  custom_domain: string
  domain_verified: boolean
  custom_css_enabled: boolean
  hide_powered_by: boolean
}

const defaultConfig: WhitelabelConfig = {
  company_name: '',
  logo_url: '',
  favicon_url: '',
  primary_color: '#1976d2',
  secondary_color: '#dc004e',
  accent_color: '#9c27b0',
  custom_domain: '',
  domain_verified: false,
  custom_css_enabled: false,
  hide_powered_by: false,
}

export const WhitelabelSettings = () => {
  const [config, setConfig] = useState<WhitelabelConfig>(defaultConfig)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/tenants/whitelabel/')
      setConfig({ ...defaultConfig, ...response.data })
    } catch {
      setError('Failed to load white-label configuration')
    }
    setLoading(false)
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await api.put('/api/tenants/whitelabel/', config)
      setSuccess('White-label settings saved successfully')
    } catch {
      setError('Failed to save white-label settings')
    }
    setSaving(false)
  }

  const handleVerifyDomain = async () => {
    if (!config.custom_domain) {
      setError('Please enter a custom domain first')
      return
    }
    setVerifying(true)
    setError(null)
    try {
      const response = await api.post('/api/tenants/whitelabel/verify-domain/', {
        domain: config.custom_domain,
      })
      if (response.data.verified) {
        setConfig({ ...config, domain_verified: true })
        setSuccess('Domain verified successfully')
      } else {
        setError(response.data.message || 'Domain verification failed')
      }
    } catch {
      setError('Failed to verify domain. Please check DNS settings.')
    }
    setVerifying(false)
  }

  const updateConfig = (field: keyof WhitelabelConfig, value: string | boolean) => {
    if (field === 'custom_domain') {
      setConfig({ ...config, custom_domain: value as string, domain_verified: false })
    } else {
      setConfig({ ...config, [field]: value })
    }
  }

  if (loading) {
    return (
      <Box>
        <Skeleton variant="rounded" height={200} sx={{ mb: 2 }} />
        <Skeleton variant="rounded" height={200} sx={{ mb: 2 }} />
        <Skeleton variant="rounded" height={150} />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h6" fontWeight={600} gutterBottom>
        White-Label Settings
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Customize the appearance and branding of your application
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Company Branding Section */}
      <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Company Branding
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Company Name"
              value={config.company_name}
              onChange={(e) => updateConfig('company_name', e.target.value)}
              placeholder="Your Company Name"
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Logo URL"
              value={config.logo_url}
              onChange={(e) => updateConfig('logo_url', e.target.value)}
              placeholder="https://example.com/logo.png"
              helperText="URL to your company logo (recommended: 200x50px)"
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Favicon URL"
              value={config.favicon_url}
              onChange={(e) => updateConfig('favicon_url', e.target.value)}
              placeholder="https://example.com/favicon.ico"
              helperText="URL to your favicon (recommended: 32x32px)"
            />
          </Grid>
        </Grid>
      </Paper>

      {/* Brand Colors Section */}
      <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Brand Colors
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              type="color"
              label="Primary Color"
              value={config.primary_color}
              onChange={(e) => updateConfig('primary_color', e.target.value)}
              InputProps={{
                sx: { height: 56 },
              }}
              helperText="Main brand color"
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              type="color"
              label="Secondary Color"
              value={config.secondary_color}
              onChange={(e) => updateConfig('secondary_color', e.target.value)}
              InputProps={{
                sx: { height: 56 },
              }}
              helperText="Secondary accent color"
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              type="color"
              label="Accent Color"
              value={config.accent_color}
              onChange={(e) => updateConfig('accent_color', e.target.value)}
              InputProps={{
                sx: { height: 56 },
              }}
              helperText="Highlight color for actions"
            />
          </Grid>
        </Grid>
      </Paper>

      {/* Custom Domain Section */}
      <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <Typography variant="subtitle1" fontWeight={600}>
            Custom Domain
          </Typography>
          <Chip
            label={config.domain_verified ? 'Verified' : 'Not verified'}
            size="small"
            color={config.domain_verified ? 'success' : 'default'}
          />
        </Box>
        <Grid container spacing={2} alignItems="flex-start">
          <Grid item xs={12} md={8}>
            <TextField
              fullWidth
              label="Custom Domain"
              value={config.custom_domain}
              onChange={(e) => updateConfig('custom_domain', e.target.value)}
              placeholder="app.yourdomain.com"
              helperText="Enter your custom domain (CNAME record required)"
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <Button
              variant="outlined"
              fullWidth
              onClick={handleVerifyDomain}
              disabled={verifying || !config.custom_domain}
              sx={{ height: 56 }}
            >
              {verifying ? 'Verifying...' : 'Verify Domain'}
            </Button>
          </Grid>
        </Grid>
        {config.custom_domain && !config.domain_verified && (
          <Alert severity="info" sx={{ mt: 2 }}>
            Add a CNAME record pointing {config.custom_domain} to your application domain, then click Verify Domain.
          </Alert>
        )}
      </Paper>

      {/* Additional Options Section */}
      <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Additional Options
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <FormControlLabel
            control={
              <Switch
                checked={config.custom_css_enabled}
                onChange={(e) => updateConfig('custom_css_enabled', e.target.checked)}
              />
            }
            label={
              <Box>
                <Typography variant="body2">Enable Custom CSS</Typography>
                <Typography variant="caption" color="text.secondary">
                  Allow custom CSS styles for advanced customization
                </Typography>
              </Box>
            }
          />
          <FormControlLabel
            control={
              <Switch
                checked={config.hide_powered_by}
                onChange={(e) => updateConfig('hide_powered_by', e.target.checked)}
              />
            }
            label={
              <Box>
                <Typography variant="body2">Hide Powered By</Typography>
                <Typography variant="caption" color="text.secondary">
                  Remove the powered by attribution from the footer
                </Typography>
              </Box>
            }
          />
        </Box>
      </Paper>

      {/* Preview Section */}
      <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Preview
        </Typography>
        <Box
          sx={{
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1,
            overflow: 'hidden',
          }}
        >
          {/* Preview Header */}
          <Box
            sx={{
              bgcolor: config.primary_color,
              color: '#fff',
              p: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 2,
            }}
          >
            {config.logo_url ? (
              <Box
                component="img"
                src={config.logo_url}
                alt="Logo"
                sx={{ height: 32, maxWidth: 120, objectFit: 'contain' }}
                onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                  e.currentTarget.style.display = 'none'
                }}
              />
            ) : (
              <Typography variant="h6" fontWeight={600}>
                {config.company_name || 'Your Company'}
              </Typography>
            )}
          </Box>
          {/* Preview Content */}
          <Box sx={{ p: 3, bgcolor: 'background.paper' }}>
            <Typography variant="body1" gutterBottom>
              This is a preview of your branding
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
              <Button
                variant="contained"
                sx={{
                  bgcolor: config.primary_color,
                  '&:hover': { bgcolor: config.primary_color, filter: 'brightness(0.9)' },
                }}
              >
                Primary Button
              </Button>
              <Button
                variant="contained"
                sx={{
                  bgcolor: config.secondary_color,
                  '&:hover': { bgcolor: config.secondary_color, filter: 'brightness(0.9)' },
                }}
              >
                Secondary Button
              </Button>
              <Button
                variant="outlined"
                sx={{
                  color: config.accent_color,
                  borderColor: config.accent_color,
                  '&:hover': { borderColor: config.accent_color, bgcolor: `${config.accent_color}10` },
                }}
              >
                Accent Button
              </Button>
            </Box>
          </Box>
          {/* Preview Footer */}
          {!config.hide_powered_by && (
            <Box
              sx={{
                bgcolor: 'grey.100',
                p: 1,
                textAlign: 'center',
              }}
            >
              <Typography variant="caption" color="text.secondary">
                Powered by Faibric
              </Typography>
            </Box>
          )}
        </Box>
      </Paper>

      <Divider sx={{ my: 3 }} />

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
        <Button variant="outlined" onClick={fetchConfig} disabled={loading}>
          Reset
        </Button>
        <Button variant="contained" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Settings'}
        </Button>
      </Box>
    </Box>
  )
}

export default WhitelabelSettings
