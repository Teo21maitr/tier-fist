import { useState } from 'react'
import { useTierLists } from '../api/queries'
import { TierListCard } from '../components/TierListCard'
import { EmptyState, ErrorNote, Spinner } from '../components/ui'

const FILTERS = [
  { key: undefined, label: 'Toutes' },
  { key: 'ongoing', label: 'En cours' },
  { key: 'completed', label: 'Terminées' },
] as const

export function MyTierListsPage() {
  const [filter, setFilter] = useState<string | undefined>(undefined)
  const { data, isLoading, isError } = useTierLists(filter)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-bold">Mes Tier Lists</h1>
        <div role="group" aria-label="Filtrer" className="flex gap-1 rounded-xl bg-slate-200 p-1 dark:bg-slate-800">
          {FILTERS.map((option) => (
            <button
              key={option.label}
              type="button"
              onClick={() => setFilter(option.key)}
              aria-pressed={filter === option.key}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                filter === option.key
                  ? 'bg-white shadow-sm dark:bg-slate-950'
                  : 'text-slate-600 dark:text-slate-300'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <Spinner />}
      {isError && <ErrorNote>Impossible de charger tes Tier Lists.</ErrorNote>}
      {data && data.length === 0 && (
        <EmptyState>Rien dans cette catégorie. Laurent s'ennuie ferme.</EmptyState>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {(data ?? []).map((tierList) => (
          <TierListCard key={tierList.id} tierList={tierList} />
        ))}
      </div>
    </div>
  )
}
