export type AtomType =
  | 'DECISION'
  | 'SPEC_CHANGE'
  | 'ACTION_ITEM'
  | 'BLOCKER'
  | 'RISK'
  | 'TEST_RESULT'
  | 'STATUS_UPDATE'
  | 'QUESTION'

export type Urgency = 'low' | 'medium' | 'high' | 'critical'

export type Phase = 'Concept' | 'EVT' | 'DVT' | 'PVT' | 'Production'

export interface AtomSource {
  channel: string
  thread_ts: string
  message_range: [number, number]
  key_participants: string[]
}

export interface AtomWorkstreams {
  originating: string
  affected: string[]
}

export interface Atom {
  atom_id: string
  type: AtomType
  summary: string
  detail: string
  source: AtomSource
  workstreams: AtomWorkstreams
  urgency: Urgency
  confidence: number
  implicit_decision: boolean
  phase_relevance: Phase[]
}
