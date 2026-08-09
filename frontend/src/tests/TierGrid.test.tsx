import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { TierGrid } from '../components/TierGrid'
import type { RankedItem, RankingRank } from '../types'

function item(id: number, name: string, overrides: Partial<RankedItem> = {}): RankedItem {
  return {
    id,
    name,
    image_url: null,
    has_image: false,
    joker_locked: false,
    global_score: '7.00',
    algorithm_rank: 1,
    moved_by_joker: false,
    ...overrides,
  }
}

const ranks: RankingRank[] = [
  { number: 1, name: 'S', color: 'red', items: [item(1, 'KFC')] },
  { number: 2, name: 'A', color: 'orange', items: [item(2, 'Quick')] },
  { number: 3, name: 'B', color: 'yellow', items: [] },
  { number: 4, name: 'C', color: 'green', items: [] },
  { number: 5, name: 'D', color: 'blue', items: [item(3, 'McDo')] },
]

describe('grille de Tier List', () => {
  it('affiche les cinq rangs avec leurs noms personnalisés', () => {
    const custom = ranks.map((rank, index) =>
      index === 0 ? { ...rank, name: 'Légendaire' } : rank,
    )
    render(<TierGrid ranks={custom} />)
    for (const name of ['Légendaire', 'A', 'B', 'C', 'D']) {
      expect(screen.getByText(name)).toBeInTheDocument()
    }
  })

  it('signale explicitement les rangs vides', () => {
    render(<TierGrid ranks={ranks} />)
    expect(screen.getAllByText('Rang vide')).toHaveLength(2)
  })

  it('prévisualise un déplacement sans modifier les données', () => {
    render(<TierGrid ranks={ranks} selectedItemId={3} previewRank={1} />)
    // McDo (rang D) apparaît en aperçu dans le rang S.
    const sRow = screen.getByText('S').closest('div')!.parentElement!
    expect(within(sRow).getByTitle('McDo')).toBeInTheDocument()
  })

  it('marque les items déjà déplacés par un joker', () => {
    const locked = ranks.map((rank) =>
      rank.number === 1
        ? { ...rank, items: [item(1, 'KFC', { joker_locked: true, moved_by_joker: true })] }
        : rank,
    )
    render(<TierGrid ranks={locked} lockedItemIds={[1]} />)
    expect(screen.getByTitle('Déplacé par un joker : plus modifiable')).toBeInTheDocument()
  })

  it('remonte la sélection d’un item', async () => {
    const onSelectItem = vi.fn()
    render(<TierGrid ranks={ranks} onSelectItem={onSelectItem} />)
    await userEvent.click(screen.getByTitle('KFC'))
    expect(onSelectItem).toHaveBeenCalledWith(1)
  })

  it('reste utilisable sans glisser-déposer : chaque item est un bouton', () => {
    render(<TierGrid ranks={ranks} onSelectItem={() => {}} />)
    expect(screen.getByRole('button', { name: /KFC/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /McDo/ })).toBeInTheDocument()
  })
})
