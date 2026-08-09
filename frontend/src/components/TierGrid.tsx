import { useState } from 'react'
import type { RankingRank } from '../types'
import { ItemImage, RANK_BACKGROUND, RANK_TEXT } from './ui'

interface TierGridProps {
  ranks: RankingRank[]
  onSelectItem?: (itemId: number) => void
  /** Item actuellement choisi pour un joker (aperçu avant validation). */
  selectedItemId?: number | null
  /** Rang de destination prévisualisé pour l'item sélectionné. */
  previewRank?: number | null
  /** Active le glisser-déposer (complément du mode sélection, jamais l'unique moyen). */
  draggable?: boolean
  onMove?: (itemId: number, toRank: number) => void
  /** Items verrouillés par un joker déjà joué : plus déplaçables. */
  lockedItemIds?: number[]
}

/**
 * Grille de Tier List (spec §31) : une ligne par rang, label bien visible,
 * cartes compactes avec grandes images. Responsive et lisible sur mobile.
 */
export function TierGrid({
  ranks,
  onSelectItem,
  selectedItemId = null,
  previewRank = null,
  draggable = false,
  onMove,
  lockedItemIds = [],
}: TierGridProps) {
  const [dragOverRank, setDragOverRank] = useState<number | null>(null)

  // Aperçu : l'item sélectionné apparaît déjà dans son rang de destination.
  const displayed = ranks.map((rank) => ({
    ...rank,
    items: rank.items.filter((item) => !(previewRank !== null && item.id === selectedItemId)),
  }))
  if (previewRank !== null && selectedItemId !== null) {
    const moving = ranks.flatMap((rank) => rank.items).find((item) => item.id === selectedItemId)
    const target = displayed.find((rank) => rank.number === previewRank)
    if (moving && target) target.items = [...target.items, moving]
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-300 dark:border-slate-800">
      {displayed.map((rank) => (
        <div
          key={rank.number}
          className={`flex border-b border-slate-300 last:border-b-0 dark:border-slate-800 ${
            dragOverRank === rank.number ? 'bg-brand-100 dark:bg-brand-950/60' : ''
          }`}
          onDragOver={
            draggable
              ? (event) => {
                  event.preventDefault()
                  setDragOverRank(rank.number)
                }
              : undefined
          }
          onDragLeave={draggable ? () => setDragOverRank(null) : undefined}
          onDrop={
            draggable
              ? (event) => {
                  event.preventDefault()
                  setDragOverRank(null)
                  const itemId = Number(event.dataTransfer.getData('text/plain'))
                  if (itemId && onMove) onMove(itemId, rank.number)
                }
              : undefined
          }
        >
          <div
            className={`flex w-16 shrink-0 items-center justify-center p-2 text-center sm:w-24 ${RANK_BACKGROUND[rank.color]} ${RANK_TEXT[rank.color]}`}
          >
            <span className="font-display text-sm font-black leading-tight sm:text-xl">
              {rank.name}
            </span>
          </div>

          <ul className="flex min-h-[5.5rem] flex-1 flex-wrap content-start gap-2 bg-slate-50 p-2 dark:bg-slate-900 sm:min-h-[7rem]">
            {rank.items.length === 0 && (
              <li className="self-center px-2 text-xs text-slate-400">Rang vide</li>
            )}
            {rank.items.map((item) => {
              const locked = lockedItemIds.includes(item.id)
              const selected = item.id === selectedItemId
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    draggable={draggable && !locked}
                    onDragStart={(event) => event.dataTransfer.setData('text/plain', String(item.id))}
                    onClick={() => onSelectItem?.(item.id)}
                    aria-pressed={onSelectItem ? selected : undefined}
                    className={`group relative w-16 overflow-hidden rounded-xl border-2 bg-white text-left transition hover:-translate-y-0.5 dark:bg-slate-950 sm:w-20 ${
                      selected
                        ? 'border-brand-500 ring-2 ring-brand-400'
                        : 'border-transparent hover:border-brand-400'
                    }`}
                    title={item.name}
                  >
                    <ItemImage name={item.name} url={item.image_url} className="h-16 w-full sm:h-20" />
                    <span className="block truncate px-1 py-1 text-[11px] font-semibold">
                      {item.name}
                    </span>
                    {/* Un item déplacé par un joker est verrouillé pour toute la
                        partie : un seul badge suffit à dire les deux. */}
                    {locked && (
                      <span
                        className="absolute right-1 top-1 rounded bg-brand-600 px-1 text-[10px] font-semibold text-white"
                        title="Déplacé par un joker : plus modifiable"
                      >
                        🔒 joker
                      </span>
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </div>
  )
}
