import { useCallback, useEffect, useRef, useState } from 'react'
import {
  getPipelineStatus,
  runPipeline,
  type PipelineStatus,
} from '../api/client'

const POLL_INTERVAL_MS = 2000

const STAGE_LABELS: Record<string, string> = {
  extraction_stage1: 'Stage 1: Coarse Extraction',
  extraction_stage2: 'Stage 2: Enrichment',
  generating_digests: 'Generating Digests',
  done: 'Complete',
}

interface PipelineRunnerProps {
  onComplete: () => void
}

export default function PipelineRunner({ onComplete }: PipelineRunnerProps) {
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const poll = useCallback(async () => {
    try {
      const s = await getPipelineStatus()
      setStatus(s)

      if (s.state === 'complete') {
        stopPolling()
        onComplete()
      } else if (s.state === 'failed') {
        stopPolling()
        setError(s.error ?? 'Pipeline failed')
      }
    } catch {
      // Silently retry on network errors during polling
    }
  }, [stopPolling, onComplete])

  const startPolling = useCallback(() => {
    stopPolling()
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS)
    // Immediate first poll
    poll()
  }, [poll, stopPolling])

  // Check status on mount — resume polling if already running
  useEffect(() => {
    const checkInitial = async () => {
      try {
        const s = await getPipelineStatus()
        setStatus(s)
        if (s.state === 'running') {
          startPolling()
        }
      } catch {
        // Backend not ready yet
      }
    }
    checkInitial()
    return stopPolling
  }, [startPolling, stopPolling])

  const handleRun = async () => {
    setStarting(true)
    setError(null)
    try {
      const result = await runPipeline()
      if (result.status === 'already_running') {
        // Just start polling
      }
      startPolling()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start pipeline')
    } finally {
      setStarting(false)
    }
  }

  const isRunning = status?.state === 'running'
  const isComplete = status?.state === 'complete'
  const progress = status?.progress
  const stage = status?.stage ?? ''
  const stageLabel = STAGE_LABELS[stage] ?? stage

  const progressPct =
    progress && progress.total > 0
      ? Math.round((progress.succeeded / progress.total) * 100)
      : 0

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <button
          onClick={handleRun}
          disabled={isRunning || starting}
          className={`
            text-sm px-3 py-1.5 rounded-md transition-colors
            ${
              isRunning || starting
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-emerald-600 text-white hover:bg-emerald-700'
            }
          `}
        >
          {starting ? 'Starting...' : isRunning ? 'Running...' : 'Run Pipeline'}
        </button>

        {isComplete && (
          <span className="text-xs text-emerald-600 font-medium">
            ✓ Pipeline complete
            {status?.stats?.atoms_after_filter != null &&
              ` — ${status.stats.atoms_after_filter} atoms`}
          </span>
        )}
      </div>

      {isRunning && progress && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{stageLabel}</span>
            <span>
              {progress.succeeded}/{progress.total}
              {progress.errored > 0 && (
                <span className="text-red-500 ml-1">
                  ({progress.errored} errored)
                </span>
              )}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          {status?.batch_id && (
            <p className="text-[10px] text-gray-400 font-mono">
              batch: {status.batch_id}
            </p>
          )}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md px-3 py-2">
          <p className="text-xs text-red-700">{error}</p>
        </div>
      )}
    </div>
  )
}
