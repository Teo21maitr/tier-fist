import { describe, expect, it } from 'vitest'
import { describeTierList } from '../utils/tierListState'
import type { TierList, TierListStatus, ViewerState } from '../types'

function tierList(status: TierListStatus, viewer: ViewerState = {}): TierList {
  return {
    id: 7,
    name: 'Fast-food',
    theme: 'Fast-food',
    invite_code: 'A7K4P9',
    status,
    creator: { id: 1, username: 'teo', avatar_url: null, initial: 'T' },
    ranks: [],
    participants_count: 2,
    items_count: 4,
    questions_count: 6,
    is_creator: true,
    can_finalize: false,
    finalization_blockers: [],
    coefficients: [],
    viewer,
    created_at: '',
    updated_at: '',
    finalized_at: null,
    completed_at: null,
  }
}

describe("état d'une Tier List sur l'accueil", () => {
  it('range une Tier List DRAFT dans « En création »', () => {
    const state = describeTierList(tierList('DRAFT'))
    expect(state.section).toBe('draft')
    expect(state.needsMe).toBe(false)
    expect(state.href).toBe('/tier-lists/7')
  })

  it('met en évidence un questionnaire à compléter', () => {
    const state = describeTierList(tierList('ANSWERING', { has_finished_answering: false }))
    expect(state.section).toBe('todo')
    expect(state.needsMe).toBe(true)
    expect(state.href).toBe('/tier-lists/7/questionnaire')
  })

  it("bascule en attente lorsque l'utilisateur a terminé", () => {
    const state = describeTierList(tierList('ANSWERING', { has_finished_answering: true }))
    expect(state.section).toBe('waiting')
    expect(state.needsMe).toBe(false)
  })

  it('signale un tour de joker à jouer', () => {
    const state = describeTierList(tierList('JOKER', { is_my_joker_turn: true }))
    expect(state.section).toBe('joker')
    expect(state.needsMe).toBe(true)
    expect(state.href).toBe('/tier-lists/7/resultat')
  })

  it("n'exige rien quand ce n'est pas son tour de joker", () => {
    const state = describeTierList(tierList('JOKER', { is_my_joker_turn: false }))
    expect(state.section).toBe('waiting')
    expect(state.needsMe).toBe(false)
  })

  it('classe une partie terminée', () => {
    const state = describeTierList(tierList('COMPLETED'))
    expect(state.section).toBe('done')
    expect(state.needsMe).toBe(false)
  })

  it("fournit un marqueur en plus de la couleur pour chaque état", () => {
    // On ne doit jamais reposer uniquement sur la couleur (accessibilité).
    const statuses: TierListStatus[] = ['DRAFT', 'ANSWERING', 'JOKER', 'COMPLETED']
    for (const status of statuses) {
      expect(describeTierList(tierList(status)).marker).not.toBe('')
    }
  })
})
