import React, { useState, useCallback, DragEvent } from "react"
import {
  Box,
  IconButton,
  Typography,
  Tooltip,
  Paper,
} from "@mui/material"
import DragIndicatorIcon from "@mui/icons-material/DragIndicator"
import ContentCopyIcon from "@mui/icons-material/ContentCopy"
import DeleteIcon from "@mui/icons-material/Delete"
import AddIcon from "@mui/icons-material/Add"
import { Section } from "./sectionTypes"

interface DragDropSectionEditorProps {
  sections: Section[]
  onReorder: (fromIndex: number, toIndex: number) => void
  onDuplicate: (sectionId: string) => void
  onDelete: (sectionId: string) => void
  onAddSection: () => void
}

const DragDropSectionEditor: React.FC<DragDropSectionEditorProps> = ({
  sections,
  onReorder,
  onDuplicate,
  onDelete,
  onAddSection,
}) => {
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)

  const handleDragStart = useCallback((e: DragEvent<HTMLDivElement>, index: number) => {
    setDraggedIndex(index)
    e.dataTransfer.effectAllowed = "move"
    e.dataTransfer.setData("text/plain", String(index))
  }, [])

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>, index: number) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = "move"
    setDragOverIndex(index)
  }, [])

  const handleDragLeave = useCallback(() => {
    setDragOverIndex(null)
  }, [])

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>, toIndex: number) => {
    e.preventDefault()
    const fromIndex = draggedIndex
    setDraggedIndex(null)
    setDragOverIndex(null)

    if (fromIndex === null || fromIndex === toIndex) return
    onReorder(fromIndex, toIndex)
  }, [draggedIndex, onReorder])

  const handleDragEnd = useCallback(() => {
    setDraggedIndex(null)
    setDragOverIndex(null)
  }, [])

  if (sections.length === 0) {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          py: 8,
          px: 2,
        }}
      >
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          No sections yet. Add your first section to get started.
        </Typography>
        <Tooltip title="Add a section">
          <IconButton
            onClick={onAddSection}
            sx={{
              backgroundColor: "#1976d2",
              color: "#ffffff",
              "&:hover": {
                backgroundColor: "#1565c0",
              },
              width: 48,
              height: 48,
            }}
          >
            <AddIcon />
          </IconButton>
        </Tooltip>
      </Box>
    )
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1, p: 1 }}>
      {sections.map((section, index) => {
        const isDragged = draggedIndex === index
        const isDragOver = dragOverIndex === index
        const showDropIndicator = isDragOver && draggedIndex !== null && draggedIndex !== index

        return (
          <Box key={section.id}>
            {/* Drop indicator line above */}
            {showDropIndicator && draggedIndex !== null && draggedIndex > index && (
              <Box
                sx={{
                  height: 3,
                  backgroundColor: "#1976d2",
                  borderRadius: 1,
                  mb: 0.5,
                }}
              />
            )}

            <Paper
              draggable
              onDragStart={(e) => handleDragStart(e, index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, index)}
              onDragEnd={handleDragEnd}
              elevation={isDragged ? 4 : 1}
              sx={{
                display: "flex",
                alignItems: "center",
                px: 1.5,
                py: 1,
                cursor: "grab",
                opacity: isDragged ? 0.5 : 1,
                border: isDragOver ? "2px solid #1976d2" : "1px solid #e0e0e0",
                borderRadius: 1,
                backgroundColor: isDragged ? "#e3f2fd" : "#ffffff",
                transition: "box-shadow 0.2s, opacity 0.2s",
                "&:hover": {
                  boxShadow: 2,
                },
                "&:active": {
                  cursor: "grabbing",
                },
              }}
            >
              {/* Drag handle */}
              <Tooltip title="Drag to reorder">
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    color: "text.secondary",
                    mr: 1,
                  }}
                >
                  <DragIndicatorIcon fontSize="small" />
                </Box>
              </Tooltip>

              {/* Section label */}
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography
                  variant="body2"
                  fontWeight={500}
                  noWrap
                >
                  {section.label}
                </Typography>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  noWrap
                >
                  {section.type}
                </Typography>
              </Box>

              {/* Action buttons */}
              <Box sx={{ display: "flex", gap: 0.5, ml: 1 }}>
                <Tooltip title="Duplicate section">
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDuplicate(section.id)
                    }}
                    sx={{
                      color: "text.secondary",
                      "&:hover": {
                        color: "#1976d2",
                        backgroundColor: "#e3f2fd",
                      },
                    }}
                  >
                    <ContentCopyIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Delete section">
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDelete(section.id)
                    }}
                    sx={{
                      color: "text.secondary",
                      "&:hover": {
                        color: "#d32f2f",
                        backgroundColor: "#ffebee",
                      },
                    }}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
            </Paper>

            {/* Drop indicator line below */}
            {showDropIndicator && draggedIndex !== null && draggedIndex < index && (
              <Box
                sx={{
                  height: 3,
                  backgroundColor: "#1976d2",
                  borderRadius: 1,
                  mt: 0.5,
                }}
              />
            )}
          </Box>
        )
      })}

      {/* Add section button at the bottom */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          pt: 1,
        }}
      >
        <Tooltip title="Add a new section">
          <IconButton
            onClick={onAddSection}
            sx={{
              border: "2px dashed #bdbdbd",
              borderRadius: 1,
              width: "100%",
              py: 1,
              color: "text.secondary",
              "&:hover": {
                borderColor: "#1976d2",
                color: "#1976d2",
                backgroundColor: "#e3f2fd",
              },
            }}
          >
            <AddIcon />
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  )
}

export default DragDropSectionEditor
