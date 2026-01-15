import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../services/api'
import { BuildStatusResponse, BuildEvent } from '../components/building-studio/types'

interface UseBuildStatusParams {
  sessionToken: string
  onDeployed?: (url: string) => void
  onProgressEvent?: (message: string, eventId: string) => void
  onErrorEvent?: (error: string) => void
}

interface UseBuildStatusReturn {
  isBuilding: boolean
  buildStatus: string
  buildPhase: string
  deploymentUrl: string | null
  targetProgress: number
  stopBuilding: () => Promise<void>
  resetForNewBuild: (mode: 'modify' | 'new') => void
}

export function useBuildStatus({
  sessionToken,
  onDeployed,
  onProgressEvent,
  onErrorEvent,
}: UseBuildStatusParams): UseBuildStatusReturn {
  const [isBuilding, setIsBuilding] = useState(true)
  const [buildStatus, setBuildStatus] = useState<string>('initializing')
  const [buildPhase, setBuildPhase] = useState<string>('Starting...')
  const [deploymentUrl, setDeploymentUrl] = useState<string | null>(null)
  const [targetProgress, setTargetProgress] = useState(3)

  // Track processed events to avoid duplicates
  const processedEventIds = useRef<Set<string>>(new Set())

  // Use refs for callbacks to avoid stale closures
  const onDeployedRef = useRef(onDeployed)
  const onProgressEventRef = useRef(onProgressEvent)
  const onErrorEventRef = useRef(onErrorEvent)

  useEffect(() => { onDeployedRef.current = onDeployed }, [onDeployed])
  useEffect(() => { onProgressEventRef.current = onProgressEvent }, [onProgressEvent])
  useEffect(() => { onErrorEventRef.current = onErrorEvent }, [onErrorEvent])

  // Calculate target progress based on build phase message
  const calculateTargetProgress = useCallback((message: string, currentProgress: number): number => {
    let newTarget = currentProgress

    if (message.includes('VERIFIED') || message.includes('live')) {
      newTarget = Math.max(currentProgress, 95)
    } else if (message.includes('Deploying') || message.includes('deploying')) {
      newTarget = Math.max(currentProgress, 85)
    } else if (message.includes('Assembling') || message.includes('Finalizing')) {
      newTarget = Math.max(currentProgress, 75)
    } else if (message.includes('footer') || message.includes('modal')) {
      newTarget = Math.max(currentProgress, 65)
    } else if (message.includes('form') || message.includes('feature')) {
      newTarget = Math.max(currentProgress, 55)
    } else if (message.includes('chart') || message.includes('stats')) {
      newTarget = Math.max(currentProgress, 45)
    } else if (message.includes('table') || message.includes('list')) {
      newTarget = Math.max(currentProgress, 35)
    } else if (message.includes('navigation') || message.includes('header')) {
      newTarget = Math.max(currentProgress, 25)
    } else if (message.includes('layout')) {
      newTarget = Math.max(currentProgress, 18)
    } else if (message.includes('Building')) {
      newTarget = Math.max(currentProgress, 12)
    } else if (message.includes('Planning')) {
      newTarget = Math.max(currentProgress, 8)
    } else if (message.includes('Analyzing')) {
      newTarget = Math.max(currentProgress, 5)
    } else {
      // Small gradual increase
      newTarget = Math.min(70, currentProgress + 3)
    }

    // LIMIT: Never jump more than 15% at once (except for 100%)
    if (newTarget < 100) {
      return Math.min(newTarget, currentProgress + 15)
    }
    return newTarget
  }, [])

  // Poll for build status
  useEffect(() => {
    if (!sessionToken) return

    // Don't poll if we're deployed and not rebuilding
    if (!isBuilding && deploymentUrl) return

    const pollStatus = async () => {
      try {
        const res = await api.get(`/api/onboarding/status/${sessionToken}/`)
        const data: BuildStatusResponse = res.data

        // Use backend progress if provided
        if (data.build_progress && data.build_progress > 0) {
          setTargetProgress(prev => Math.max(prev, data.build_progress!))
        }
        setBuildStatus(data.status)

        // Handle deployment URL
        if (data.deployment_url && data.deployment_url !== deploymentUrl) {
          setDeploymentUrl(data.deployment_url)
          setIsBuilding(false)
          setTargetProgress(100)
          onDeployedRef.current?.(data.deployment_url)
        }

        // Process build progress events
        if (data.events && data.events.length > 0) {
          const progressEvents = data.events
            .filter((e: BuildEvent) => e.event_type === 'build_progress' && e.event_data?.message)
            .reverse()

          if (progressEvents.length > 0) {
            const latestEvent = progressEvents[progressEvents.length - 1]
            const latestMsg = latestEvent.event_data.message!
            setBuildPhase(latestMsg)

            // Update progress based on phase
            if (data.status === 'deployed') {
              setTargetProgress(100)
            } else {
              setTargetProgress(prev => calculateTargetProgress(latestMsg, prev))
            }

            // Notify parent of new events (with deduplication)
            for (const event of progressEvents) {
              const eventId = event.id || `event-${event.timestamp}`
              if (!processedEventIds.current.has(eventId)) {
                processedEventIds.current.add(eventId)
                onProgressEventRef.current?.(event.event_data.message!, eventId)
              }
            }
          }

          // Process error events
          const errorEvents = data.events.filter((e: BuildEvent) => e.event_type === 'error')
          if (errorEvents.length > 0) {
            const latestError = errorEvents[0]
            const errorId = latestError.id || `error-${latestError.timestamp}`
            if (!processedEventIds.current.has(errorId)) {
              processedEventIds.current.add(errorId)
              onErrorEventRef.current?.(latestError.event_data?.error || 'An error occurred')
            }
          }
        }
      } catch {
        // Status poll failed - will retry on next interval
      }
    }

    pollStatus()
    const interval = setInterval(pollStatus, 2000)
    return () => clearInterval(interval)
  }, [sessionToken, deploymentUrl, isBuilding, calculateTargetProgress])

  const stopBuilding = useCallback(async () => {
    try {
      await api.post(`/api/onboarding/stop/`, { session_token: sessionToken })
      setIsBuilding(false)
    } catch {
      setIsBuilding(false)
      throw new Error('Could not stop build on server')
    }
  }, [sessionToken])

  const resetForNewBuild = useCallback((mode: 'modify' | 'new') => {
    setIsBuilding(true)
    setTargetProgress(mode === 'modify' ? 50 : 5)
    setBuildPhase(mode === 'modify' ? 'Modifying code...' : 'Starting new build...')
    setDeploymentUrl(null)
    processedEventIds.current.clear()
  }, [])

  return {
    isBuilding,
    buildStatus,
    buildPhase,
    deploymentUrl,
    targetProgress,
    stopBuilding,
    resetForNewBuild,
  }
}
