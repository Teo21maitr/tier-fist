import { Link } from 'react-router-dom'
import type { TierList } from '../types'
import { describeTierList, TONE_CLASSES } from '../utils/tierListState'
import { ProgressBar } from './ui'

export function TierListCard({ tierList }: { tierList: TierList }) {
  const state = describeTierList(tierList)

  return (
    <Link
      to={state.href}
      className={`block rounded-2xl border p-4 transition hover:-translate-y-0.5 hover:shadow-md ${
        state.needsMe
          ? 'border-brand-400 bg-white shadow-sm dark:border-brand-600 dark:bg-slate-900'
          : 'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate font-display text-lg font-bold">{tierList.name}</h3>
          <p className="truncate text-sm text-slate-500">{tierList.theme}</p>
        </div>
        <span
          className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold ${TONE_CLASSES[state.tone]}`}
        >
          <span aria-hidden className="mr-1">
            {state.marker}
          </span>
          {state.label}
        </span>
      </div>

      <dl className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
        <div className="flex gap-1">
          <dt>Participants</dt>
          <dd className="font-semibold text-slate-700 dark:text-slate-300">
            {tierList.participants_count}
          </dd>
        </div>
        <div className="flex gap-1">
          <dt>Items</dt>
          <dd className="font-semibold text-slate-700 dark:text-slate-300">
            {tierList.items_count}
          </dd>
        </div>
        <div className="flex gap-1">
          <dt>Questions</dt>
          <dd className="font-semibold text-slate-700 dark:text-slate-300">
            {tierList.questions_count}/6
          </dd>
        </div>
      </dl>

      {tierList.status === 'ANSWERING' && (
        <div className="mt-3 space-y-1">
          <ProgressBar
            percent={tierList.viewer.progress_percent ?? 0}
            label={`Ta progression sur ${tierList.name}`}
          />
          <p className="text-xs text-slate-500">
            {tierList.viewer.validated_items ?? 0} / {tierList.viewer.total_items ?? 0} items validés
          </p>
        </div>
      )}
    </Link>
  )
}
