import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import { useAnswering, useRefreshTierList } from '../api/queries'
import { AnswerScale } from '../features/answering/AnswerScale'
import { LaurentBubble } from '../components/LaurentBubble'
import { Avatar, ErrorNote, ItemImage, ProgressBar, Spinner } from '../components/ui'
import { NotFoundPage } from './ErrorPages'
import type { AnsweringItem, AnsweringPayload } from '../types'

export function AnsweringPage() {
  const { id } = useParams()
  const tierListId = Number(id)
  const navigate = useNavigate()
  const refresh = useRefreshTierList(tierListId)

  const { data, isLoading, error } = useAnswering(tierListId, { poll: true })

  // Dès que tout le monde a terminé, la partie bascule en phase joker.
  useEffect(() => {
    if (data && data.tier_list.status !== 'ANSWERING') {
      navigate(`/tier-lists/${tierListId}/resultat`, { replace: true })
    }
  }, [data, navigate, tierListId])

  if (isLoading) return <Spinner label="Je prépare tes questions…" />
  if (error instanceof ApiError && error.status === 404) return <NotFoundPage />
  if (error) return <ErrorNote>{(error as ApiError).message}</ErrorNote>
  if (!data) return null

  const currentItem = data.items.find((item) => !item.is_validated)

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <Link to={`/tier-lists/${tierListId}`} className="text-sm text-brand-500 hover:underline">
          ← {data.tier_list.name}
        </Link>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="font-display text-2xl font-bold">Questionnaire</h1>
          <p className="text-sm font-medium">
            {data.progress.validated_items} / {data.progress.total_items} items validés —{' '}
            {data.progress.progress_percent} %
          </p>
        </div>
        <ProgressBar percent={data.progress.progress_percent} label="Ta progression" />
      </header>

      {currentItem ? (
        <ItemQuestionnaire
          key={currentItem.id}
          tierListId={tierListId}
          item={currentItem}
          questions={data.questions}
          onValidated={refresh}
        />
      ) : (
        <WaitingForOthers data={data} />
      )}

      <OtherParticipants data={data} />
    </div>
  )
}

function ItemQuestionnaire({
  tierListId,
  item,
  questions,
  onValidated,
}: {
  tierListId: number
  item: AnsweringItem
  questions: AnsweringPayload['questions']
  onValidated: () => void
}) {
  const [answers, setAnswers] = useState<Record<string, number>>(item.answers)
  const [error, setError] = useState<string | null>(null)
  const [savingCount, setSavingCount] = useState(0)

  // Autosave : chaque changement part immédiatement au serveur (spec §20).
  const saveAnswer = useMutation({
    mutationFn: ({ questionId, value }: { questionId: number; value: number }) =>
      api.put(`/api/tier-lists/${tierListId}/items/${item.id}/answers/${questionId}`, { value }),
    onMutate: () => setSavingCount((count) => count + 1),
    onSettled: () => setSavingCount((count) => Math.max(0, count - 1)),
    onError: (caught) =>
      setError(caught instanceof ApiError ? caught.message : 'Sauvegarde impossible.'),
  })

  const validate = useMutation({
    mutationFn: () => api.post(`/api/tier-lists/${tierListId}/items/${item.id}/validate`),
    onSuccess: onValidated,
    onError: (caught) =>
      setError(caught instanceof ApiError ? caught.message : 'Validation impossible.'),
  })

  const answeredCount = useMemo(
    () => questions.filter((question) => answers[String(question.id)] !== undefined).length,
    [answers, questions],
  )
  const complete = answeredCount === questions.length

  return (
    <div className="card space-y-6">
      <div className="flex items-center gap-4">
        <ItemImage
          name={item.name}
          url={item.image_url}
          className="h-20 w-20 shrink-0 rounded-2xl sm:h-24 sm:w-24"
        />
        <div>
          <h2 className="font-display text-2xl font-black">{item.name}</h2>
          <p className="text-sm text-slate-500">
            {answeredCount} / {questions.length} réponses
            {savingCount > 0 && <span className="ml-2 text-brand-500">enregistrement…</span>}
          </p>
        </div>
      </div>

      <LaurentBubble variant="compact" mood="neutral">
        Réponds franchement. Les autres ne verront rien avant la fin.
      </LaurentBubble>

      {error && <ErrorNote>{error}</ErrorNote>}

      <div className="space-y-6">
        {questions.map((question) => (
          <AnswerScale
            key={question.id}
            questionId={question.id}
            questionText={question.text}
            value={answers[String(question.id)]}
            onChange={(value) => {
              setAnswers((current) => ({ ...current, [String(question.id)]: value }))
              setError(null)
              saveAnswer.mutate({ questionId: question.id, value })
            }}
          />
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3 border-t border-slate-200 pt-4 dark:border-slate-800">
        <button
          type="button"
          className="btn-primary"
          disabled={!complete || validate.isPending || savingCount > 0}
          onClick={() => validate.mutate()}
        >
          {validate.isPending ? 'Validation…' : `Valider ${item.name}`}
        </button>
        <p className="text-xs text-slate-500">
          {complete
            ? 'Une fois validé, cet item est verrouillé : plus aucune modification possible.'
            : 'Réponds aux six questions pour pouvoir valider.'}
        </p>
      </div>
    </div>
  )
}

function WaitingForOthers({ data }: { data: AnsweringPayload }) {
  const remaining = data.participants.filter((participant) => !participant.has_finished)

  return (
    <div className="card space-y-4">
      <LaurentBubble mood="smug">
        {remaining.length === 0
          ? 'Tu as fini. Admire maintenant la lenteur des autres.'
          : 'Tout le monde n’a pas terminé. Je pourrais inventer leurs réponses, mais apparemment ce serait « malhonnête ».'}
      </LaurentBubble>

      <div>
        <h2 className="font-display text-xl font-bold">Tu as terminé !</h2>
        <p className="mt-1 text-sm text-slate-500">
          {remaining.length === 0
            ? 'Le classement arrive.'
            : `En attente de ${remaining.map((participant) => participant.user.username).join(', ')}.`}
        </p>
      </div>
    </div>
  )
}

/** Avancement des autres : pourcentage et statut uniquement (spec §22). */
function OtherParticipants({ data }: { data: AnsweringPayload }) {
  return (
    <section className="space-y-3">
      <h2 className="font-display text-lg font-bold">Avancement des joueurs</h2>
      <ul className="space-y-2">
        {data.participants.map((participant) => (
          <li
            key={participant.id}
            className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"
          >
            <Avatar user={participant.user} size="sm" />
            <span className="w-24 shrink-0 truncate text-sm font-medium">
              {participant.user.username}
            </span>
            <div className="flex-1">
              <ProgressBar
                percent={participant.progress_percent}
                label={`Progression de ${participant.user.username}`}
              />
            </div>
            <span className="w-20 shrink-0 text-right text-xs text-slate-500">
              {participant.has_finished ? '✅ Terminé' : `${participant.progress_percent} %`}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
