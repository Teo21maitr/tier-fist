import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../features/auth/AuthContext'
import { ThemeToggle } from '../features/theme/ThemeContext'
import { LaurentBaffist } from '../components/LaurentBaffist'
import { Avatar } from '../components/ui'

export function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/connexion')
  }

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-3 py-2 text-sm font-medium transition ${
      isActive
        ? 'bg-brand-600 text-white'
        : 'text-slate-600 hover:bg-slate-200/60 dark:text-slate-300 dark:hover:bg-slate-800'
    }`

  return (
    <div className="min-h-screen">
      <a
        href="#contenu"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-brand-600 focus:px-4 focus:py-2 focus:text-white"
      >
        Aller au contenu
      </a>

      <header className="sticky top-0 z-30 border-b border-slate-200 bg-slate-100/85 backdrop-blur dark:border-slate-800 dark:bg-slate-950/85">
        <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
          <Link to="/" className="flex items-center gap-2 font-display text-lg font-extrabold">
            <LaurentBaffist className="h-9 w-9" mood="smug" />
            <span>
              Tier <span className="text-brand-500">Fist</span>
            </span>
          </Link>

          {user && (
            <nav aria-label="Navigation principale" className="ml-4 hidden gap-1 sm:flex">
              <NavLink to="/" end className={navClass}>
                Accueil
              </NavLink>
              <NavLink to="/mes-tier-lists" className={navClass}>
                Mes Tier Lists
              </NavLink>
            </nav>
          )}

          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            {user && (
              <>
                <Link
                  to="/profil"
                  className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-200/60 dark:hover:bg-slate-800"
                >
                  <Avatar user={user} size="sm" />
                  <span className="hidden text-sm font-medium sm:inline">{user.username}</span>
                </Link>
                <button type="button" onClick={handleLogout} className="btn-ghost text-sm">
                  Déconnexion
                </button>
              </>
            )}
          </div>
        </div>

        {user && (
          <nav aria-label="Navigation principale" className="flex gap-1 border-t border-slate-200 px-4 py-2 dark:border-slate-800 sm:hidden">
            <NavLink to="/" end className={navClass}>
              Accueil
            </NavLink>
            <NavLink to="/mes-tier-lists" className={navClass}>
              Mes Tier Lists
            </NavLink>
          </nav>
        )}
      </header>

      <main id="contenu" className="mx-auto max-w-6xl px-4 py-6 sm:py-10">
        <Outlet />
      </main>

      <footer className="mx-auto max-w-6xl px-4 pb-10 pt-4 text-center text-xs text-slate-400">
        Tier Fist — les classements calculés par Laurent Baffist, qui n'a jamais tort.
      </footer>
    </div>
  )
}
