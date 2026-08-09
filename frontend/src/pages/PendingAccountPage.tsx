import { Link } from 'react-router-dom'
import { LaurentBubble } from '../components/LaurentBubble'

export function PendingAccountPage() {
  return (
    <div className="mx-auto max-w-md space-y-6 text-center">
      <LaurentBubble variant="hero" mood="neutral">
        Ton compte existe, mais il attend le feu vert d'un administrateur. Patiente, je surveille
        la file.
      </LaurentBubble>

      <div className="card space-y-3">
        <h1 className="font-display text-2xl font-bold">Compte en attente de validation</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Un administrateur doit accepter ta demande avant que tu puisses te connecter. Reviens
          essayer un peu plus tard.
        </p>
        <Link to="/connexion" className="btn-secondary w-full">
          Retour à la connexion
        </Link>
      </div>
    </div>
  )
}
