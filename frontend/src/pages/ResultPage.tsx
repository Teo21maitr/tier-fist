import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import { useJokerState, useRefreshTierList } from '../api/queries'
import { TierGrid } from '../components/TierGrid'
import { LaurentBubble } from '../components/LaurentBubble'
import { ItemDetailModal } from '../features/results/ItemDetailModal'
import { Avatar, ErrorNote, Modal, Spinner } from '../components/ui'
import { NotFoundPage } from './ErrorPages'
import type { JokerActionPayload, JokerStatePayload } from '../types'

export function ResultPage() {
  const { id } = useParams()
  const tierListId = Number(id)
  const refresh = useRefreshTierList(tierListId)
  const { data, isLoading, error } = useJokerState(tierListId, { poll: true })

  const [detailItemId, setDetailItemId] = useState<number | null>(null)
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null)
  const [previewRank, setPreviewRank] = useState<number | null>(null)
  const [confirmSkip, setConfirmSkip] = useState(false)
  const [confirmForce, setConfirmForce] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const resetSelection = () => {
    setSelectedItemId(null)
    setPreviewRank(null)
  }

  const onError = (caught: unknown) =>
    setActionError(caught instanceof ApiError ? caught.message : 'Action impossible.')

  const useJoker = useMutation({
    mutationFn: () =>
      api.post(`/api/tier-lists/${tierListId}/joker/use`, {
        item_id: selectedItemId,
        to_rank: previewRank,
      }),
    onSuccess: () => {
      refresh()
      resetSelection()
      setActionError(null)
    },
    onError,
  })

  const skipJoker = useMutation({
    mutationFn: () => api.post(`/api/tier-lists/${tierListId}/joker/skip`),
    onSuccess: () => {
      refresh()
      resetSelection()
      setConfirmSkip(false)
    },
    onError,
  })

  const forceSkip = useMutation({
    mutationFn: () => api.post(`/api/tier-lists/${tierListId}/joker/force-skip`),
    onSuccess: () => {
      refresh()
      setConfirmForce(false)
    },
    onError,
  })

  if (isLoading) return <Spinner label="Je compile les verdicts…" />
  if (error instanceof ApiError && error.status === 404) return <NotFoundPage />
  if (error) return <ErrorNote>{(error as ApiError).message}</ErrorNote>
  if (!data) return null

  const isCompleted = data.status === 'COMPLETED'
  const canPlay = data.is_my_turn && !isCompleted
  const currentRankOfSelected =
    selectedItemId === null
      ? null
      : (data.ranking.ranks.find((rank) => rank.items.some((item) => item.id === selectedItemId))
          ?.number ?? null)

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <Link to={`/tier-lists/${tierListId}`} className="text-sm text-brand-500 hover:underline">
          ← Retour à la Tier List
        </Link>
        <h1 className="font-display text-3xl font-black">
          {isCompleted ? 'Résultat définitif' : 'Résultat — phase joker'}
        </h1>
      </header>

      <LaurentBubble mood={isCompleted ? 'happy' : 'smug'}>
        {isCompleted
          ? 'Verdict définitif. Vous pouvez maintenant débattre pendant trois heures.'
          : canPlay
            ? 'Ton tour. Une seule modification. Fais-en quelque chose d’irresponsable mais légal.'
            : 'Les calculs sont faits. Certains résultats vont probablement vexer quelqu’un.'}
      </LaurentBubble>

      {actionError && <ErrorNote>{actionError}</ErrorNote>}

      <TierGrid
        ranks={data.ranking.ranks}
        lockedItemIds={data.locked_item_ids}
        selectedItemId={selectedItemId}
        previewRank={previewRank}
        draggable={canPlay}
        onMove={(itemId, toRank) => {
          if (!canPlay || data.locked_item_ids.includes(itemId)) return
          setSelectedItemId(itemId)
          setPreviewRank(toRank)
        }}
        onSelectItem={(itemId) => {
          if (canPlay && !data.locked_item_ids.includes(itemId)) {
            setSelectedItemId((current) => (current === itemId ? null : itemId))
            setPreviewRank(null)
          } else {
            setDetailItemId(itemId)
          }
        }}
      />

      {canPlay && (
        <div className="card space-y-4">
          <h2 className="font-display text-xl font-bold">Ton joker</h2>
          <p className="text-sm text-slate-500">
            Sélectionne un item puis choisis son nouveau rang. Sur ordinateur, tu peux aussi le
            faire glisser directement dans la grille. Rien n'est enregistré tant que tu n'as pas
            validé.
          </p>

          {selectedItemId === null ? (
            <p className="text-sm font-medium">1. Choisis un item dans la grille ci-dessus.</p>
          ) : (
            <div className="space-y-3">
              <p className="text-sm font-medium">2. Choisis le rang de destination :</p>
              <div className="flex flex-wrap gap-2">
                {data.ranking.ranks.map((rank) => (
                  <button
                    key={rank.number}
                    type="button"
                    disabled={rank.number === currentRankOfSelected}
                    onClick={() => setPreviewRank(rank.number)}
                    aria-pressed={previewRank === rank.number}
                    className={`btn ${
                      previewRank === rank.number
                        ? 'bg-brand-600 text-white'
                        : 'border border-slate-300 dark:border-slate-700'
                    }`}
                  >
                    {rank.name}
                    {rank.number === currentRankOfSelected && ' (actuel)'}
                  </button>
                ))}
              </div>

              <div className="flex flex-wrap gap-2 border-t border-slate-200 pt-3 dark:border-slate-800">
                <button
                  type="button"
                  className="btn-primary"
                  disabled={previewRank === null || useJoker.isPending}
                  onClick={() => useJoker.mutate()}
                >
                  {useJoker.isPending ? 'Validation…' : 'Valider mon joker'}
                </button>
                <button type="button" className="btn-secondary" onClick={resetSelection}>
                  Annuler
                </button>
              </div>
            </div>
          )}

          <div className="border-t border-slate-200 pt-3 dark:border-slate-800">
            <button type="button" className="btn-ghost" onClick={() => setConfirmSkip(true)}>
              Je n'utilise pas mon joker
            </button>
          </div>
        </div>
      )}

      {!canPlay && !isCompleted && data.current_turn && (
        <div className="card space-y-3">
          <div className="flex items-center gap-3">
            <Avatar user={data.current_turn.user} />
            <p className="text-sm">
              C'est au tour de <b>{data.current_turn.user.username}</b> de jouer son joker.
            </p>
          </div>
          {data.is_creator && (
            <button type="button" className="btn-secondary" onClick={() => setConfirmForce(true)}>
              Forcer le passage du tour
            </button>
          )}
        </div>
      )}

      <JokerOrder data={data} />
      <JokerHistory data={data} />

      {detailItemId !== null && (
        <ItemDetailModal
          tierListId={tierListId}
          itemId={detailItemId}
          onClose={() => setDetailItemId(null)}
        />
      )}

      <Modal
        open={confirmSkip}
        onClose={() => setConfirmSkip(false)}
        title="Renoncer à ton joker ?"
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setConfirmSkip(false)}>
              Non, je réfléchis encore
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => skipJoker.mutate()}
              disabled={skipJoker.isPending}
            >
              Oui, je renonce
            </button>
          </>
        }
      >
        <LaurentBubble mood="smug">
          Aucun joker ? Une confiance touchante envers les mathématiques.
        </LaurentBubble>
      </Modal>

      <Modal
        open={confirmForce}
        onClose={() => setConfirmForce(false)}
        title="Forcer le passage du tour ?"
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setConfirmForce(false)}>
              Annuler
            </button>
            <button
              type="button"
              className="btn-danger"
              onClick={() => forceSkip.mutate()}
              disabled={forceSkip.isPending}
            >
              Oui, forcer
            </button>
          </>
        }
      >
        <p className="text-sm text-slate-600 dark:text-slate-300">
          <b>{data.current_turn?.user.username}</b> perdra définitivement son joker. Continuer ?
        </p>
      </Modal>
    </div>
  )
}

function JokerOrder({ data }: { data: JokerStatePayload }) {
  return (
    <section className="space-y-3">
      <h2 className="font-display text-lg font-bold">Ordre des jokers</h2>
      <p className="text-sm text-slate-500">
        L'ordre est l'inverse de l'ordre de fin du questionnaire : le plus rapide joue en dernier.
      </p>
      <ol className="space-y-2">
        {data.order.map((action) => (
          <li
            key={action.participant_id}
            className={`flex items-center gap-3 rounded-2xl border p-3 ${
              action.participant_id === data.current_turn?.participant_id
                ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/40'
                : 'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900'
            }`}
          >
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-slate-200 text-xs font-bold dark:bg-slate-800">
              {action.joker_order}
            </span>
            <Avatar user={action.user} size="sm" />
            <span className="flex-1 truncate text-sm font-medium">{action.user.username}</span>
            <span className="shrink-0 text-xs text-slate-500">
              {action.status === 'PENDING' &&
              action.participant_id === data.current_turn?.participant_id
                ? '⏳ à son tour'
                : action.status === 'PENDING'
                  ? 'en attente'
                  : action.status_label}
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}

function JokerHistory({ data }: { data: JokerStatePayload }) {
  if (data.history.length === 0) return null

  const rankName = (number: number | null) =>
    data.ranking.ranks.find((rank) => rank.number === number)?.name ?? '?'

  return (
    <section className="space-y-3">
      <h2 className="font-display text-lg font-bold">Historique des jokers</h2>
      <ul className="space-y-2">
        {data.history.map((action) => (
          <li
            key={action.participant_id}
            className="rounded-2xl border border-slate-200 bg-white p-3 text-sm dark:border-slate-800 dark:bg-slate-900"
          >
            {describeAction(action, rankName)}
          </li>
        ))}
      </ul>
    </section>
  )
}

function describeAction(
  action: JokerActionPayload,
  rankName: (number: number | null) => string,
): string {
  switch (action.status) {
    case 'USED':
      return `${action.user.username} a déplacé ${action.item?.name} de ${rankName(
        action.from_rank,
      )} vers ${rankName(action.to_rank)}.`
    case 'SKIPPED':
      return `${action.user.username} a renoncé à son joker.`
    case 'FORCED_SKIP':
      return `${action.forced_by?.username ?? 'Le créateur'} a forcé le passage du tour de ${action.user.username}.`
    default:
      return `${action.user.username} n'a pas encore joué.`
  }
}
