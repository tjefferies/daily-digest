import type { Digest, DigestSection, SectionType } from '../types'

/** Visual config per section type: colors, icons, and emphasis. */
const SECTION_STYLES: Record<
  SectionType,
  { bg: string; border: string; text: string; icon: string }
> = {
  requires_action: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-800',
    icon: '\u26A0\uFE0F',
  },
  decisions_changes: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-800',
    icon: '\u2699\uFE0F',
  },
  progress_risks: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-800',
    icon: '\uD83D\uDCC8',
  },
  broader_context: {
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    text: 'text-gray-600',
    icon: '\uD83D\uDD0D',
  },
}

function SectionCard({ section }: { section: DigestSection }) {
  const style = SECTION_STYLES[section.section_type]
  return (
    <div className={`rounded-lg border ${style.border} ${style.bg} p-4`}>
      <h2
        className={`text-sm font-semibold uppercase tracking-wide ${style.text} mb-3`}
      >
        {style.icon} {section.title}
      </h2>
      {(!section.items || section.items.length === 0) ? (
        <p className="text-sm text-gray-400 italic">No items in this section.</p>
      ) : (
        <ul className="space-y-3">
          {section.items.map((item) => (
            <li key={item.atom_id} className="bg-white rounded-md p-3 shadow-sm">
              <p className="font-medium text-sm text-gray-900">
                {item.headline}
              </p>
              <p className="text-sm text-gray-600 mt-1">{item.context}</p>
              <span className="inline-block mt-1.5 text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                {item.source_channel}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="bg-white rounded-lg border border-gray-200 p-4 space-y-3"
        >
          <div className="h-4 bg-gray-200 rounded w-48" />
          <div className="h-3 bg-gray-100 rounded w-full" />
          <div className="h-3 bg-gray-100 rounded w-3/4" />
        </div>
      ))}
    </div>
  )
}

interface DigestDisplayProps {
  digest: Digest | null
  loading: boolean
  error: string | null
  personaName: string
}

export default function DigestDisplay({
  digest,
  loading,
  error,
  personaName,
}: DigestDisplayProps) {
  if (loading) {
    return <LoadingSkeleton />
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4 text-red-700 text-sm">
        {error}
      </div>
    )
  }

  if (!digest) {
    return null
  }

  return (
    <div className="space-y-4">
      <div className="flex items-baseline gap-2">
        <p className="text-sm text-gray-500">
          Digest for{' '}
          <span className="font-medium text-gray-700">{personaName}</span>
        </p>
        {digest.generated_at && (
          <span className="text-xs text-gray-400">
            {new Date(digest.generated_at).toLocaleString()}
          </span>
        )}
      </div>

      {digest.sections.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
          <p className="text-gray-400 italic">
            No digest sections available. Run the pipeline to generate content.
          </p>
        </div>
      ) : (
        digest.sections.map((section) => (
          <SectionCard key={section.section_type} section={section} />
        ))
      )}
    </div>
  )
}
