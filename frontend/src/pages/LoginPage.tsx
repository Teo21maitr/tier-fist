import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../features/auth/AuthContext'
import { ApiError } from '../api/client'
import { LaurentBubble } from '../components/LaurentBubble'
import { ErrorNote } from '../components/ui'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setPending(true)
    try {
      await login(username, password)
      const from = (location.state as { from?: string } | null)?.from
      navigate(from ?? '/', { replace: true })
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === 'account_pending') {
        navigate('/compte-en-attente')
        return
      }
      setError(caught instanceof ApiError ? caught.message : 'Connexion impossible.')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <LaurentBubble variant="hero" mood="smug">
        Une Tier List normale ? Trop facile. Ici, je fais les calculs à votre place.
      </LaurentBubble>

      <form onSubmit={onSubmit} className="card space-y-4">
        <h1 className="font-display text-2xl font-bold">Connexion</h1>

        {error && <ErrorNote>{error}</ErrorNote>}

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
            required
          />
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
            autoComplete="current-password"
            required
          />
        </div>

        <button type="submit" className="btn-primary w-full" disabled={pending}>
          {pending ? 'Connexion…' : 'Se connecter'}
        </button>

        <p className="text-center text-sm text-slate-500">
          Pas encore de compte ?{' '}
          <Link to="/inscription" className="font-semibold text-brand-500 hover:underline">
            Créer un compte
          </Link>
        </p>
        <p className="text-center text-xs text-slate-400">
          Mot de passe oublié ? Il n'y a pas d'email ici : demande à un administrateur de le
          réinitialiser.
        </p>
      </form>
    </div>
  )
}
