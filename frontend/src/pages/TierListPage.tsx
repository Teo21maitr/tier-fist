import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import { useRefreshTierList, useTierList } from '../api/queries'
import { ItemsPanel } from '../features/items/ItemsPanel'
import { QuestionsPanel } from '../features/questions/QuestionsPanel'
import { RanksPanel } from '../features/tier-lists/RanksPanel'
import { ParticipantsPanel } from '../features/tier-lists/ParticipantsPanel'
import { LaurentBubble } from '../components/LaurentBubble'
import { ErrorNote, Modal, Spinner, SuccessNote } from '../components/ui'
import { NotFoundPage } from './ErrorPages'
import type { TierList } from '../types'

type Tab = 'items' | 'questions' | 'ranks' | 'participants'

export function TierListPage() {
  const { id } = useParams()
  const tierListId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const refresh = useRefreshTierList(tierListId)
  const { data: tierList, isLoading, error } = useTierList(tierListId, { poll: true })

  const [tab, setTab] = useState<Tab>('items')
  const [confirmFinalize, setConfirmFinalize] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [codeCopied, setCodeCopied] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const finalize = useMutation({
    mutationFn: () => api.post(`/api/tier-lists/${tierListId}/finalize`),
    onSuccess: () => {
      refresh()
      setConfirmFinalize(false)
      navigate(`/tier-lists/${tierListId}/questionnaire`)
    },
    onError: (caught) =>
      setActionError(caught instanceof ApiError ? caught.message : 'Finalisation impossible.'),
  })

  const duplicate = useMutation({
    mutationFn: () => api.post<TierList>(`/api/tier-lists/${tierListId}/duplicate`),
    onSuccess: (copy) => {
      queryClient.invalidateQueries({ queryKey: ['tier-lists'] })
      navigate(`/tier-lists/${copy.id}`)
    },
  })

  const remove = useMutation({
    mutationFn: () => api.delete(`/api/tier-lists/${tierListId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tier-lists'] })
      navigate('/mes-tier-lists')
    },
  })

  if (isLoading) return <Spinner label="Chargement de la Tier List…" />
  if (error instanceof ApiError && error.status === 404) return <NotFoundPage />
  if (!tierList) return <ErrorNote>Impossible de charger cette Tier List.</ErrorNote>

  const isDraft = tierList.status === 'DRAFT'

  const tabs: Array<[Tab, string]> = [
    ['items', `Items (${tierList.items_count})`],
    ['questions', `Questions (${tierList.questions_count}/6)`],
    ['ranks', 'Rangs'],
    ['participants', `Participants (${tierList.participants_count})`],
  ]

  return (
    <div className="space-y-6">
      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="font-display text-3xl font-black">{tierList.name}</h1>
            <p className="text-slate-500">Thème : {tierList.theme}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {!isDraft && (
              <Link
                to={
                  tierList.status === 'ANSWERING'
                    ? `/tier-lists/${tierList.id}/questionnaire`
                    : `/tier-lists/${tierList.id}/resultat`
                }
                className="btn-primary"
              >
                {tierList.status === 'ANSWERING' ? 'Aller au questionnaire' : 'Voir le résultat'}
              </Link>
            )}
            <button
              type="button"
              className="btn-secondary"
              onClick={() => duplicate.mutate()}
              disabled={duplicate.isPending}
            >
              Dupliquer
            </button>
            {tierList.is_creator && (
              <button type="button" className="btn-danger" onClick={() => setConfirmDelete(true)}>
                Supprimer
              </button>
            )}
          </div>
        </div>

        {isDraft && (
          <div className="card flex flex-wrap items-center gap-4">
            <div>
              <p className="text-sm text-slate-500">Code d'invitation</p>
              <p className="font-mono text-3xl font-black tracking-[0.3em]">
                {tierList.invite_code}
              </p>
            </div>
            <button
              type="button"
              className="btn-secondary"
              onClick={async () => {
                await navigator.clipboard.writeText(tierList.invite_code)
                setCodeCopied(true)
                window.setTimeout(() => setCodeCopied(false), 2500)
              }}
            >
              {codeCopied ? 'Copié !' : 'Copier le code'}
            </button>
            <p className="flex-1 text-sm italic text-slate-500">
              « Partage ce code uniquement avec les gens dont tu es prêt à subir les opinions. »
            </p>
          </div>
        )}
      </header>

      {actionError && <ErrorNote>{actionError}</ErrorNote>}

      {isDraft && tierList.is_creator && (
        <div className="card space-y-3">
          {tierList.can_finalize ? (
            <>
              <LaurentBubble mood="happy">
                Tout est en ordre. Tu peux lancer les hostilités quand tu veux.
              </LaurentBubble>
              <button
                type="button"
                className="btn-primary w-full sm:w-auto"
                onClick={() => setConfirmFinalize(true)}
              >
                Finaliser la Tier List
              </button>
            </>
          ) : (
            <>
              <LaurentBubble tone="warning" mood="smug">
                On ne finalise rien tant que les six questions et leurs coefficients ne sont pas
                impeccables.
              </LaurentBubble>
              <ul className="list-inside list-disc space-y-1 text-sm text-slate-600 dark:text-slate-300">
                {tierList.finalization_blockers.map((blocker) => (
                  <li key={blocker}>{blocker}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {isDraft && !tierList.is_creator && (
        <SuccessNote>
          Tu peux ajouter des items et des questions. Seul {tierList.creator.username} peut
          finaliser.
        </SuccessNote>
      )}

      {!isDraft && (
        <LaurentBubble mood="neutral">
          Très bien. Maintenant, plus personne ne touche aux règles. Place au jugement.
        </LaurentBubble>
      )}

      <nav aria-label="Sections de la Tier List" className="flex flex-wrap gap-1 border-b border-slate-200 dark:border-slate-800">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            aria-current={tab === key ? 'page' : undefined}
            className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-semibold transition ${
              tab === key
                ? 'border-brand-500 text-brand-600 dark:text-brand-300'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === 'items' && <ItemsPanel tierList={tierList} />}
      {tab === 'questions' && <QuestionsPanel tierList={tierList} />}
      {tab === 'ranks' && <RanksPanel tierList={tierList} />}
      {tab === 'participants' && <ParticipantsPanel tierList={tierList} />}

      <Modal
        open={confirmFinalize}
        onClose={() => setConfirmFinalize(false)}
        title="Finaliser la Tier List ?"
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setConfirmFinalize(false)}>
              Annuler
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => finalize.mutate()}
              disabled={finalize.isPending}
            >
              {finalize.isPending ? 'Finalisation…' : 'Oui, finaliser'}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <LaurentBubble mood="smug">
            Très bien. Maintenant, plus personne ne touche aux règles. Place au jugement.
          </LaurentBubble>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Après finalisation, plus personne ne peut rejoindre, et les items, les questions, les
            coefficients et les noms de rang sont définitivement figés.
          </p>
        </div>
      </Modal>

      <Modal
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Supprimer cette Tier List ?"
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setConfirmDelete(false)}>
              Annuler
            </button>
            <button
              type="button"
              className="btn-danger"
              onClick={() => remove.mutate()}
              disabled={remove.isPending}
            >
              {remove.isPending ? 'Suppression…' : 'Supprimer définitivement'}
            </button>
          </>
        }
      >
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Tout disparaît : items, questions, réponses, classement et jokers. C'est irréversible.
        </p>
      </Modal>
    </div>
  )
}
