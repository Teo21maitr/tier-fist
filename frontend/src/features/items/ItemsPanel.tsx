import { useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api, ApiError } from '../../api/client'
import { useItems, useRefreshTierList } from '../../api/queries'
import { LaurentBubble } from '../../components/LaurentBubble'
import { EmptyState, ErrorNote, ItemImage, Modal, Spinner } from '../../components/ui'
import type { Item, TierList } from '../../types'

type ImageMode = 'none' | 'upload' | 'url'

export function ItemsPanel({ tierList }: { tierList: TierList }) {
  const { data: items, isLoading } = useItems(tierList.id)
  const refresh = useRefreshTierList(tierList.id)
  const [editing, setEditing] = useState<Item | null>(null)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const remove = useMutation({
    mutationFn: (item: Item) => api.delete(`/api/tier-lists/${tierList.id}/items/${item.id}`),
    onSuccess: refresh,
    onError: (caught) =>
      setError(caught instanceof ApiError ? caught.message : 'Suppression impossible.'),
  })

  const readOnly = tierList.status !== 'DRAFT'

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-xl font-bold">
          Items <span className="text-slate-400">({items?.length ?? 0})</span>
        </h2>
        {!readOnly && (
          <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
            + Ajouter un item
          </button>
        )}
      </div>

      <LaurentBubble variant="compact" mood="smug">
        {items && items.length === 0
          ? 'Pour classer des choses, il me faudrait idéalement… des choses.'
          : 'Plus il y a de candidats, plus j’ai de travail. Merci, vraiment.'}
      </LaurentBubble>

      {error && <ErrorNote>{error}</ErrorNote>}
      {isLoading && <Spinner />}

      {items && items.length === 0 && (
        <EmptyState>Aucun item pour le moment.</EmptyState>
      )}

      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {(items ?? []).map((item) => (
          <li
            key={item.id}
            className="overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
          >
            <ItemImage name={item.name} url={item.image_url} className="h-28 w-full" />
            <div className="space-y-2 p-3">
              <p className="truncate text-sm font-semibold" title={item.name}>
                {item.name}
              </p>
              {!readOnly && (
                <div className="flex gap-1">
                  <button
                    type="button"
                    className="btn-ghost px-2 py-1 text-xs"
                    onClick={() => setEditing(item)}
                  >
                    Modifier
                  </button>
                  <button
                    type="button"
                    className="btn-ghost px-2 py-1 text-xs text-rose-600 dark:text-rose-400"
                    onClick={() => {
                      if (window.confirm(`Supprimer « ${item.name} » ?`)) remove.mutate(item)
                    }}
                  >
                    Supprimer
                  </button>
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>

      {(creating || editing) && (
        <ItemDialog
          tierList={tierList}
          item={editing}
          onClose={() => {
            setCreating(false)
            setEditing(null)
          }}
          onSaved={() => {
            refresh()
            setCreating(false)
            setEditing(null)
          }}
        />
      )}
    </section>
  )
}

function ItemDialog({
  tierList,
  item,
  onClose,
  onSaved,
}: {
  tierList: TierList
  item: Item | null
  onClose: () => void
  onSaved: () => void
}) {
  const [name, setName] = useState(item?.name ?? '')
  const [imageMode, setImageMode] = useState<ImageMode>(
    item?.image_url?.startsWith('http') && !item.image_url.includes('/media/') ? 'url' : 'none',
  )
  const [imageUrl, setImageUrl] = useState(
    item && imageModeIsUrl(item) ? (item.image_url ?? '') : '',
  )
  const fileInput = useRef<HTMLInputElement>(null)
  const [error, setError] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: async () => {
      const base = `/api/tier-lists/${tierList.id}/items`
      const path = item ? `${base}/${item.id}` : base
      const file = fileInput.current?.files?.[0]

      if (imageMode === 'upload' && file) {
        const formData = new FormData()
        formData.append('name', name)
        formData.append('uploaded_image', file)
        return item ? api.patchForm(path, formData) : api.postForm(path, formData)
      }

      const payload: Record<string, unknown> = { name }
      if (imageMode === 'url') payload.external_image_url = imageUrl
      if (imageMode === 'none') payload.remove_image = true
      return item ? api.patch(path, payload) : api.post(path, payload)
    },
    onSuccess: onSaved,
    onError: (caught) =>
      setError(caught instanceof ApiError ? caught.message : 'Enregistrement impossible.'),
  })

  return (
    <Modal
      open
      onClose={onClose}
      title={item ? `Modifier « ${item.name} »` : 'Nouvel item'}
      footer={
        <>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Annuler
          </button>
          <button
            type="submit"
            form="item-form"
            className="btn-primary"
            disabled={save.isPending || !name.trim()}
          >
            {save.isPending ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </>
      }
    >
      <form
        id="item-form"
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          setError(null)
          save.mutate()
        }}
      >
        {error && <ErrorNote>{error}</ErrorNote>}

        <div>
          <label className="label" htmlFor="item-name">
            Nom
          </label>
          <input
            id="item-name"
            className="input"
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={120}
            required
            autoFocus
          />
        </div>

        <fieldset>
          <legend className="label">Image (facultative)</legend>
          <div className="flex flex-wrap gap-2">
            {(
              [
                ['none', 'Aucune (Laurent pose)'],
                ['upload', 'Depuis mon appareil'],
                ['url', 'Depuis une URL'],
              ] as Array<[ImageMode, string]>
            ).map(([mode, label]) => (
              <label
                key={mode}
                className={`relative cursor-pointer rounded-xl border px-3 py-2 text-sm ${
                  imageMode === mode
                    ? 'border-brand-500 bg-brand-50 font-semibold dark:bg-brand-950/40'
                    : 'border-slate-300 dark:border-slate-700'
                }`}
              >
                <input
                  type="radio"
                  name="image-mode"
                  className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                  checked={imageMode === mode}
                  onChange={() => setImageMode(mode)}
                />
                {label}
              </label>
            ))}
          </div>

          {imageMode === 'upload' && (
            <input
              ref={fileInput}
              type="file"
              accept="image/*"
              className="mt-3 block w-full text-sm"
              aria-label="Fichier image"
            />
          )}
          {imageMode === 'url' && (
            <input
              type="url"
              className="input mt-3"
              value={imageUrl}
              onChange={(event) => setImageUrl(event.target.value)}
              placeholder="https://exemple.com/image.png"
              aria-label="URL de l'image"
            />
          )}
        </fieldset>
      </form>
    </Modal>
  )
}

function imageModeIsUrl(item: Item): boolean {
  return Boolean(item.image_url && !item.image_url.includes('/media/'))
}
