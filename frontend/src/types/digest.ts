export type SectionType =
  | 'requires_action'
  | 'decisions_changes'
  | 'progress_risks'
  | 'broader_context'

export interface DigestItem {
  headline: string
  context: string
  source_channel: string
  source_thread_ts: string
  atom_id: string
}

export interface DigestSection {
  section_type: SectionType
  title: string
  items: DigestItem[]
}

export interface Digest {
  persona_id: string
  generated_at: string
  sections: DigestSection[]
}
