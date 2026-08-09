/**
 * Formats d'image acceptés à l'upload, alignés sur la validation backend
 * (voir backend/common/uploads.py).
 *
 * Le HEIC des iPhone est accepté puis converti en JPEG côté serveur : Chrome et
 * Firefox ne savent pas l'afficher. On liste les types MIME *et* les extensions,
 * car iOS et certains navigateurs n'annoncent pas toujours le bon type MIME.
 */
export const ACCEPTED_IMAGE_TYPES =
  'image/jpeg,image/png,image/gif,image/webp,image/heic,image/heif,.jpg,.jpeg,.png,.gif,.webp,.heic,.heif'

/** Libellé affiché sous les sélecteurs de fichier. */
export const ACCEPTED_IMAGE_LABEL = 'JPEG, PNG, GIF, WebP ou HEIC'
