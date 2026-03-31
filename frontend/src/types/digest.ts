import type { Atom } from './atom'

export type SectionType =
  | 'requires_action'
  | 'decisions_changes'
  | 'progress_risks'
  | 'broader_context'

export interface DigestSection {
  section_type: SectionType
  title: string
  atoms: Atom[]
}

export interface Digest {
  persona_id: string
  sections: DigestSection[]
}
