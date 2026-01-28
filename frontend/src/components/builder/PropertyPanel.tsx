import React, { useState, useEffect, ChangeEvent } from "react"
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  SelectChangeEvent,
} from "@mui/material"
import CloseIcon from "@mui/icons-material/Close"

interface PropertyValue {
  text?: string
  src?: string
  backgroundColor?: string
  color?: string
  fontSize?: number
  padding?: number
  borderRadius?: number
  fontFamily?: string
}

interface PropertyPanelProps {
  elementType: string
  currentValue: PropertyValue
  onApply: (value: PropertyValue) => void
  onCancel: () => void
}

const PropertyPanel: React.FC<PropertyPanelProps> = ({ elementType, currentValue, onApply, onCancel }) => {
  const [value, setValue] = useState<PropertyValue>(currentValue || {})

  useEffect(() => {
    setValue(currentValue || {})
  }, [currentValue])

  const handleApply = () => {
    onApply(value)
  }

  const handleCancel = () => {
    onCancel()
  }

  const renderTextEditor = (): React.ReactNode => (
    <Box sx={{ mb: 2 }}>
      <TextField
        fullWidth
        multiline
        rows={4}
        label="Text Content"
        value={value.text || ""}
        onChange={(e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setValue({ ...value, text: e.target.value })}
      />
    </Box>
  )

  const renderButtonEditor = (): React.ReactNode => (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mb: 2 }}>
      <TextField
        fullWidth
        label="Button Text"
        value={value.text || ""}
        onChange={(e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setValue({ ...value, text: e.target.value })}
      />
      <Box>
        <Typography variant="body2" sx={{ mb: 1 }}>
          Background Color
        </Typography>
        <input
          type="color"
          value={value.backgroundColor || "#1976d2"}
          onChange={(e: ChangeEvent<HTMLInputElement>) => setValue({ ...value, backgroundColor: e.target.value })}
          style={{ width: "100%", height: 40, cursor: "pointer", border: "1px solid #ccc", borderRadius: 4 }}
        />
      </Box>
    </Box>
  )

  const renderImageEditor = (): React.ReactNode => (
    <Box sx={{ mb: 2 }}>
      <TextField
        fullWidth
        label="Image URL"
        placeholder="https://example.com/image.png"
        value={value.src || ""}
        onChange={(e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setValue({ ...value, src: e.target.value })}
      />
      {value.src && (
        <Box sx={{ mt: 2, textAlign: "center" }}>
          <img
            src={value.src}
            alt="Preview"
            style={{ maxWidth: "100%", maxHeight: 150, objectFit: "contain" }}
            onError={(e: React.SyntheticEvent<HTMLImageElement>) => { e.currentTarget.style.display = "none" }}
          />
        </Box>
      )}
    </Box>
  )

  const renderStyleEditor = (): React.ReactNode => (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mb: 2 }}>
      <Box>
        <Typography variant="body2" sx={{ mb: 1 }}>
          Text Color
        </Typography>
        <input
          type="color"
          value={value.color || "#000000"}
          onChange={(e: ChangeEvent<HTMLInputElement>) => setValue({ ...value, color: e.target.value })}
          style={{ width: "100%", height: 40, cursor: "pointer", border: "1px solid #ccc", borderRadius: 4 }}
        />
      </Box>
      <Box>
        <Typography variant="body2" sx={{ mb: 1 }}>
          Background Color
        </Typography>
        <input
          type="color"
          value={value.backgroundColor || "#ffffff"}
          onChange={(e: ChangeEvent<HTMLInputElement>) => setValue({ ...value, backgroundColor: e.target.value })}
          style={{ width: "100%", height: 40, cursor: "pointer", border: "1px solid #ccc", borderRadius: 4 }}
        />
      </Box>
      <TextField
        fullWidth
        type="number"
        label="Font Size (px)"
        value={value.fontSize || 16}
        onChange={(e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setValue({ ...value, fontSize: parseInt(e.target.value, 10) || 16 })}
        inputProps={{ min: 8, max: 72 }}
      />
      <TextField
        fullWidth
        type="number"
        label="Padding (px)"
        value={value.padding || 0}
        onChange={(e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setValue({ ...value, padding: parseInt(e.target.value, 10) || 0 })}
        inputProps={{ min: 0, max: 100 }}
      />
      <TextField
        fullWidth
        type="number"
        label="Border Radius (px)"
        value={value.borderRadius || 0}
        onChange={(e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setValue({ ...value, borderRadius: parseInt(e.target.value, 10) || 0 })}
        inputProps={{ min: 0, max: 50 }}
      />
      <FormControl fullWidth>
        <InputLabel>Font Family</InputLabel>
        <Select
          value={value.fontFamily || "inherit"}
          onChange={(e: SelectChangeEvent) => setValue({ ...value, fontFamily: e.target.value })}
          label="Font Family"
        >
          <MenuItem value="inherit">Default</MenuItem>
          <MenuItem value="Arial, sans-serif">Arial</MenuItem>
          <MenuItem value="Helvetica, sans-serif">Helvetica</MenuItem>
          <MenuItem value="Georgia, serif">Georgia</MenuItem>
          <MenuItem value="Times New Roman, serif">Times New Roman</MenuItem>
          <MenuItem value="Courier New, monospace">Courier New</MenuItem>
          <MenuItem value="Verdana, sans-serif">Verdana</MenuItem>
        </Select>
      </FormControl>
    </Box>
  )

  const renderEditorByType = (): React.ReactNode => {
    switch (elementType) {
      case "text":
        return renderTextEditor()
      case "button":
        return renderButtonEditor()
      case "image":
        return renderImageEditor()
      case "style":
        return renderStyleEditor()
      default:
        return (
          <Typography color="text.secondary">
            Unknown element type: {elementType}
          </Typography>
        )
    }
  }

  const getElementTypeLabel = (): string => {
    const labels: Record<string, string> = {
      text: "Text Element",
      button: "Button Element",
      image: "Image Element",
      style: "Style Properties",
    }
    return labels[elementType] || "Element"
  }

  return (
    <Paper
      sx={{
        position: "fixed",
        top: 0,
        right: 0,
        width: 320,
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        boxShadow: "-4px 0 12px rgba(0, 0, 0, 0.15)",
        zIndex: 1200,
      }}
      elevation={8}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          p: 2,
          borderBottom: "1px solid #e0e0e0",
          backgroundColor: "#f5f5f5",
        }}
      >
        <Typography variant="h6" fontWeight="bold">
          {getElementTypeLabel()}
        </Typography>
        <IconButton size="small" onClick={handleCancel}>
          <CloseIcon />
        </IconButton>
      </Box>

      {/* Content */}
      <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
        {renderEditorByType()}
      </Box>

      {/* Actions */}
      <Box
        sx={{
          display: "flex",
          gap: 1,
          p: 2,
          borderTop: "1px solid #e0e0e0",
        }}
      >
        <Button
          variant="outlined"
          fullWidth
          onClick={handleCancel}
        >
          Cancel
        </Button>
        <Button
          variant="contained"
          fullWidth
          onClick={handleApply}
        >
          Apply
        </Button>
      </Box>
    </Paper>
  )
}

export default PropertyPanel
