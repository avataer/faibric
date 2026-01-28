import { useState, useEffect } from "react"
import {
  Box,
  Paper,
  Typography,
  RadioGroup,
  FormControlLabel,
  Radio,
  CircularProgress,
} from "@mui/material"
import { api } from "../../services/api"

interface ModelConfig {
  key: string
  id: string
  name: string
  provider: string
  description: string
  credits_per_request: number
  max_tokens: number
}

interface ModelSelectorProps {
  selectedModel: string
  onModelChange: (modelKey: string) => void
}

const ModelSelector = ({ selectedModel, onModelChange }: ModelSelectorProps) => {
  const [models, setModels] = useState<ModelConfig[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await api.get("/api/ai/models/")
        if (response.data.models) {
          setModels(response.data.models)
        }
      } catch (err) {
        setError("Failed to load models")
      } finally {
        setIsLoading(false)
      }
    }
    fetchModels()
  }, [])

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onModelChange(event.target.value)
  }

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 2 }}>
        <CircularProgress size={24} />
      </Box>
    )
  }

  if (error) {
    return (
      <Typography color="error" sx={{ p: 2 }}>
        {error}
      </Typography>
    )
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Select AI Model
      </Typography>
      <RadioGroup value={selectedModel} onChange={handleChange}>
        {models.map((model) => (
          <Paper
            key={model.key}
            sx={{
              p: 2,
              mb: 1,
              cursor: "pointer",
              border: selectedModel === model.key ? "2px solid #1976d2" : "1px solid #e0e0e0",
              "&:hover": { backgroundColor: "#f5f5f5" },
            }}
            onClick={() => onModelChange(model.key)}
          >
            <FormControlLabel
              value={model.key}
              control={<Radio />}
              label={
                <Box>
                  <Typography variant="subtitle1" fontWeight="bold">
                    {model.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {model.description}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {model.credits_per_request} credit{model.credits_per_request !== 1 ? "s" : ""} per request
                  </Typography>
                </Box>
              }
              sx={{ m: 0, width: "100%" }}
            />
          </Paper>
        ))}
      </RadioGroup>
    </Box>
  )
}

export default ModelSelector
