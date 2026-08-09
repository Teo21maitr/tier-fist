import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api, ApiError } from '../../api/client'
import { useRefreshTierList } from '../../api/queries'
import { ErrorNote, RANK_BACKGROUND, RANK_TEXT, SuccessNote } from '../../components/ui'
import type { TierList } from '../../types'

/** Édition des cinq noms de rang (spec §13). Couleurs et ordre non modifiables. */
export function RanksPanel({ tierList }: { tierList: TierList }) {
  const refresh = useRefreshTierList(tierList.id)
  const [names, setNames] = useState(() => tierList.ranks.map((rank) => rank.name))
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setNames(tierList.ranks.map((rank) => rank.name))
  }, [tierList.ranks])

  const save = useMutation({
    mutationFn: () =>
      api.patch(`/api/tier-lists/${tierList.id}`, {
        rank_1_name: names[0],
        rank_2_name: names[1],
        rank_3_name: names[2],
        rank_4_name: names[3],
        rank_5_name: names[4],
      }),
    onSuccess: () => {
      refresh()
      setSaved(true)
      setError(null)
      window.setTimeout(() => setSaved(false), 2500)
    },
    onError: (caught) =>
      setError(caught instanceof ApiError ? caught.message : 'Enregistrement impossible.'),
  })

  const readOnly = tierList.status !== 'DRAFT'
  const unchanged = names.every((name, index) => name === tierList.ranks[index].name)

  return (
    <section className="space-y-4">
      <h2 className="font-display text-xl font-bold">Noms des rangs</h2>
      <p className="text-sm text-slate-500">
        Le rang 1 est toujours le meilleur. L'ordre et les couleurs ne sont pas modifiables.
      </p>

      {error && <ErrorNote>{error}</ErrorNote>}
      {saved && <SuccessNote>Noms de rang enregistrés.</SuccessNote>}

      <form
        className="space-y-3"
        onSubmit={(event) => {
          event.preventDefault()
          save.mutate()
        }}
      >
        {tierList.ranks.map((rank, index) => (
          <div key={rank.number} className="flex items-center gap-3">
            <span
              className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl font-display text-lg font-black ${RANK_BACKGROUND[rank.color]} ${RANK_TEXT[rank.color]}`}
              aria-hidden
            >
              {rank.number}
            </span>
            <label className="sr-only" htmlFor={`rank-${rank.number}`}>
              Nom du rang {rank.number}
            </label>
            <input
              id={`rank-${rank.number}`}
              className="input"
              value={names[index] ?? ''}
              maxLength={30}
              disabled={readOnly}
              onChange={(event) =>
                setNames((current) =>
                  current.map((name, position) => (position === index ? event.target.value : name)),
                )
              }
            />
          </div>
        ))}

        {!readOnly && (
          <button
            type="submit"
            className="btn-primary"
            disabled={save.isPending || unchanged || names.some((name) => !name.trim())}
          >
            {save.isPending ? 'Enregistrement…' : 'Enregistrer les rangs'}
          </button>
        )}
      </form>
    </section>
  )
}
