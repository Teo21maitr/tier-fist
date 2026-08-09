import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import { LaurentBubble } from '../components/LaurentBubble'
import { ErrorNote } from '../components/ui'
import type { TierList } from '../types'

export function JoinPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [code, setCode] = useState('')

  const mutation = useMutation({
    mutationFn: (value: string) =>
      api.post<{ already_member: boolean; tier_list: TierList }>('/api/tier-lists/join', {
        code: value,
      }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['tier-lists'] })
      navigate(`/tier-lists/${result.tier_list.id}`)
    },
  })

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <LaurentBubble variant="hero" mood="neutral">
        Six caractères. Si tu te trompes, je le saurai avant toi.
      </LaurentBubble>

      <form
        className="card space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate(code)
        }}
      >
        <h1 className="font-display text-2xl font-bold">Rejoindre avec un code</h1>

        {mutation.isError && (
          <ErrorNote>
            {mutation.error instanceof ApiError ? mutation.error.message : 'Code invalide.'}
          </ErrorNote>
        )}

        <div>
          <label className="label" htmlFor="code">
            Code d'invitation
          </label>
          <input
            id="code"
            className="input text-center font-mono text-2xl uppercase tracking-[0.4em]"
            value={code}
            onChange={(event) => setCode(event.target.value.toUpperCase())}
            placeholder="A7K4P9"
            maxLength={6}
            autoComplete="off"
            autoCapitalize="characters"
            required
          />
        </div>

        <button
          type="submit"
          className="btn-primary w-full"
          disabled={mutation.isPending || code.length < 6}
        >
          {mutation.isPending ? 'Recherche…' : 'Rejoindre'}
        </button>
      </form>
    </div>
  )
}
