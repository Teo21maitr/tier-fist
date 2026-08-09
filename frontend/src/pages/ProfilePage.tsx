import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import { keys } from '../api/queries'
import { useAuth } from '../features/auth/AuthContext'
import { LaurentBubble } from '../components/LaurentBubble'
import { Avatar, ErrorNote, Spinner, SuccessNote } from '../components/ui'
import type { CurrentUser } from '../types'

export function ProfilePage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [username, setUsername] = useState(user?.username ?? '')
  const fileInput = useRef<HTMLInputElement>(null)
  const [profileMessage, setProfileMessage] = useState<string | null>(null)
  const [profileError, setProfileError] = useState<string | null>(null)

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null)
  const [passwordError, setPasswordError] = useState<string | null>(null)

  const updateProfile = useMutation({
    mutationFn: (payload: { username?: string; file?: File | null; removeAvatar?: boolean }) => {
      if (payload.file) {
        const formData = new FormData()
        if (payload.username) formData.append('username', payload.username)
        formData.append('avatar', payload.file)
        return api.patchForm<CurrentUser>('/api/auth/me', formData)
      }
      const body: Record<string, unknown> = {}
      if (payload.username) body.username = payload.username
      if (payload.removeAvatar) body.remove_avatar = true
      return api.patch<CurrentUser>('/api/auth/me', body)
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(keys.me, updated)
      setProfileMessage('Profil mis à jour.')
      setProfileError(null)
      if (fileInput.current) fileInput.current.value = ''
    },
    onError: (caught) => {
      setProfileMessage(null)
      setProfileError(caught instanceof ApiError ? caught.message : 'Mise à jour impossible.')
    },
  })

  const changePassword = useMutation({
    mutationFn: () =>
      api.post('/api/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      }),
    onSuccess: () => {
      setPasswordMessage('Mot de passe mis à jour.')
      setPasswordError(null)
      setCurrentPassword('')
      setNewPassword('')
    },
    onError: (caught) => {
      setPasswordMessage(null)
      setPasswordError(caught instanceof ApiError ? caught.message : 'Changement impossible.')
    },
  })

  if (!user) return <Spinner />

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <LaurentBubble mood="neutral">
        Sans avatar, tu hérites d'une initiale. C'est sobre, mais assumé.
      </LaurentBubble>

      <section className="card space-y-4">
        <h1 className="font-display text-2xl font-bold">Profil</h1>

        {profileError && <ErrorNote>{profileError}</ErrorNote>}
        {profileMessage && <SuccessNote>{profileMessage}</SuccessNote>}

        <div className="flex items-center gap-4">
          <Avatar user={user} size="lg" />
          <div className="flex-1 space-y-2">
            <label className="label" htmlFor="avatar">
              Avatar (facultatif)
            </label>
            <input
              id="avatar"
              ref={fileInput}
              type="file"
              accept="image/*"
              className="block w-full text-sm"
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) updateProfile.mutate({ file })
              }}
            />
            {user.avatar_url && (
              <button
                type="button"
                className="btn-ghost px-2 py-1 text-xs text-rose-600 dark:text-rose-400"
                onClick={() => updateProfile.mutate({ removeAvatar: true })}
              >
                Supprimer l'avatar
              </button>
            )}
          </div>
        </div>

        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault()
            updateProfile.mutate({ username })
          }}
        >
          <div>
            <label className="label" htmlFor="profile-username">
              Pseudo
            </label>
            <input
              id="profile-username"
              className="input"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              minLength={3}
              maxLength={30}
              required
            />
          </div>
          <button
            type="submit"
            className="btn-primary"
            disabled={updateProfile.isPending || username === user.username}
          >
            Enregistrer le pseudo
          </button>
        </form>
      </section>

      <section className="card space-y-3">
        <h2 className="font-display text-xl font-bold">Changer de mot de passe</h2>

        {passwordError && <ErrorNote>{passwordError}</ErrorNote>}
        {passwordMessage && <SuccessNote>{passwordMessage}</SuccessNote>}

        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault()
            changePassword.mutate()
          }}
        >
          <div>
            <label className="label" htmlFor="current-password">
              Mot de passe actuel
            </label>
            <input
              id="current-password"
              type="password"
              className="input"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          <div>
            <label className="label" htmlFor="new-password">
              Nouveau mot de passe
            </label>
            <input
              id="new-password"
              type="password"
              className="input"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              autoComplete="new-password"
              minLength={8}
              required
            />
          </div>
          <button type="submit" className="btn-primary" disabled={changePassword.isPending}>
            Mettre à jour
          </button>
        </form>
      </section>
    </div>
  )
}
