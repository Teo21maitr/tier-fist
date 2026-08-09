/** Hooks TanStack Query : cache, invalidations et polling léger (spec §23). */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, api } from './client'
import type {
  AnsweringPayload,
  CurrentUser,
  Item,
  ItemResultDetail,
  JokerStatePayload,
  Participant,
  ParticipantProgress,
  Question,
  RankingPayload,
  TierList,
} from '../types'

export const keys = {
  me: ['me'] as const,
  tierLists: (filter?: string) => ['tier-lists', filter ?? 'all'] as const,
  tierList: (id: number) => ['tier-list', id] as const,
  items: (id: number) => ['tier-list', id, 'items'] as const,
  questions: (id: number) => ['tier-list', id, 'questions'] as const,
  participants: (id: number) => ['tier-list', id, 'participants'] as const,
  answering: (id: number) => ['tier-list', id, 'answering'] as const,
  ranking: (id: number) => ['tier-list', id, 'ranking'] as const,
  joker: (id: number) => ['tier-list', id, 'joker'] as const,
  itemDetail: (id: number, itemId: number) => ['tier-list', id, 'item', itemId] as const,
}

/** Cadence de polling des écrans d'attente : suffisamment vive, sans noyer l'API. */
export const WAITING_POLL_MS = 8000

// --- Auth ------------------------------------------------------------------

export function useMe() {
  return useQuery({
    queryKey: keys.me,
    // « Non authentifié » est une réponse valide, pas une erreur : sans cela,
    // la requête resterait en état d'erreur en conservant l'ancien utilisateur,
    // et l'interface continuerait de le montrer connecté après un logout.
    queryFn: async (): Promise<CurrentUser | null> => {
      try {
        return await api.get<CurrentUser>('/api/auth/me')
      } catch (error) {
        if (error instanceof ApiError && [401, 403].includes(error.status)) return null
        throw error
      }
    },
    retry: false,
    staleTime: 60_000,
  })
}

// --- Tier Lists ------------------------------------------------------------

export function useTierLists(filter?: string) {
  return useQuery({
    queryKey: keys.tierLists(filter),
    queryFn: () =>
      api.get<TierList[]>(`/api/tier-lists${filter ? `?status=${filter}` : ''}`),
  })
}

export function useTierList(id: number, options: { poll?: boolean } = {}) {
  return useQuery({
    queryKey: keys.tierList(id),
    queryFn: () => api.get<TierList>(`/api/tier-lists/${id}`),
    refetchInterval: options.poll ? WAITING_POLL_MS : false,
  })
}

export function useItems(id: number) {
  return useQuery({
    queryKey: keys.items(id),
    queryFn: () => api.get<Item[]>(`/api/tier-lists/${id}/items`),
  })
}

export function useQuestions(id: number) {
  return useQuery({
    queryKey: keys.questions(id),
    queryFn: () => api.get<Question[]>(`/api/tier-lists/${id}/questions`),
  })
}

export function useParticipants(id: number, options: { poll?: boolean } = {}) {
  return useQuery({
    queryKey: keys.participants(id),
    queryFn: () =>
      api.get<Array<Participant | ParticipantProgress>>(`/api/tier-lists/${id}/participants`),
    refetchInterval: options.poll ? WAITING_POLL_MS : false,
  })
}

export function useAnswering(id: number, options: { poll?: boolean } = {}) {
  return useQuery({
    queryKey: keys.answering(id),
    queryFn: () => api.get<AnsweringPayload>(`/api/tier-lists/${id}/answering`),
    refetchInterval: options.poll ? WAITING_POLL_MS : false,
  })
}

export function useRanking(id: number) {
  return useQuery({
    queryKey: keys.ranking(id),
    queryFn: () => api.get<RankingPayload>(`/api/tier-lists/${id}/ranking`),
  })
}

export function useJokerState(id: number, options: { poll?: boolean } = {}) {
  return useQuery({
    queryKey: keys.joker(id),
    queryFn: () => api.get<JokerStatePayload>(`/api/tier-lists/${id}/joker`),
    refetchInterval: options.poll ? WAITING_POLL_MS : false,
  })
}

export function useItemDetail(id: number, itemId: number | null) {
  return useQuery({
    queryKey: keys.itemDetail(id, itemId ?? 0),
    queryFn: () =>
      api.get<ItemResultDetail>(`/api/tier-lists/${id}/items/${itemId}/result-detail`),
    enabled: itemId !== null,
  })
}

// --- Invalidations ---------------------------------------------------------

/** Recharge tout ce qui dépend d'une Tier List après une action importante. */
export function useRefreshTierList(id: number) {
  const queryClient = useQueryClient()
  return () => {
    queryClient.invalidateQueries({ queryKey: ['tier-list', id] })
    queryClient.invalidateQueries({ queryKey: ['tier-lists'] })
  }
}

export function useTierListMutation<TVariables, TData>(
  id: number,
  mutationFn: (variables: TVariables) => Promise<TData>,
) {
  const refresh = useRefreshTierList(id)
  return useMutation({ mutationFn, onSuccess: refresh })
}
