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
  Divider,
  RadioGroup,
  Radio,
  FormControl,
  FormLabel,
  Select,
  MenuItem,
  InputLabel,
} from '@mui/material'
import api from '../../services/api'

const defaultConfig = {
  enabled: false,
  sso_type: 'saml',
  // SAML settings
  idp_entity_id: '',
  sso_url: '',
  certificate: '',
  // OIDC settings
  issuer_url: '',
  client_id: '',
  client_secret: '',
  // Common settings
  domain_restriction: '',
  auto_provision_users: false,
  default_role: 'member',
}

export const SSOSettings = () => {
  const [config, setConfig] = useState(defaultConfig)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/tenants/sso/config/')
      setConfig({ ...defaultConfig, ...response.data })
    } catch {
      setError('Failed to load SSO configuration')
    }
    setLoading(false)
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await api.put('/api/tenants/sso/config/', config)
      setSuccess('SSO settings saved successfully')
    } catch {
      setError('Failed to save SSO settings')
    }
    setSaving(false)
  }

  const handleTestSSO = async () => {
    setTesting(true)
    setError(null)
    try {
      const response = await api.get('/api/tenants/sso/login-url/')
      if (response.data.url) {
        window.open(response.data.url, '_blank')
      }
    } catch {
      setError('Failed to get SSO login URL')
    }
    setTesting(false)
  }

  const updateConfig = (field: string, value: string | boolean) => {
    setConfig({ ...config, [field]: value })
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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            SSO Settings
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure Single Sign-On for your organization
          </Typography>
        </Box>
        <FormControlLabel
          control={
            <Switch
              checked={config.enabled}
              onChange={(e) => updateConfig('enabled', e.target.checked)}
            />
          }
          label={config.enabled ? 'Enabled' : 'Disabled'}
        />
      </Box>

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

      {/* SSO Type Selection */}
      <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
        <FormControl component="fieldset">
          <FormLabel component="legend">
            <Typography variant="subtitle1" fontWeight={600}>
              SSO Type
            </Typography>
          </FormLabel>
          <RadioGroup
            row
            value={config.sso_type}
            onChange={(e) => updateConfig('sso_type', e.target.value)}
          >
            <FormControlLabel value="saml" control={<Radio />} label="SAML 2.0" />
            <FormControlLabel value="oidc" control={<Radio />} label="OpenID Connect (OIDC)" />
          </RadioGroup>
        </FormControl>
      </Paper>

      {/* SAML Configuration */}
      {config.sso_type === 'saml' && (
        <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            SAML Configuration
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="IdP Entity ID"
                value={config.idp_entity_id}
                onChange={(e) => updateConfig('idp_entity_id', e.target.value)}
                placeholder="https://idp.example.com/metadata"
                helperText="The Entity ID from your Identity Provider"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="SSO URL"
                value={config.sso_url}
                onChange={(e) => updateConfig('sso_url', e.target.value)}
                placeholder="https://idp.example.com/sso/saml"
                helperText="The Single Sign-On URL from your Identity Provider"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={6}
                label="X.509 Certificate"
                value={config.certificate}
                onChange={(e) => updateConfig('certificate', e.target.value)}
                placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
                helperText="The public X.509 certificate from your Identity Provider"
              />
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* OIDC Configuration */}
      {config.sso_type === 'oidc' && (
        <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            OIDC Configuration
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Issuer URL"
                value={config.issuer_url}
                onChange={(e) => updateConfig('issuer_url', e.target.value)}
                placeholder="https://accounts.google.com"
                helperText="The OIDC issuer URL from your Identity Provider"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Client ID"
                value={config.client_id}
                onChange={(e) => updateConfig('client_id', e.target.value)}
                placeholder="your-client-id"
                helperText="The client ID from your Identity Provider"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="password"
                label="Client Secret"
                value={config.client_secret}
                onChange={(e) => updateConfig('client_secret', e.target.value)}
                placeholder="your-client-secret"
                helperText="The client secret from your Identity Provider"
              />
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* Common Settings */}
      <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Common Settings
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Domain Restriction"
              value={config.domain_restriction}
              onChange={(e) => updateConfig('domain_restriction', e.target.value)}
              placeholder="@company.com"
              helperText="Only allow users with this email domain"
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Default Role</InputLabel>
              <Select
                value={config.default_role}
                label="Default Role"
                onChange={(e) => updateConfig('default_role', e.target.value)}
              >
                <MenuItem value="viewer">Viewer</MenuItem>
                <MenuItem value="member">Member</MenuItem>
                <MenuItem value="admin">Admin</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={config.auto_provision_users}
                  onChange={(e) => updateConfig('auto_provision_users', e.target.checked)}
                />
              }
              label={
                <Box>
                  <Typography variant="body2">Auto-provision Users</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Automatically create accounts for new SSO users
                  </Typography>
                </Box>
              }
            />
          </Grid>
        </Grid>
      </Paper>

      <Divider sx={{ my: 3 }} />

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
        <Button
          variant="outlined"
          onClick={handleTestSSO}
          disabled={testing || !config.enabled}
        >
          {testing ? 'Opening...' : 'Test SSO'}
        </Button>
        <Button variant="outlined" onClick={fetchConfig} disabled={loading}>
          Reset
        </Button>
        <Button variant="contained" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Configuration'}
        </Button>
      </Box>
    </Box>
  )
}

export default SSOSettings
