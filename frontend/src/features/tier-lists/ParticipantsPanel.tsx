import { useParticipants } from '../../api/queries'
import { Avatar, ProgressBar, Spinner } from '../../components/ui'
import type { Participant, ParticipantProgress, TierList } from '../../types'

function hasProgress(row: Participant | ParticipantProgress): row is ParticipantProgress {
  return 'progress_percent' in row
}

/**
 * Liste des participants.
 * Pendant ANSWERING, on affiche l'avancement — jamais les réponses (spec §22).
 */
export function ParticipantsPanel({ tierList }: { tierList: TierList }) {
  const showProgress = tierList.status !== 'DRAFT'
  const { data, isLoading } = useParticipants(tierList.id, {
    poll: tierList.status === 'ANSWERING',
  })

  if (isLoading) return <Spinner />

  return (
    <section className="space-y-3">
      <h2 className="font-display text-xl font-bold">
        Participants <span className="text-slate-400">({data?.length ?? 0})</span>
      </h2>

      <ul className="space-y-2">
        {(data ?? []).map((row) => (
          <li
            key={row.id}
            className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"
          >
            <Avatar user={row.user} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">
                {row.user.username}
                {row.is_creator && (
                  <span className="ml-2 rounded-full bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-900/60 dark:text-brand-200">
                    créateur
                  </span>
                )}
              </p>
              {showProgress && hasProgress(row) && (
                <div className="mt-1.5 space-y-1">
                  <ProgressBar
                    percent={row.progress_percent}
                    label={`Progression de ${row.user.username}`}
                  />
                  <p className="text-xs text-slate-500">
                    {row.has_finished
                      ? '✅ Terminé'
                      : `${row.progress_percent} % — ${row.validated_items}/${row.total_items} items`}
                  </p>
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
