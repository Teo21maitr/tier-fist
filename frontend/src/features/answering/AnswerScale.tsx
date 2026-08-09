const VALUES = [1, 2, 3, 4, 5, 6, 7, 8, 9]

interface AnswerScaleProps {
  questionId: number
  questionText: string
  value: number | undefined
  disabled?: boolean
  onChange: (value: number) => void
}

/**
 * Échelle de réponse de 1 à 9 (spec §19, §57).
 *
 * Groupe de boutons radio : utilisable au clavier (flèches), zones tactiles
 * confortables sur mobile, et la valeur sélectionnée reste identifiable
 * autrement que par la seule couleur (spec §58).
 */
export function AnswerScale({
  questionId,
  questionText,
  value,
  disabled = false,
  onChange,
}: AnswerScaleProps) {
  return (
    <fieldset className="space-y-2" disabled={disabled}>
      <legend className="text-base font-medium leading-snug">{questionText}</legend>

      <div className="flex items-center justify-between text-xs text-slate-500 sm:hidden">
        <span>Pas du tout d'accord</span>
        <span>Tout à fait d'accord</span>
      </div>

      <div className="flex items-center gap-2">
        <span className="hidden w-32 shrink-0 text-right text-xs text-slate-500 sm:block">
          Pas du tout d'accord
        </span>

        <div role="radiogroup" aria-label={questionText} className="flex flex-1 justify-between gap-1">
          {VALUES.map((candidate) => {
            const selected = value === candidate
            return (
              <label
                key={candidate}
                className={`relative flex h-11 flex-1 cursor-pointer items-center justify-center rounded-xl border text-sm font-bold transition sm:h-12 ${
                  selected
                    ? 'border-brand-500 bg-brand-600 text-white shadow-md ring-2 ring-brand-400'
                    : 'border-slate-300 bg-white text-slate-600 hover:border-brand-400 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300'
                } ${disabled ? 'cursor-not-allowed opacity-60' : ''}`}
              >
                {/* L'input couvre toute la pastille : la zone tactile est
                    celle du bouton visible, pas un carré d'un pixel. */}
                <input
                  type="radio"
                  name={`question-${questionId}`}
                  className="absolute inset-0 h-full w-full cursor-pointer opacity-0 disabled:cursor-not-allowed"
                  value={candidate}
                  checked={selected}
                  disabled={disabled}
                  onChange={() => onChange(candidate)}
                />
                {candidate}
                {selected && (
                  <span className="sr-only"> (sélectionné)</span>
                )}
              </label>
            )
          })}
        </div>

        <span className="hidden w-32 shrink-0 text-xs text-slate-500 sm:block">
          Tout à fait d'accord
        </span>
      </div>
    </fieldset>
  )
}
