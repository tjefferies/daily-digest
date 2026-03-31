import { useCallback, useEffect, useState } from 'react'
import { getDigest } from './api/client'
import PersonaSelector, {
  DEMO_PERSONAS,
} from './components/PersonaSelector'
import type { Digest } from './types'

function App() {
  const [selectedPersona, setSelectedPersona] = useState(
    DEMO_PERSONAS[0].user_id,
  )
  const [digest, setDigest] = useState<Digest | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchDigest = useCallback(async (personaId: string) => {
    setLoading(true)
    setError(null)
    try {
      const data = await getDigest(personaId)
      setDigest(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load digest')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDigest(selectedPersona)
  }, [selectedPersona, fetchDigest])

  const handlePersonaSelect = (personaId: string) => {
    setSelectedPersona(personaId)
  }

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

      <PersonaSelector
        selectedId={selectedPersona}
        onSelect={handlePersonaSelect}
      />

      <main className="max-w-7xl mx-auto px-4 py-8">
        {loading && (
          <p className="text-gray-500 animate-pulse">Loading digest...</p>
        )}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 text-red-700 text-sm">
            {error}
          </div>
        )}
        {!loading && !error && digest && (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              Digest for{' '}
              <span className="font-medium text-gray-700">
                {DEMO_PERSONAS.find((p) => p.user_id === selectedPersona)
                  ?.name ?? selectedPersona}
              </span>
            </p>
            {digest.sections.length === 0 ? (
              <p className="text-gray-400 italic">
                No digest sections available. Run the pipeline to generate
                content.
              </p>
            ) : (
              digest.sections.map((section) => (
                <div
                  key={section.section_type}
                  className="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
                >
                  <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                    {section.title}
                  </h2>
                </div>
              ))
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
