import { useState } from 'react'
import { useItemDetail } from '../../api/queries'
import { Avatar, ItemImage, Modal, Spinner } from '../../components/ui'

/** Détail d'un item : score collectif, moyenne par question, vue individuelle (spec §32). */
export function ItemDetailModal({
  tierListId,
  itemId,
  onClose,
}: {
  tierListId: number
  itemId: number
  onClose: () => void
}) {
  const { data, isLoading } = useItemDetail(tierListId, itemId)
  const [showIndividual, setShowIndividual] = useState(false)

  return (
    <Modal open onClose={onClose} title={data?.item.name ?? 'Détail'}>
      {isLoading && <Spinner />}
      {data && (
        <div className="space-y-5">
          <div className="flex items-center gap-4">
            <ItemImage
              name={data.item.name}
              url={data.item.image_url}
              className="h-24 w-24 shrink-0 rounded-2xl"
            />
            <div>
              <p className="text-sm text-slate-500">Score global</p>
              <p className="font-display text-4xl font-black text-brand-600 dark:text-brand-300">
                {data.global_score ?? '—'}
              </p>
              <p className="text-sm text-slate-500">
                Rang : <span className="font-semibold">{data.rank_name}</span>
                {data.algorithm_rank !== data.current_rank && ' (déplacé par un joker)'}
              </p>
            </div>
          </div>

          <section className="space-y-2">
            <h3 className="font-display text-lg font-bold">Détail par question</h3>
            <ul className="space-y-2">
              {data.questions.map((question) => (
                <li
                  key={question.id}
                  className="rounded-xl border border-slate-200 p-3 dark:border-slate-800"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm">{question.text}</p>
                    <span className="shrink-0 rounded-lg bg-slate-200 px-2 py-0.5 text-xs font-bold dark:bg-slate-800">
                      ×{question.coefficient}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-500">
                    Moyenne : <span className="font-semibold">{question.average ?? '—'}</span>
                  </p>
                </li>
              ))}
            </ul>
          </section>

          <section className="space-y-2">
            <button
              type="button"
              className="btn-secondary w-full"
              onClick={() => setShowIndividual((current) => !current)}
              aria-expanded={showIndividual}
            >
              {showIndividual ? 'Masquer' : 'Afficher'} le détail individuel
            </button>

            {showIndividual && (
              <ul className="space-y-3">
                {data.participants.map((participant) => (
                  <li
                    key={participant.participant_id}
                    className="rounded-xl border border-slate-200 p-3 dark:border-slate-800"
                  >
                    <div className="mb-2 flex items-center gap-2">
                      <Avatar user={participant.user} size="sm" />
                      <span className="text-sm font-semibold">{participant.user.username}</span>
                      <span className="ml-auto text-sm text-slate-500">
                        Score : <b>{participant.score ?? '—'}</b>
                      </span>
                    </div>
                    <ul className="flex flex-wrap gap-2">
                      {data.questions.map((question, index) => (
                        <li
                          key={question.id}
                          className="rounded-lg bg-slate-100 px-2 py-1 text-xs dark:bg-slate-800"
                        >
                          Q{index + 1} :{' '}
                          <b>{participant.answers[String(question.id)] ?? '—'}</b>
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </Modal>
  )
}
