import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { AppLayout } from '../layouts/AppLayout'
import { useAuth } from '../features/auth/AuthContext'
import { Spinner } from '../components/ui'

import { LoginPage } from '../pages/LoginPage'
import { RegisterPage } from '../pages/RegisterPage'
import { PendingAccountPage } from '../pages/PendingAccountPage'
import { HomePage } from '../pages/HomePage'
import { MyTierListsPage } from '../pages/MyTierListsPage'
import { CreateTierListPage } from '../pages/CreateTierListPage'
import { JoinPage } from '../pages/JoinPage'
import { TierListPage } from '../pages/TierListPage'
import { AnsweringPage } from '../pages/AnsweringPage'
import { ResultPage } from '../pages/ResultPage'
import { ProfilePage } from '../pages/ProfilePage'
import { NotFoundPage, ForbiddenPage } from '../pages/ErrorPages'

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) return <Spinner label="Laurent vérifie tes papiers…" />
  if (!user) return <Navigate to="/connexion" state={{ from: location.pathname }} replace />
  return <>{children}</>
}

function RedirectIfAuthenticated({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <Spinner />
  if (user) return <Navigate to="/" replace />
  return <>{children}</>
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route
          path="/connexion"
          element={
            <RedirectIfAuthenticated>
              <LoginPage />
            </RedirectIfAuthenticated>
          }
        />
        <Route
          path="/inscription"
          element={
            <RedirectIfAuthenticated>
              <RegisterPage />
            </RedirectIfAuthenticated>
          }
        />
        <Route path="/compte-en-attente" element={<PendingAccountPage />} />

        <Route
          path="/"
          element={
            <RequireAuth>
              <HomePage />
            </RequireAuth>
          }
        />
        <Route
          path="/mes-tier-lists"
          element={
            <RequireAuth>
              <MyTierListsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/creer"
          element={
            <RequireAuth>
              <CreateTierListPage />
            </RequireAuth>
          }
        />
        <Route
          path="/rejoindre"
          element={
            <RequireAuth>
              <JoinPage />
            </RequireAuth>
          }
        />
        <Route
          path="/tier-lists/:id"
          element={
            <RequireAuth>
              <TierListPage />
            </RequireAuth>
          }
        />
        <Route
          path="/tier-lists/:id/questionnaire"
          element={
            <RequireAuth>
              <AnsweringPage />
            </RequireAuth>
          }
        />
        <Route
          path="/tier-lists/:id/resultat"
          element={
            <RequireAuth>
              <ResultPage />
            </RequireAuth>
          }
        />
        <Route
          path="/profil"
          element={
            <RequireAuth>
              <ProfilePage />
            </RequireAuth>
          }
        />

        <Route path="/acces-refuse" element={<ForbiddenPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
