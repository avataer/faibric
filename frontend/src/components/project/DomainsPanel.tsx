import { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Alert,
  Skeleton,
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import RefreshIcon from '@mui/icons-material/Refresh'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import { projectServicesApi, Domain } from '../../services/projectServices'

interface DomainsPanelProps {
  projectId: number | string
}

export const DomainsPanel = ({ projectId }: DomainsPanelProps) => {
  const [domains, setDomains] = useState<Domain[]>([])
  const [loading, setLoading] = useState(true)
  const [newDomain, setNewDomain] = useState('')
  const [adding, setAdding] = useState(false)
  const [selectedDomain, setSelectedDomain] = useState<Domain | null>(null)
  const [dnsDialog, setDnsDialog] = useState(false)

  useEffect(() => {
    fetchDomains()
  }, [projectId])

  const fetchDomains = async () => {
    setLoading(true)
    try {
      const result = await projectServicesApi.getDomains(projectId)
      setDomains(result.domains || [])
    } catch {
      // Failed to fetch domains
    }
    setLoading(false)
  }

  const handleAddDomain = async () => {
    if (!newDomain.trim()) return
    setAdding(true)
    try {
      const result = await projectServicesApi.addDomain(projectId, newDomain.trim().toLowerCase())
      if (result.success) {
        setNewDomain('')
        fetchDomains()
        // Show DNS instructions
        const addedDomain = {
          domain: result.domain,
          is_verified: result.is_verified,
          ssl_status: 'pending',
          dns_records: result.dns_records,
          is_primary: false,
        }
        setSelectedDomain(addedDomain)
        setDnsDialog(true)
      }
    } catch (error: any) {
      alert(error.response?.data?.error || 'Failed to add domain')
    }
    setAdding(false)
  }

  const handleVerify = async (domain: string) => {
    try {
      const result = await projectServicesApi.verifyDomain(projectId, domain)
      if (result.is_verified) {
        alert('Domain verified successfully!')
      } else {
        alert('Domain not yet verified. Please check your DNS settings.')
      }
      fetchDomains()
    } catch {
      // Verification failed
    }
  }

  const handleRemove = async (domain: string) => {
    if (!confirm(`Remove ${domain}?`)) return
    try {
      await projectServicesApi.removeDomain(projectId, domain)
      fetchDomains()
    } catch {
      // Failed to remove domain
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  if (loading) {
    return (
      <Box>
        <Skeleton variant="rounded" height={56} sx={{ mb: 2 }} />
        <Skeleton variant="rounded" height={200} />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h6" fontWeight={600} gutterBottom>
        Custom Domains
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Connect your own domain to your app. We'll handle SSL automatically.
      </Typography>

      {/* Add Domain Form */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            fullWidth
            label="Domain"
            placeholder="example.com or app.example.com"
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            size="small"
          />
          <Button variant="contained" onClick={handleAddDomain} disabled={adding || !newDomain.trim()}>
            {adding ? 'Adding...' : 'Add Domain'}
          </Button>
        </Box>
      </Paper>

      {/* Domains List */}
      {domains.length > 0 ? (
        <Paper>
          <List disablePadding>
            {domains.map((domain) => (
              <ListItem
                key={domain.domain}
                sx={{
                  borderBottom: '1px solid',
                  borderColor: 'divider',
                  '&:last-child': { borderBottom: 'none' },
                }}
              >
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1" fontWeight={500}>
                        {domain.domain}
                      </Typography>
                      {domain.is_primary && <Chip label="Primary" size="small" color="primary" />}
                      <Chip
                        label={domain.is_verified ? 'Verified' : 'Pending'}
                        size="small"
                        color={domain.is_verified ? 'success' : 'warning'}
                      />
                      <Chip
                        label={`SSL: ${domain.ssl_status}`}
                        size="small"
                        variant="outlined"
                      />
                    </Box>
                  }
                />
                <ListItemSecondaryAction>
                  {!domain.is_verified && (
                    <>
                      <Button
                        size="small"
                        onClick={() => {
                          setSelectedDomain(domain)
                          setDnsDialog(true)
                        }}
                        sx={{ mr: 1 }}
                      >
                        View DNS
                      </Button>
                      <IconButton onClick={() => handleVerify(domain.domain)} title="Check verification">
                        <RefreshIcon />
                      </IconButton>
                    </>
                  )}
                  <IconButton onClick={() => handleRemove(domain.domain)} color="error">
                    <DeleteIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </Paper>
      ) : (
        <Alert severity="info">
          No custom domains configured. Add a domain above to get started.
        </Alert>
      )}

      {/* DNS Instructions Dialog */}
      <Dialog open={dnsDialog} onClose={() => setDnsDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Configure DNS for {selectedDomain?.domain}</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 3 }}>
            Add the following DNS records at your domain registrar (GoDaddy, Namecheap, Cloudflare,
            etc.)
          </Alert>

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Type</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Value</TableCell>
                <TableCell>Copy</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {selectedDomain?.dns_records?.map((record, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <Chip label={record.type} size="small" />
                  </TableCell>
                  <TableCell sx={{ fontFamily: 'monospace' }}>{record.name}</TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', maxWidth: 300, wordBreak: 'break-all' }}>
                    {record.value}
                  </TableCell>
                  <TableCell>
                    <IconButton size="small" onClick={() => copyToClipboard(record.value)}>
                      <ContentCopyIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <Alert severity="warning" sx={{ mt: 3 }}>
            DNS changes can take up to 48 hours to propagate, but usually complete within 5-10
            minutes.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDnsDialog(false)}>Close</Button>
          <Button
            variant="contained"
            onClick={() => {
              handleVerify(selectedDomain!.domain)
              setDnsDialog(false)
            }}
          >
            Verify Now
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default DomainsPanel



