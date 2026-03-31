import { useState } from 'react'
import PipelineRunner from './PipelineRunner'

const WORKSTREAMS = [
  'chassis',
  'drivetrain',
  'thermal',
  'power-systems',
  'sensors',
  'firmware',
  'end-effector',
]

const PHASES = ['Concept', 'EVT', 'DVT', 'PVT', 'MP'] as const

interface PhaseToggleProps {
  onApply: (override: string) => void
  activeOverride: string | null
  onClear: () => void
  onPipelineComplete: () => void
}

export default function PhaseToggle({
  onApply,
  activeOverride,
  onClear,
  onPipelineComplete,
}: PhaseToggleProps) {
  const [collapsed, setCollapsed] = useState(true)
  const [workstream, setWorkstream] = useState(WORKSTREAMS[0])
  const [phase, setPhase] = useState<string>(PHASES[2])

  const handleApply = () => {
    onApply(`${workstream}:${phase}`)
  }

  return (
    <div className="border border-dashed border-gray-300 rounded-lg bg-gray-50/50 mx-4 mt-4">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full px-4 py-2 text-left flex items-center justify-between text-sm text-gray-500 hover:text-gray-700"
      >
        <span className="font-medium">Demo Controls</span>
        <span className="text-xs">{collapsed ? 'Expand' : 'Collapse'}</span>
      </button>

      {!collapsed && (
        <div className="px-4 pb-4 space-y-3">
          <p className="text-xs text-gray-400">
            Override a workstream phase to demonstrate phase-sensitive digest
            changes (Evaluation Criterion 3).
          </p>

          <div className="flex items-end gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Workstream
              </label>
              <select
                value={workstream}
                onChange={(e) => setWorkstream(e.target.value)}
                className="text-sm border border-gray-300 rounded-md px-2 py-1.5 bg-white"
              >
                {WORKSTREAMS.map((ws) => (
                  <option key={ws} value={ws}>
                    {ws}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Phase
              </label>
              <select
                value={phase}
                onChange={(e) => setPhase(e.target.value)}
                className="text-sm border border-gray-300 rounded-md px-2 py-1.5 bg-white"
              >
                {PHASES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleApply}
              className="text-sm bg-blue-600 text-white px-3 py-1.5 rounded-md hover:bg-blue-700 transition-colors"
            >
              Apply Override
            </button>

            {activeOverride && (
              <button
                onClick={onClear}
                className="text-sm text-gray-500 px-3 py-1.5 rounded-md border border-gray-300 hover:bg-gray-100 transition-colors"
              >
                Clear
              </button>
            )}
          </div>

          {activeOverride && (
            <div className="bg-amber-50 border border-amber-200 rounded-md px-3 py-2 text-sm text-amber-800">
              Viewing with override:{' '}
              <span className="font-medium">{activeOverride}</span>
            </div>
          )}

          <div className="border-t border-gray-200 pt-3">
            <PipelineRunner onComplete={onPipelineComplete} />
          </div>
        </div>
      )}
    </div>
  )
}
