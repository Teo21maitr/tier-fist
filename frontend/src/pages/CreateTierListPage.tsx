import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import { LaurentBubble } from '../components/LaurentBubble'
import { ErrorNote } from '../components/ui'
import type { TierList } from '../types'

export function CreateTierListPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [theme, setTheme] = useState('')

  const mutation = useMutation({
    mutationFn: (payload: { name: string; theme: string }) =>
      api.post<TierList>('/api/tier-lists', payload),
    onSuccess: (tierList) => {
      queryClient.invalidateQueries({ queryKey: ['tier-lists'] })
      navigate(`/tier-lists/${tierList.id}`)
    },
  })

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <LaurentBubble variant="hero" mood="smug">
        Donne-moi un sujet. J'essaierai de ne juger personne. Enfin, pas tout de suite.
      </LaurentBubble>

      <form
        className="card space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate({ name, theme })
        }}
      >
        <h1 className="font-display text-2xl font-bold">Créer une Tier List</h1>

        {mutation.isError && (
          <ErrorNote>
            {mutation.error instanceof ApiError
              ? mutation.error.message
              : 'Création impossible.'}
          </ErrorNote>
        )}

        <div>
          <label className="label" htmlFor="name">
            Nom
          </label>
          <input
            id="name"
            className="input"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Meilleurs fast-foods"
            maxLength={120}
            required
          />
        </div>

        <div>
          <label className="label" htmlFor="theme">
            Thème
          </label>
          <input
            id="theme"
            className="input"
            value={theme}
            onChange={(event) => setTheme(event.target.value)}
            placeholder="Fast-food"
            maxLength={120}
            required
          />
        </div>

        <button type="submit" className="btn-primary w-full" disabled={mutation.isPending}>
          {mutation.isPending ? 'Création…' : 'Créer'}
        </button>
      </form>
    </div>
  )
}
