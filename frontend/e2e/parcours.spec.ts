import { expect, test } from '@playwright/test'
import { createTierList, login, logout } from './helpers'

test.describe('Authentification', () => {
  test('un compte non validé ne peut pas se connecter', async ({ page }) => {
    const username = `pending${Date.now()}`.slice(0, 20)
    await page.goto('/inscription')
    await page.getByLabel('Pseudo').fill(username)
    await page.getByLabel('Mot de passe').fill('MotDePasse!42')
    await page.getByRole('button', { name: 'Demander un compte' }).click()

    await expect(page.getByText('Compte en attente de validation')).toBeVisible()

    await page.goto('/connexion')
    await page.getByLabel('Pseudo').fill(username)
    await page.getByLabel('Mot de passe').fill('MotDePasse!42')
    await page.getByRole('button', { name: 'Se connecter' }).click()
    await expect(page.getByText('Compte en attente de validation')).toBeVisible()
  })

  test('connexion puis déconnexion', async ({ page }) => {
    await login(page, 'teo')
    await expect(page.getByRole('heading', { name: 'Créer une Tier List' })).toBeVisible()
    await logout(page)
    await expect(page.getByRole('heading', { name: 'Connexion' })).toBeVisible()
  })

  test('une Tier List privée est inaccessible à un non-participant', async ({ page }) => {
    await login(page, 'teo')
    const { id } = await createTierList(page, `Privée ${Date.now()}`, 'Test')
    await logout(page)

    await login(page, 'paul')
    await page.goto(`/tier-lists/${id}`)
    await expect(page.getByText('404')).toBeVisible()
  })
})

test.describe('Construction collaborative', () => {
  test('créer une Tier List, ajouter items et questions, puis finaliser', async ({ page }) => {
    await login(page, 'teo')
    const { code } = await createTierList(page, `Fast-food ${Date.now()}`, 'Fast-food')

    expect(code).toMatch(/^[A-Z2-9]{6}$/)
    // Caractères ambigus exclus du code d'invitation.
    expect(code).not.toMatch(/[01OI]/)

    // Items
    for (const name of ['KFC', 'Quick']) {
      await page.getByRole('button', { name: '+ Ajouter un item' }).click()
      await page.getByLabel('Nom').fill(name)
      await page.getByRole('button', { name: 'Enregistrer' }).click()
      await expect(page.getByTitle(name)).toBeVisible()
    }

    // Doublon insensible à la casse : refusé.
    await page.getByRole('button', { name: '+ Ajouter un item' }).click()
    await page.getByLabel('Nom').fill('kfc')
    await page.getByRole('button', { name: 'Enregistrer' }).click()
    await expect(page.getByText(/Cet item existe déjà/)).toBeVisible()
    await page.getByRole('button', { name: 'Annuler' }).click()

    // Questions : la distribution 1,1,2,2,3,5 est imposée.
    await page.getByRole('button', { name: /^Questions/ }).click()
    const coefficients = [1, 1, 2, 2, 3, 5]
    for (const [index, coefficient] of coefficients.entries()) {
      await page.getByRole('button', { name: '+ Ajouter une question' }).click()
      await page.getByLabel('Affirmation').fill(`Cet item est réussi sur le critère ${index + 1}.`)
      await page.getByRole('radio', { name: `×${coefficient}` }).click()
      await page.getByRole('button', { name: 'Enregistrer' }).click()
      await expect(page.getByRole('heading', { name: `Questions (${index + 1}/6)` })).toBeVisible()
    }

    // Plus aucune question ne peut être ajoutée.
    await expect(page.getByRole('button', { name: '+ Ajouter une question' })).toHaveCount(0)

    // Finalisation avec confirmation explicite.
    await page.getByRole('button', { name: 'Finaliser la Tier List' }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.getByRole('button', { name: 'Oui, finaliser' }).click()
    await page.waitForURL(/questionnaire$/)
    await expect(page.getByRole('heading', { name: 'Questionnaire' })).toBeVisible()
  })

  test('rejoindre avec un code inconnu affiche une erreur claire', async ({ page }) => {
    await login(page, 'teo')
    await page.goto('/rejoindre')
    await page.getByLabel("Code d'invitation").fill('ZZZZZZ')
    await page.getByRole('button', { name: 'Rejoindre' }).click()
    await expect(page.getByText(/Ce code ne correspond à aucune Tier List/)).toBeVisible()
  })
})

test.describe('Questionnaire', () => {
  test('répondre, autosauvegarder puis verrouiller un item', async ({ page }) => {
    await login(page, 'teo')

    // La Tier List de démonstration « Pokémon de départ » est en phase ANSWERING.
    await page.getByRole('link', { name: /Pokémon de départ/ }).click()
    await page.waitForURL(/questionnaire$/)

    // Les six questions, chacune sur une échelle de 1 à 9.
    const groups = page.getByRole('radiogroup')
    await expect(groups).toHaveCount(6)
    for (let index = 0; index < 6; index += 1) {
      await groups.nth(index).getByRole('radio', { name: '7' }).click()
    }

    // Autosave : la valeur survit à un rechargement, sans validation.
    await page.reload()
    await expect(page.getByRole('radiogroup').first().getByRole('radio', { name: '7' })).toBeChecked()

    const validateButton = page.getByRole('button', { name: /^Valider / })
    const itemLabel = await validateButton.innerText()
    await validateButton.click()

    // L'item validé disparaît au profit du suivant, et la progression augmente.
    await expect(page.getByText(/1 \/ 5 items validés/)).toBeVisible()
    await expect(page.getByRole('button', { name: /^Valider / })).not.toHaveText(itemLabel)
  })

  test('la progression des autres est visible, pas leurs réponses', async ({ page }) => {
    await login(page, 'teo')
    await page.getByRole('link', { name: /Pokémon de départ/ }).click()
    await page.waitForURL(/questionnaire$/)

    const section = page.getByRole('heading', { name: 'Avancement des joueurs' })
    await expect(section).toBeVisible()
    await expect(page.getByText('laura')).toBeVisible()
    // Aucune valeur de réponse d'autrui n'est exposée.
    await expect(page.getByText(/réponse de laura/i)).toHaveCount(0)
  })
})

test.describe('Résultat et joker', () => {
  test('le classement définitif affiche les cinq rangs', async ({ page }) => {
    await login(page, 'teo')
    await page.getByRole('link', { name: /Jeux vidéo cultes/ }).click()
    await page.waitForURL(/resultat$/)

    await expect(page.getByRole('heading', { name: 'Résultat définitif' })).toBeVisible()
    for (const rank of ['S', 'A', 'B', 'C', 'D']) {
      await expect(page.getByText(rank, { exact: true })).toBeVisible()
    }
  })

  test("le détail d'un item montre score global et moyennes", async ({ page }) => {
    await login(page, 'teo')
    await page.goto('/mes-tier-lists')
    await page.getByRole('link', { name: /Jeux vidéo cultes/ }).click()
    await page.waitForURL(/resultat$/)

    await page.locator('ul li button').first().click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText('Score global')).toBeVisible()
    await expect(dialog.getByText('Détail par question')).toBeVisible()

    // La consultation des réponses individuelles est permise une fois la partie finie.
    await dialog.getByRole('button', { name: /détail individuel/ }).click()
    await expect(dialog.getByText(/Score :/).first()).toBeVisible()
  })

  test("un joueur hors tour ne peut pas jouer de joker", async ({ page }) => {
    await login(page, 'teo')
    await page.goto('/mes-tier-lists')
    await page.getByRole('link', { name: /Films de Noël/ }).click()
    await page.waitForURL(/resultat$/)

    // Ce n'est pas le tour de teo : aucun panneau de joker jouable.
    await expect(page.getByRole('heading', { name: 'Ton joker' })).toHaveCount(0)
    await expect(page.getByText(/de jouer son joker/)).toBeVisible()
  })
})

test.describe('Préférences', () => {
  test('le thème clair/sombre est mémorisé', async ({ page }) => {
    await login(page, 'teo')
    const html = page.locator('html')
    const wasDark = await html.evaluate((node) => node.classList.contains('dark'))

    await page.getByRole('button', { name: /Passer en thème/ }).click()
    await expect
      .poll(() => html.evaluate((node) => node.classList.contains('dark')))
      .toBe(!wasDark)

    await page.reload()
    await expect
      .poll(() => html.evaluate((node) => node.classList.contains('dark')))
      .toBe(!wasDark)
  })
})
