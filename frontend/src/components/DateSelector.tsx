interface DateSelectorProps {
  selectedDate: string | null
  onSelect: (date: string | null) => void
}

const DATE_OPTIONS = [
  { value: '2026-04-02', label: '2026-04-02 (demo)' },
  { value: '2026-04-01', label: '2026-04-01' },
  { value: '2026-03-31', label: '2026-03-31' },
  { value: '2026-03-30', label: '2026-03-30' },
  { value: '2026-03-29', label: '2026-03-29' },
  { value: '2026-03-28', label: '2026-03-28' },
]

export default function DateSelector({
  selectedDate,
  onSelect,
}: DateSelectorProps) {
  return (
    <div className="flex items-center gap-2">
      <label
        htmlFor="date-filter"
        className="text-xs font-medium text-gray-500 uppercase tracking-wide"
      >
        Filter by date
      </label>
      <select
        id="date-filter"
        value={selectedDate ?? ''}
        onChange={(e) => onSelect(e.target.value || null)}
        className="text-sm border border-gray-300 rounded-md px-2 py-1 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
      >
        {DATE_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}
