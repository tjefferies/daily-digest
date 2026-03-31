import { useState } from 'react'
import { runPipeline } from '../api/client'

const STAGES = [
  'Ingesting messages...',
  'Extracting atoms...',
  'Scoring relevance...',
  'Generating digests...',
]

interface PipelineRunnerProps {
  onComplete: () => void
}

export default function PipelineRunner({ onComplete }: PipelineRunnerProps) {
  const [running, setRunning] = useState(false)
  const [stageIndex, setStageIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const handleRun = async () => {
    setRunning(true)
    setError(null)
    setStageIndex(0)

    // Simulate stage progression while API call runs
    const interval = setInterval(() => {
      setStageIndex((prev) => Math.min(prev + 1, STAGES.length - 1))
    }, 800)

    try {
      await runPipeline()
      clearInterval(interval)
      setStageIndex(STAGES.length - 1)
      // Brief delay to show completion before refreshing
      setTimeout(() => {
        setRunning(false)
        onComplete()
      }, 500)
    } catch (err) {
      clearInterval(interval)
      setRunning(false)
      setError(err instanceof Error ? err.message : 'Pipeline failed')
    }
  }

  const progress = ((stageIndex + 1) / STAGES.length) * 100

  return (
    <div className="space-y-2">
      <button
        onClick={handleRun}
        disabled={running}
        className={`
          text-sm px-3 py-1.5 rounded-md transition-colors
          ${
            running
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-emerald-600 text-white hover:bg-emerald-700'
          }
        `}
      >
        {running ? 'Running...' : 'Re-run Pipeline'}
      </button>

      {running && (
        <div className="space-y-1">
          <div className="w-full bg-gray-200 rounded-full h-1.5">
            <div
              className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-500">{STAGES[stageIndex]}</p>
        </div>
      )}

      {error && (
        <p className="text-xs text-red-600">{error}</p>
      )}
    </div>
  )
}
