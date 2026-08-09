import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AnswerScale } from '../features/answering/AnswerScale'

describe('échelle de réponse 1 à 9', () => {
  it('affiche exactement neuf valeurs entières', () => {
    render(
      <AnswerScale questionId={1} questionText="Cet item est réussi." value={undefined} onChange={() => {}} />,
    )
    const options = screen.getAllByRole('radio')
    expect(options).toHaveLength(9)
    expect(options.map((option) => (option as HTMLInputElement).value)).toEqual([
      '1', '2', '3', '4', '5', '6', '7', '8', '9',
    ])
  })

  it('affiche les libellés fixes des deux extrémités', () => {
    render(
      <AnswerScale questionId={1} questionText="Cet item est réussi." value={undefined} onChange={() => {}} />,
    )
    expect(screen.getAllByText("Pas du tout d'accord").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Tout à fait d'accord").length).toBeGreaterThan(0)
  })

  it('remonte la valeur choisie', async () => {
    const onChange = vi.fn()
    render(
      <AnswerScale questionId={1} questionText="Cet item est réussi." value={undefined} onChange={onChange} />,
    )
    await userEvent.click(screen.getByRole('radio', { name: '7' }))
    expect(onChange).toHaveBeenCalledWith(7)
  })

  it('marque la valeur sélectionnée', () => {
    render(
      <AnswerScale questionId={1} questionText="Cet item est réussi." value={5} onChange={() => {}} />,
    )
    expect(screen.getByRole('radio', { name: /5/ })).toBeChecked()
  })

  it("désactive toute l'échelle une fois l'item validé", async () => {
    const onChange = vi.fn()
    render(
      <AnswerScale
        questionId={1}
        questionText="Cet item est réussi."
        value={5}
        disabled
        onChange={onChange}
      />,
    )
    const option = screen.getByRole('radio', { name: '9' })
    expect(option).toBeDisabled()
    await userEvent.click(option)
    expect(onChange).not.toHaveBeenCalled()
  })

  it("expose l'affirmation comme libellé accessible du groupe", () => {
    render(
      <AnswerScale questionId={1} questionText="Cet item est mémorable." value={undefined} onChange={() => {}} />,
    )
    expect(screen.getByRole('radiogroup', { name: 'Cet item est mémorable.' })).toBeInTheDocument()
  })
})
