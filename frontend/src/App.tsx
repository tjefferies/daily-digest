import { useCallback, useEffect, useState } from 'react'
import { getDigest } from './api/client'
import DigestDisplay from './components/DigestDisplay'
import PersonaSelector, {
  DEMO_PERSONAS,
} from './components/PersonaSelector'
import PhaseToggle from './components/PhaseToggle'
import type { Digest } from './types'

function App() {
  const [selectedPersona, setSelectedPersona] = useState(
    DEMO_PERSONAS[0].user_id,
  )
  const [digest, setDigest] = useState<Digest | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [phaseOverride, setPhaseOverride] = useState<string | null>(null)

  const fetchDigest = useCallback(
    async (personaId: string, override?: string | null) => {
      setLoading(true)
      setError(null)
      try {
        const data = await getDigest(personaId, override ?? undefined)
        setDigest(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load digest')
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  useEffect(() => {
    fetchDigest(selectedPersona, phaseOverride)
  }, [selectedPersona, phaseOverride, fetchDigest])

  const handlePersonaSelect = (personaId: string) => {
    setSelectedPersona(personaId)
    setPhaseOverride(null)
  }

  const handlePhaseApply = (override: string) => {
    setPhaseOverride(override)
  }

  const handlePhaseClear = () => {
    setPhaseOverride(null)
  }

  const currentPersona = DEMO_PERSONAS.find(
    (p) => p.user_id === selectedPersona,
  )

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-xl font-semibold text-gray-900">EverCurrent</h1>
          <p className="text-sm text-gray-500">
            Context-aware daily digest for robotics hardware teams
          </p>
        </div>
      </header>

      <div className="max-w-7xl mx-auto">
        <PersonaSelector
          selectedId={selectedPersona}
          onSelect={handlePersonaSelect}
        />

        <PhaseToggle
          onApply={handlePhaseApply}
          activeOverride={phaseOverride}
          onClear={handlePhaseClear}
        />
      </div>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <DigestDisplay
          digest={digest}
          loading={loading}
          error={error}
          personaName={currentPersona?.name ?? selectedPersona}
        />
      </main>
    </div>
  )
}

export default App
