import React, { useState, useEffect, useRef, useCallback } from "react"
import { Box, CircularProgress, Typography } from "@mui/material"
import PropertyPanel from "./PropertyPanel"

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

interface SelectedElement {
  selector: string
  elementType: string
  currentValue: PropertyValue
  newValue?: PropertyValue
}

interface EditAppliedData {
  selector: string
  elementType: string
  newValue: string
  editPrompt?: string
}

interface VisualEditorProps {
  previewUrl: string
  sessionToken: string
  onEditApplied?: (data: EditAppliedData) => void
}

interface MessageData {
  type: string
  selector?: string
  elementType?: string
  currentValue?: string
}

const VisualEditor: React.FC<VisualEditorProps> = ({ previewUrl, sessionToken, onEditApplied }) => {
  const [selectedElement, setSelectedElement] = useState<SelectedElement | null>(null)
  const [isEditing, setIsEditing] = useState<boolean>(false)
  const [showPropertyPanel, setShowPropertyPanel] = useState<boolean>(false)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const iframeRef = useRef<HTMLIFrameElement | null>(null)

  // Handle messages from iframe (element selection)
  useEffect(() => {
    const handleMessage = (event: MessageEvent<MessageData>): void => {
      // Only handle messages from our preview iframe
      if (!previewUrl) return

      const data = event.data
      if (!data || !data.type) return

      if (data.type === "element_hover") {
        handleElementHover(data.selector || "")
      } else if (data.type === "element_click") {
        handleElementClick(data.selector || "", data.elementType || "", data.currentValue || "")
      } else if (data.type === "iframe_ready") {
        setIsLoading(false)
      }
    }

    window.addEventListener("message", handleMessage)
    return () => window.removeEventListener("message", handleMessage)
  }, [previewUrl])

  const handleElementHover = useCallback((selector: string): void => {
    // Send highlight command to iframe
    if (iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        { type: "highlight_element", selector },
        "*"
      )
    }
  }, [])

  const handleElementClick = useCallback((selector: string, elementType: string, currentValue: string): void => {
    // Determine element type if not provided
    let type = elementType
    if (!type) {
      if (selector.includes("button") || selector.includes("btn")) {
        type = "button"
      } else if (selector.includes("img") || selector.includes("image")) {
        type = "image"
      } else {
        type = "text"
      }
    }

    // Parse current value based on element type
    let parsedValue: PropertyValue = {}
    if (type === "text") {
      parsedValue = { text: currentValue || "" }
    } else if (type === "button") {
      parsedValue = { text: currentValue || "" }
    } else if (type === "image") {
      parsedValue = { src: currentValue || "" }
    } else if (type === "style") {
      try {
        parsedValue = currentValue ? JSON.parse(currentValue) : {}
      } catch {
        parsedValue = {}
      }
    }

    setSelectedElement({
      selector,
      elementType: type,
      currentValue: parsedValue,
    })
    setIsEditing(true)
    setShowPropertyPanel(true)
  }, [])

  const handlePropertyChange = useCallback((newValue: PropertyValue): void => {
    if (!selectedElement) return
    setSelectedElement((prev) => {
      if (!prev) return null
      return {
        ...prev,
        newValue,
      }
    })
  }, [selectedElement])

  const applyEdit = useCallback(async (newValue: PropertyValue): Promise<void> => {
    if (!selectedElement || !sessionToken) return

    setError(null)

    // Prepare the new value based on element type
    let formattedNewValue = ""
    if (selectedElement.elementType === "text") {
      formattedNewValue = newValue.text || ""
    } else if (selectedElement.elementType === "button") {
      formattedNewValue = newValue.text || ""
    } else if (selectedElement.elementType === "image") {
      formattedNewValue = newValue.src || ""
    } else if (selectedElement.elementType === "style") {
      formattedNewValue = JSON.stringify(newValue)
    }

    // Get current value for the API
    let currentVal = ""
    if (selectedElement.currentValue) {
      if (selectedElement.elementType === "text" || selectedElement.elementType === "button") {
        currentVal = selectedElement.currentValue.text || ""
      } else if (selectedElement.elementType === "image") {
        currentVal = selectedElement.currentValue.src || ""
      } else if (selectedElement.elementType === "style") {
        currentVal = JSON.stringify(selectedElement.currentValue)
      }
    }

    try {
      const response = await fetch("/api/onboarding/visual-edit/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_token: sessionToken,
          selector: selectedElement.selector,
          element_type: selectedElement.elementType,
          current_value: currentVal,
          new_value: formattedNewValue,
        }),
      })

      const result = await response.json()

      if (result.success) {
        // Close panel and reset state
        setShowPropertyPanel(false)
        setIsEditing(false)
        setSelectedElement(null)

        // Notify parent component
        if (onEditApplied) {
          onEditApplied({
            selector: selectedElement.selector,
            elementType: selectedElement.elementType,
            newValue: formattedNewValue,
            editPrompt: result.edit_prompt,
          })
        }

        // Tell iframe to apply the visual change immediately
        if (iframeRef.current && iframeRef.current.contentWindow) {
          iframeRef.current.contentWindow.postMessage(
            {
              type: "apply_edit",
              selector: selectedElement.selector,
              elementType: selectedElement.elementType,
              newValue: formattedNewValue,
            },
            "*"
          )
        }
      } else {
        setError(result.error || "Failed to apply edit")
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error"
      setError("Network error: " + errorMessage)
    }
  }, [selectedElement, sessionToken, onEditApplied])

  const handleCancel = useCallback((): void => {
    setShowPropertyPanel(false)
    setIsEditing(false)
    setSelectedElement(null)

    // Remove highlight from iframe
    if (iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        { type: "clear_highlight" },
        "*"
      )
    }
  }, [])

  const handleIframeLoad = useCallback((): void => {
    setIsLoading(false)
    // Inject selection script into iframe
    if (iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        { type: "enable_visual_editing" },
        "*"
      )
    }
  }, [])

  return (
    <Box
      sx={{
        position: "relative",
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Preview iframe container */}
      <Box
        sx={{
          flex: 1,
          position: "relative",
          border: isEditing ? "2px solid #1976d2" : "1px solid #e0e0e0",
          borderRadius: 1,
          overflow: "hidden",
          backgroundColor: "#f5f5f5",
        }}
      >
        {isLoading && (
          <Box
            sx={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: "rgba(255, 255, 255, 0.8)",
              zIndex: 10,
            }}
          >
            <CircularProgress />
          </Box>
        )}

        {previewUrl ? (
          <iframe
            ref={iframeRef}
            src={previewUrl}
            onLoad={handleIframeLoad}
            style={{
              width: "100%",
              height: "100%",
              border: "none",
            }}
            title="Preview"
            sandbox="allow-scripts allow-same-origin"
          />
        ) : (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "text.secondary",
            }}
          >
            <Typography>No preview available</Typography>
          </Box>
        )}
      </Box>

      {/* Error display */}
      {error && (
        <Box
          sx={{
            p: 2,
            backgroundColor: "#ffebee",
            color: "#c62828",
            borderRadius: 1,
            mt: 1,
          }}
        >
          <Typography variant="body2">{error}</Typography>
        </Box>
      )}

      {/* Property panel overlay */}
      {showPropertyPanel && selectedElement && (
        <PropertyPanel
          elementType={selectedElement.elementType}
          currentValue={selectedElement.currentValue}
          onApply={applyEdit}
          onCancel={handleCancel}
        />
      )}
    </Box>
  )
}

export default VisualEditor
