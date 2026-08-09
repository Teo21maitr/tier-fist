import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../features/auth/AuthContext'
import { ApiError } from '../api/client'
import { LaurentBubble } from '../components/LaurentBubble'
import { ErrorNote } from '../components/ui'

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [pending, setPending] = useState(false)

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setErrors([])
    setPending(true)
    try {
      await register(username, password)
      navigate('/compte-en-attente')
    } catch (caught) {
      if (caught instanceof ApiError) {
        const fieldErrors = caught.errors
          ? Object.values(caught.errors).flat().map(String)
          : [caught.message]
        setErrors(fieldErrors)
      } else {
        setErrors(['Inscription impossible.'])
      }
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <LaurentBubble variant="hero" mood="neutral">
        Un pseudo, un mot de passe. Pas d'email : je n'ai pas l'intention de t'écrire.
      </LaurentBubble>

      <form onSubmit={onSubmit} className="card space-y-4">
        <h1 className="font-display text-2xl font-bold">Créer un compte</h1>

        {errors.length > 0 && (
          <ErrorNote>
            {errors.map((message) => (
              <span key={message} className="block">
                {message}
              </span>
            ))}
          </ErrorNote>
        )}

        <div>
          <label className="label" htmlFor="username">
            Pseudo
          </label>
          <input
            id="username"
            className="input"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            minLength={3}
            maxLength={30}
            required
          />
          <p className="mt-1 text-xs text-slate-500">
            C'est aussi ton pseudo public, visible par les autres joueurs.
          </p>
        </div>

        <div>
          <label className="label" htmlFor="password">
            Mot de passe
          </label>
          <input
            id="password"
            type="password"
            className="input"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
            minLength={8}
            required
          />
        </div>

        <button type="submit" className="btn-primary w-full" disabled={pending}>
          {pending ? 'Création…' : 'Demander un compte'}
        </button>

        <p className="text-center text-sm text-slate-500">
          Déjà un compte ?{' '}
          <Link to="/connexion" className="font-semibold text-brand-500 hover:underline">
            Se connecter
          </Link>
        </p>
      </form>
    </div>
  )
}
