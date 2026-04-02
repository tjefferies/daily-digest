import { useCallback, useEffect, useState } from 'react'
import { getDigest } from './api/client'
import DateSelector from './components/DateSelector'
import DigestDisplay from './components/DigestDisplay'
import PersonaSelector, {
  DEMO_PERSONAS,
} from './components/PersonaSelector'
import PhaseToggle from './components/PhaseToggle'
import type { Digest } from './types'

/** Cache of preloaded digests keyed by persona_id. */
const digestCache: Record<string, Digest> = {}

function App() {
  const [selectedPersona, setSelectedPersona] = useState(
    DEMO_PERSONAS[0].user_id,
  )
  const [digest, setDigest] = useState<Digest | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [phaseOverride, setPhaseOverride] = useState<string | null>(null)
  const [dateFilter, setDateFilter] = useState<string | null>('2026-04-02')
  const [cacheReady, setCacheReady] = useState(false)

  /** Preload digests for all 3 personas on mount. */
  useEffect(() => {
    const preload = async () => {
      setLoading(true)
      try {
        const results = await Promise.allSettled(
          DEMO_PERSONAS.map((p) => getDigest(p.user_id)),
        )
        results.forEach((result, i) => {
          if (result.status === 'fulfilled') {
            digestCache[DEMO_PERSONAS[i].user_id] = result.value
          }
        })
        setCacheReady(true)
        // Show first persona's digest
        const first = digestCache[DEMO_PERSONAS[0].user_id]
        if (first) setDigest(first)
      } catch {
        // Startup preload failed - will fetch on demand
      } finally {
        setLoading(false)
      }
    }
    preload()
  }, [])

  const fetchDigest = useCallback(
    async (personaId: string, override?: string | null, date?: string | null) => {
      // Use cache for default (no override, no date filter) if available
      if (!override && !date && digestCache[personaId]) {
        setDigest(digestCache[personaId])
        return
      }

      setLoading(true)
      setError(null)
      try {
        const data = await getDigest(personaId, override ?? undefined, date ?? undefined)
        setDigest(data)
        // Update cache for default views only
        if (!override && !date) {
          digestCache[personaId] = data
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load digest')
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  const handlePersonaSelect = (personaId: string) => {
    setSelectedPersona(personaId)
    setPhaseOverride(null)
    if (!dateFilter && digestCache[personaId]) {
      setDigest(digestCache[personaId])
    } else {
      fetchDigest(personaId, null, dateFilter)
    }
  }

  const handlePhaseApply = (override: string) => {
    setPhaseOverride(override)
    fetchDigest(selectedPersona, override, dateFilter)
  }

  const handlePhaseClear = () => {
    setPhaseOverride(null)
    fetchDigest(selectedPersona, null, dateFilter)
  }

  const handleDateSelect = (date: string | null) => {
    setDateFilter(date)
    setPhaseOverride(null)
    fetchDigest(selectedPersona, null, date)
  }

  const handlePipelineComplete = () => {
    // Invalidate cache and reload all digests
    Object.keys(digestCache).forEach((k) => delete digestCache[k])
    setCacheReady(false)
    DEMO_PERSONAS.forEach((p) => {
      getDigest(p.user_id).then((data) => {
        digestCache[p.user_id] = data
        if (p.user_id === selectedPersona) {
          setDigest(data)
        }
      })
    })
    setCacheReady(true)
  }

  const currentPersona = DEMO_PERSONAS.find(
    (p) => p.user_id === selectedPersona,
  )

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-xl font-semibold text-gray-900">Daily Digest Tool</h1>
          <p className="text-sm text-gray-500">
            Context-aware daily digest for robotics hardware team.
          </p>
        </div>
      </header>

      <div className="max-w-7xl mx-auto">
        <PersonaSelector
          selectedId={selectedPersona}
          onSelect={handlePersonaSelect}
        />

        <div className="flex items-center gap-4 px-4 pt-2">
          <DateSelector
            selectedDate={dateFilter}
            onSelect={handleDateSelect}
          />
        </div>

        <PhaseToggle
          onApply={handlePhaseApply}
          activeOverride={phaseOverride}
          onClear={handlePhaseClear}
          onPipelineComplete={handlePipelineComplete}
        />
      </div>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <DigestDisplay
          digest={digest}
          loading={loading && !cacheReady}
          error={error}
          personaName={currentPersona?.name ?? selectedPersona}
        />
      </main>
    </div>
  )
}

export default App
