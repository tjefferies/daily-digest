interface DateSelectorProps {
  dates: string[]
  selectedDate: string | null
  onSelect: (date: string | null) => void
}

export default function DateSelector({
  dates,
  selectedDate,
  onSelect,
}: DateSelectorProps) {
  if (dates.length === 0) return null

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
        {dates.map((d) => (
          <option key={d} value={d}>
            {d}
          </option>
        ))}
      </select>
    </div>
  )
}
