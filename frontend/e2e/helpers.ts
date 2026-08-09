import type { Page } from '@playwright/test'

export const PASSWORD = 'MotDePasse!42'

export async function login(page: Page, username: string) {
  await page.goto('/connexion')
  await page.getByLabel('Pseudo').fill(username)
  await page.getByLabel('Mot de passe').fill(PASSWORD)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await page.waitForURL('**/')
}

export async function logout(page: Page) {
  await page.getByRole('button', { name: 'Déconnexion' }).click()
  await page.waitForURL('**/connexion')
}

/** Crée une Tier List via l'interface et renvoie son code d'invitation. */
export async function createTierList(page: Page, name: string, theme: string) {
  await page.goto('/creer')
  await page.getByRole('textbox', { name: 'Nom' }).fill(name)
  await page.getByRole('textbox', { name: 'Thème' }).fill(theme)
  await page.getByRole('button', { name: 'Créer' }).click()
  await page.waitForURL(/\/tier-lists\/\d+$/)
  const url = page.url()
  const id = Number(url.split('/').pop())
  const code = (await page.locator('p.font-mono').first().innerText()).trim()
  return { id, code }
}
