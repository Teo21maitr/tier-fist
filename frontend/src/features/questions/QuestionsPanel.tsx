import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api, ApiError } from '../../api/client'
import { useQuestions, useRefreshTierList } from '../../api/queries'
import { LaurentBubble } from '../../components/LaurentBubble'
import { EmptyState, ErrorNote, Modal, Spinner } from '../../components/ui'
import type { Question, TierList } from '../../types'

export function QuestionsPanel({ tierList }: { tierList: TierList }) {
  const { data: questions, isLoading } = useQuestions(tierList.id)
  const refresh = useRefreshTierList(tierList.id)
  const [editing, setEditing] = useState<Question | null>(null)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const remove = useMutation({
    mutationFn: (question: Question) =>
      api.delete(`/api/tier-lists/${tierList.id}/questions/${question.id}`),
    onSuccess: refresh,
    onError: (caught) =>
      setError(caught instanceof ApiError ? caught.message : 'Suppression impossible.'),
  })

  const readOnly = tierList.status !== 'DRAFT'
  const count = questions?.length ?? 0

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-xl font-bold">
          Questions <span className="text-slate-400">({count}/6)</span>
        </h2>
        {!readOnly && count < 6 && (
          <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
            + Ajouter une question
          </button>
        )}
      </div>

      <LaurentBubble variant="compact" mood="smug">
        Six questions. Pas cinq, pas sept. Je sais compter, profitez-en.
      </LaurentBubble>

      {!readOnly && (
        <div className="card space-y-2 py-4">
          <p className="text-sm font-medium">Coefficients à répartir</p>
          <ul className="flex flex-wrap gap-2">
            {tierList.coefficients.map((slot) => (
              <li
                key={slot.coefficient}
                className={`rounded-xl border px-3 py-1.5 text-sm ${
                  slot.remaining === 0
                    ? 'border-slate-300 bg-slate-100 text-slate-400 line-through dark:border-slate-700 dark:bg-slate-800'
                    : 'border-brand-400 bg-brand-50 font-semibold text-brand-800 dark:bg-brand-950/40 dark:text-brand-200'
                }`}
              >
                Coef {slot.coefficient} — {slot.used}/{slot.slots}
              </li>
            ))}
          </ul>
          <p className="text-xs text-slate-500">
            Distribution imposée : 1, 1, 2, 2, 3 et 5. Les questions doivent être des affirmations
            positives : plus la note est élevée, meilleur est l'item.
          </p>
        </div>
      )}

      {error && <ErrorNote>{error}</ErrorNote>}
      {isLoading && <Spinner />}
      {questions && questions.length === 0 && (
        <EmptyState>Aucune question. Difficile de noter quoi que ce soit.</EmptyState>
      )}

      <ul className="space-y-2">
        {(questions ?? []).map((question) => (
          <li
            key={question.id}
            className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
          >
            {question.coefficient !== undefined && (
              <span className="shrink-0 rounded-lg bg-brand-600 px-2.5 py-1 text-xs font-bold text-white">
                ×{question.coefficient}
              </span>
            )}
            <p className="min-w-0 flex-1 text-sm">{question.text}</p>
            {!readOnly && (
              <div className="flex shrink-0 gap-1">
                <button
                  type="button"
                  className="btn-ghost px-2 py-1 text-xs"
                  onClick={() => setEditing(question)}
                >
                  Modifier
                </button>
                <button
                  type="button"
                  className="btn-ghost px-2 py-1 text-xs text-rose-600 dark:text-rose-400"
                  onClick={() => {
                    if (window.confirm('Supprimer cette question ?')) remove.mutate(question)
                  }}
                >
                  Supprimer
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>

      {(creating || editing) && (
        <QuestionDialog
          tierList={tierList}
          question={editing}
          onClose={() => {
            setCreating(false)
            setEditing(null)
          }}
          onSaved={() => {
            refresh()
            setCreating(false)
            setEditing(null)
          }}
        />
      )}
    </section>
  )
}

function QuestionDialog({
  tierList,
  question,
  onClose,
  onSaved,
}: {
  tierList: TierList
  question: Question | null
  onClose: () => void
  onSaved: () => void
}) {
  const [text, setText] = useState(question?.text ?? '')
  const [coefficient, setCoefficient] = useState<number | null>(question?.coefficient ?? null)
  const [error, setError] = useState<string | null>(null)

  // Une question conserve toujours son propre coefficient dans la liste des choix.
  const available = tierList.coefficients.filter(
    (slot) => slot.remaining > 0 || slot.coefficient === question?.coefficient,
  )

  const save = useMutation({
    mutationFn: () => {
      const base = `/api/tier-lists/${tierList.id}/questions`
      const payload = { text, coefficient }
      return question ? api.patch(`${base}/${question.id}`, payload) : api.post(base, payload)
    },
    onSuccess: onSaved,
    onError: (caught) =>
      setError(caught instanceof ApiError ? caught.message : 'Enregistrement impossible.'),
  })

  return (
    <Modal
      open
      onClose={onClose}
      title={question ? 'Modifier la question' : 'Nouvelle question'}
      footer={
        <>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Annuler
          </button>
          <button
            type="submit"
            form="question-form"
            className="btn-primary"
            disabled={save.isPending || !text.trim() || coefficient === null}
          >
            {save.isPending ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </>
      }
    >
      <form
        id="question-form"
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          setError(null)
          save.mutate()
        }}
      >
        {error && <ErrorNote>{error}</ErrorNote>}

        <LaurentBubble variant="compact" mood="neutral">
          Les questions doivent être positives. Si 9 veut dire « très mauvais », mes circuits vont
          porter plainte.
        </LaurentBubble>

        <div>
          <label className="label" htmlFor="question-text">
            Affirmation
          </label>
          <textarea
            id="question-text"
            className="input min-h-[90px]"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Cet item est visuellement réussi."
            maxLength={300}
            required
            autoFocus
          />
        </div>

        <fieldset>
          <legend className="label">Coefficient</legend>
          <div className="flex flex-wrap gap-2">
            {available.map((slot) => (
              <label
                key={slot.coefficient}
                className={`relative cursor-pointer rounded-xl border px-4 py-2 text-sm font-semibold ${
                  coefficient === slot.coefficient
                    ? 'border-brand-500 bg-brand-600 text-white'
                    : 'border-slate-300 dark:border-slate-700'
                }`}
              >
                <input
                  type="radio"
                  name="coefficient"
                  className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                  checked={coefficient === slot.coefficient}
                  onChange={() => setCoefficient(slot.coefficient)}
                />
                ×{slot.coefficient}
              </label>
            ))}
          </div>
          {available.length === 0 && (
            <p className="mt-2 text-sm text-slate-500">
              Tous les coefficients sont pris. Supprime une question pour en libérer un.
            </p>
          )}
        </fieldset>
      </form>
    </Modal>
  )
}
