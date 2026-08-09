import { Link } from 'react-router-dom'
import { LaurentBubble } from '../components/LaurentBubble'

export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-lg space-y-6 text-center">
      <LaurentBubble variant="hero" mood="smug">
        Cette Tier List n'existe pas, ou tu n'en fais pas partie. J'ai vérifié deux fois.
      </LaurentBubble>
      <div className="card space-y-3">
        <h1 className="font-display text-3xl font-black">404</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Page introuvable. Les Tier Lists sont privées : seuls leurs participants y accèdent.
        </p>
        <Link to="/" className="btn-primary w-full">
          Retour à l'accueil
        </Link>
      </div>
    </div>
  )
}

export function ForbiddenPage() {
  return (
    <div className="mx-auto max-w-lg space-y-6 text-center">
      <LaurentBubble variant="hero" mood="smug">
        Accès refusé. La patience aussi mérite une note sur 9.
      </LaurentBubble>
      <div className="card space-y-3">
        <h1 className="font-display text-3xl font-black">403</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Tu n'as pas les droits nécessaires pour cette action.
        </p>
        <Link to="/" className="btn-primary w-full">
          Retour à l'accueil
        </Link>
      </div>
    </div>
  )
}
