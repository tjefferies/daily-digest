import { useCallback, useMemo, useState } from 'react'
import { getSourceThread, type SourceThread } from '../api/client'
import type { Digest, DigestSection, SectionType } from '../types'

/** Format a relative time string like "2 hours, 15 minutes ago". */
function formatRelativeTime(isoTimestamp: string): string {
  const diff = Date.now() - new Date(isoTimestamp).getTime()
  if (diff < 60_000) return 'just now'

  const minutes = Math.floor(diff / 60_000) % 60
  const hours = Math.floor(diff / 3_600_000) % 24
  const days = Math.floor(diff / 86_400_000)

  const parts: string[] = []
  if (days > 0) parts.push(`${days} day${days !== 1 ? 's' : ''}`)
  if (hours > 0) parts.push(`${hours} hour${hours !== 1 ? 's' : ''}`)
  if (minutes > 0) parts.push(`${minutes} minute${minutes !== 1 ? 's' : ''}`)

  return parts.length > 0 ? `${parts.join(', ')} ago` : 'just now'
}

/** Map Slack user_id to display name (from dataset roster). */
const USER_NAMES: Record<string, string> = {
  U001: 'Maya Chen',
  U002: 'Alex Rivera',
  U003: 'Priya Sharma',
  U004: 'James Okafor',
  U005: 'Sarah Kim',
  U006: 'Marcus Johnson',
  U007: 'Elena Vasquez',
  U008: 'David Park',
  U009: 'Aisha Patel',
  U010: 'Ryan Torres',
  U011: 'Lisa Wang',
  U012: 'Carlos Mendez',
  U013: 'Nina Petrov',
  U014: "Kevin O'Brien",
  U015: 'Fatima Al-Hassan',
  U016: 'Tom Nakamura',
  U017: 'Deepa Krishnan',
  U018: 'Michael Zhang',
  U019: 'Rachel Foster',
  U020: 'Jorge Castillo',
}

/** Format a Slack timestamp (epoch seconds) to a readable string. */
function formatSlackTs(ts: string): string {
  const epoch = parseFloat(ts) * 1000
  if (Number.isNaN(epoch)) return ''
  return new Date(epoch).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

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

function SourceModal({
  thread,
  onClose,
}: {
  thread: SourceThread
  onClose: () => void
}) {
  return (
    <div
      className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h3 className="text-sm font-semibold text-gray-900">
            {thread.channel}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-lg"
          >
            &times;
          </button>
        </div>
        <div className="overflow-y-auto p-4 space-y-3">
          {thread.messages.map((msg, i) => (
            <div key={i} className="text-sm">
              <span className="font-medium text-gray-700">
                {USER_NAMES[msg.user_id] ?? msg.user_id}
              </span>
              {msg.ts && (
                <span className="ml-2 text-xs text-gray-400">
                  {formatSlackTs(msg.ts)}
                </span>
              )}
              <p className="text-gray-600 mt-0.5 whitespace-pre-wrap">
                {msg.text}
              </p>
            </div>
          ))}
          {thread.messages.length === 0 && (
            <p className="text-sm text-gray-400 italic">
              No source messages found.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function DigestItem({
  item,
}: {
  item: { headline: string; context: string; source_channel: string; atom_id: string }
}) {
  const [thread, setThread] = useState<SourceThread | null>(null)
  const [loading, setLoading] = useState(false)

  const handleViewSource = useCallback(async () => {
    if (!item.atom_id) return
    setLoading(true)
    try {
      const data = await getSourceThread(item.atom_id)
      setThread(data)
    } catch {
      // silently fail
    } finally {
      setLoading(false)
    }
  }, [item.atom_id])

  return (
    <>
      <li className="bg-white rounded-md p-3 shadow-sm">
        <p className="font-medium text-sm text-gray-900">
          {item.headline}
        </p>
        <p className="text-sm text-gray-600 mt-1">{item.context}</p>
        <div className="flex items-center gap-2 mt-1.5">
          <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
            {item.source_channel}
          </span>
          {item.atom_id && (
            <button
              onClick={handleViewSource}
              disabled={loading}
              className="text-xs text-emerald-600 hover:text-emerald-700 hover:underline cursor-pointer"
            >
              {loading ? 'Loading...' : 'View source'}
            </button>
          )}
        </div>
      </li>
      {thread && (
        <SourceModal thread={thread} onClose={() => setThread(null)} />
      )}
    </>
  )
}

function SectionCard({ section }: { section: DigestSection }) {
  const [expanded, setExpanded] = useState(true)
  const style = SECTION_STYLES[section.section_type]
  const itemCount = section.items?.length ?? 0

  return (
    <div className={`rounded-lg border ${style.border} ${style.bg}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className={`w-full flex items-center justify-between p-4 text-left cursor-pointer`}
      >
        <h2
          className={`text-sm font-semibold uppercase tracking-wide ${style.text}`}
        >
          {style.icon} {section.title}
          {itemCount > 0 && (
            <span className="ml-2 text-xs font-normal opacity-70">
              ({itemCount})
            </span>
          )}
        </h2>
        <span className={`text-sm ${style.text} transition-transform ${expanded ? 'rotate-0' : '-rotate-90'}`}>
          ▼
        </span>
      </button>
      {expanded && (
        <div className="px-4 pb-4">
          {itemCount === 0 ? (
            <p className="text-sm text-gray-400 italic">No items in this section.</p>
          ) : (
            <ul className="space-y-3">
              {section.items.map((item) => (
                <DigestItem key={item.atom_id} item={item} />
              ))}
            </ul>
          )}
        </div>
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

  const relativeTime = useMemo(
    () => (digest?.generated_at ? formatRelativeTime(digest.generated_at) : null),
    [digest?.generated_at],
  )

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
            {relativeTime && (
              <span className="ml-1.5 text-gray-300">({relativeTime})</span>
            )}
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
