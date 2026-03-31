import type { Persona } from '../types'

/** The three demo personas matching backend context/personas.py. */
export const DEMO_PERSONAS: Persona[] = [
  {
    user_id: 'U001',
    name: 'Maya Chen',
    role_archetype: 'IC Engineer',
    title: 'Senior Mechanical Engineer',
    workstream_affinities: {
      chassis: 1.0,
      thermal: 0.85,
      drivetrain: 0.4,
    },
    phase_context: { chassis: 'DVT', thermal: 'EVT', drivetrain: 'DVT' },
    scoring_weights: {
      workstream_proximity: 0.3,
      role_type_alignment: 0.2,
      phase_alignment: 0.2,
      urgency: 0.15,
      social_signal: 0.15,
    },
    collaborator_graph: ['U003', 'U008', 'U013', 'U020'],
    digest_preferences: {
      max_items: 25,
      critical_threshold: 0.85,
      include_broader_context: true,
    },
  },
  {
    user_id: 'U007',
    name: 'Elena Vasquez',
    role_archetype: 'Supply Chain',
    title: 'Supply Chain Manager',
    workstream_affinities: {
      'supply-chain': 1.0,
      chassis: 0.5,
      drivetrain: 0.5,
    },
    phase_context: {
      'supply-chain': 'DVT',
      chassis: 'DVT',
      'power-systems': 'DVT',
    },
    scoring_weights: {
      workstream_proximity: 0.3,
      role_type_alignment: 0.2,
      phase_alignment: 0.2,
      urgency: 0.15,
      social_signal: 0.15,
    },
    collaborator_graph: ['U011', 'U013', 'U017', 'U019'],
    digest_preferences: {
      max_items: 25,
      critical_threshold: 0.85,
      include_broader_context: true,
    },
  },
  {
    user_id: 'U010',
    name: 'Ryan Torres',
    role_archetype: 'Eng Manager',
    title: 'Engineering Manager',
    workstream_affinities: {
      chassis: 0.8,
      drivetrain: 0.8,
      thermal: 0.7,
    },
    phase_context: {
      chassis: 'DVT',
      drivetrain: 'DVT',
      thermal: 'EVT',
      'power-systems': 'DVT',
      sensors: 'EVT',
      firmware: 'EVT',
    },
    scoring_weights: {
      workstream_proximity: 0.3,
      role_type_alignment: 0.2,
      phase_alignment: 0.2,
      urgency: 0.15,
      social_signal: 0.15,
    },
    collaborator_graph: ['U001', 'U007', 'U011', 'U019'],
    digest_preferences: {
      max_items: 25,
      critical_threshold: 0.85,
      include_broader_context: true,
    },
  },
]

/** Format the top workstream affinities as a readable subtitle. */
function topWorkstreams(affinities: Record<string, number>, count = 3): string {
  return Object.entries(affinities)
    .sort(([, a], [, b]) => b - a)
    .slice(0, count)
    .map(([ws]) => ws)
    .join(', ')
}

interface PersonaSelectorProps {
  selectedId: string
  onSelect: (personaId: string) => void
}

export default function PersonaSelector({
  selectedId,
  onSelect,
}: PersonaSelectorProps) {
  return (
    <nav className="flex gap-1 border-b border-gray-200 bg-white px-4">
      {DEMO_PERSONAS.map((persona) => {
        const isActive = persona.user_id === selectedId
        return (
          <button
            key={persona.user_id}
            onClick={() => onSelect(persona.user_id)}
            className={`
              px-4 py-3 text-left transition-colors border-b-2
              ${
                isActive
                  ? 'border-blue-600 text-blue-700 bg-blue-50/50'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }
            `}
          >
            <div className="font-medium text-sm">{persona.name}</div>
            <div className="text-xs text-gray-500">{persona.title}</div>
            <div className="text-xs text-gray-400 mt-0.5">
              {topWorkstreams(persona.workstream_affinities)}
            </div>
          </button>
        )
      })}
    </nav>
  )
}
