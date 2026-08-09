import { createContext, useCallback, useContext, useMemo } from 'react'
import type { ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import { keys, useMe } from '../../api/queries'
import type { CurrentUser } from '../../types'

interface AuthContextValue {
  user: CurrentUser | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<CurrentUser>
  logout: () => Promise<void>
  register: (username: string, password: string) => Promise<{ detail: string }>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const { data, isLoading } = useMe()

  const login = useCallback(
    async (username: string, password: string) => {
      const user = await api.post<CurrentUser>('/api/auth/login', { username, password })
      queryClient.setQueryData(keys.me, user)
      return user
    },
    [queryClient],
  )

  const logout = useCallback(async () => {
    await api.post('/api/auth/logout')
    // On jette toutes les données privées mises en cache, mais on garde la
    // requête d'authentification vivante : la vider détacherait son observateur,
    // qui continuerait alors d'exposer l'utilisateur précédent.
    queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== 'me' })
    queryClient.setQueryData(keys.me, null)
  }, [queryClient])

  const register = useCallback(
    (username: string, password: string) =>
      api.post<{ detail: string }>('/api/auth/register', { username, password }),
    [],
  )

  const value = useMemo(
    () => ({ user: data ?? null, isLoading, login, logout, register }),
    [data, isLoading, login, logout, register],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth doit être utilisé dans un AuthProvider")
  return context
}
