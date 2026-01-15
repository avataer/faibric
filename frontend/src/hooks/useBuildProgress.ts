import { useState, useEffect, useRef } from 'react'

interface UseBuildProgressParams {
  targetProgress: number
  isBuilding: boolean
}

interface UseBuildProgressReturn {
  buildProgress: number
}

export function useBuildProgress({ targetProgress, isBuilding }: UseBuildProgressParams): UseBuildProgressReturn {
  const [buildProgress, setBuildProgress] = useState(0)
  const lastProgressUpdate = useRef<number>(Date.now())

  // Reset progress when starting a new build
  useEffect(() => {
    if (isBuilding && targetProgress < 10) {
      setBuildProgress(0)
    }
  }, [isBuilding, targetProgress])

  // Smooth progress animation - gradually approach target
  useEffect(() => {
    const animateProgress = () => {
      const now = Date.now()
      const timeSinceLastUpdate = now - lastProgressUpdate.current

      // Only update every 200ms for smoother animation
      if (timeSinceLastUpdate < 200) return

      setBuildProgress(prev => {
        if (prev >= targetProgress) return prev

        // SLOW increment: max 2% per update, slower as we get closer to target
        const diff = targetProgress - prev
        const increment = Math.min(2, Math.max(0.5, diff * 0.1))
        const newProgress = Math.min(targetProgress, prev + increment)

        lastProgressUpdate.current = now
        return Math.round(newProgress * 10) / 10 // Round to 1 decimal
      })
    }

    // Animate continuously while building
    if (isBuilding && buildProgress < targetProgress) {
      const timer = setInterval(animateProgress, 200)
      return () => clearInterval(timer)
    }
  }, [buildProgress, targetProgress, isBuilding])

  return { buildProgress }
}
