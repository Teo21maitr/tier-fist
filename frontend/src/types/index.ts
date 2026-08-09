export type TierListStatus = 'DRAFT' | 'ANSWERING' | 'JOKER' | 'COMPLETED'
export type JokerStatus = 'PENDING' | 'USED' | 'SKIPPED' | 'FORCED_SKIP'
export type RankColor = 'red' | 'orange' | 'yellow' | 'green' | 'blue'

export interface PublicUser {
  id: number
  username: string
  avatar_url: string | null
  initial: string
}

export interface CurrentUser extends PublicUser {
  status: 'PENDING' | 'ACTIVE'
  is_staff: boolean
}

export interface Rank {
  number: number
  name: string
  color: RankColor
}

export interface CoefficientSlot {
  coefficient: number
  slots: number
  used: number
  remaining: number
}

export interface ViewerState {
  participant_id?: number
  validated_items?: number
  total_items?: number
  progress_percent?: number
  has_finished_answering?: boolean
  joker_status?: JokerStatus | null
  is_my_joker_turn?: boolean
  waiting_for_others?: boolean
}

export interface TierList {
  id: number
  name: string
  theme: string
  invite_code: string
  status: TierListStatus
  creator: PublicUser
  ranks: Rank[]
  participants_count: number
  items_count: number
  questions_count: number
  is_creator: boolean
  can_finalize: boolean
  finalization_blockers: string[]
  coefficients: CoefficientSlot[]
  viewer: ViewerState
  created_at: string
  updated_at: string
  finalized_at: string | null
  completed_at: string | null
}

export interface Item {
  id: number
  name: string
  image_url: string | null
  has_image: boolean
  joker_locked: boolean
}

export interface RankedItem extends Item {
  global_score: string | null
  algorithm_rank: number
  moved_by_joker: boolean
}

export interface Question {
  id: number
  text: string
  display_order: number
  coefficient?: number
}

export interface Participant {
  id: number
  user: PublicUser
  is_creator: boolean
  joined_at?: string
}

export interface ParticipantProgress {
  id: number
  user: PublicUser
  is_creator: boolean
  validated_items: number
  total_items: number
  progress_percent: number
  has_finished: boolean
}

export interface AnsweringItem extends Item {
  display_order: number
  is_validated: boolean
  answers: Record<string, number>
}

export interface AnsweringPayload {
  tier_list: TierList
  questions: Question[]
  items: AnsweringItem[]
  progress: {
    validated_items: number
    total_items: number
    progress_percent: number
    has_finished: boolean
  }
  participants: ParticipantProgress[]
}

export interface RankingRank {
  number: number
  name: string
  color: RankColor
  items: RankedItem[]
}

export interface RankingPayload {
  status: TierListStatus
  is_final: boolean
  ranks: RankingRank[]
}

export interface JokerActionPayload {
  participant_id: number
  user: PublicUser
  joker_order: number | null
  status: JokerStatus
  status_label: string
  item: Item | null
  from_rank: number | null
  to_rank: number | null
  played_at: string | null
  forced_by: PublicUser | null
}

export interface JokerStatePayload {
  status: TierListStatus
  is_creator: boolean
  my_participant_id: number
  current_turn: JokerActionPayload | null
  is_my_turn: boolean
  my_joker: JokerActionPayload | null
  order: JokerActionPayload[]
  history: JokerActionPayload[]
  locked_item_ids: number[]
  ranking: RankingPayload
}

export interface ItemResultDetail {
  item: Item
  global_score: string | null
  current_rank: number | null
  algorithm_rank: number | null
  rank_name: string | null
  questions: Array<{ id: number; text: string; coefficient: number; average: string | null }>
  participants: Array<{
    participant_id: number
    user: PublicUser
    score: string | null
    answers: Record<string, number | null>
  }>
}
