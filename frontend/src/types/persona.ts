export type RoleArchetype =
  | 'IC Engineer'
  | 'Eng Manager'
  | 'Program Manager'
  | 'Supply Chain'
  | 'Executive'

export interface ScoringWeights {
  workstream_proximity: number
  role_type_alignment: number
  phase_alignment: number
  urgency: number
  social_signal: number
}

export interface DigestPreferences {
  max_items: number
  critical_threshold: number
  include_broader_context: boolean
}

export interface Persona {
  user_id: string
  name: string
  role_archetype: RoleArchetype
  title: string
  workstream_affinities: Record<string, number>
  phase_context: Record<string, string>
  scoring_weights: ScoringWeights
  collaborator_graph: string[]
  digest_preferences: DigestPreferences
}
