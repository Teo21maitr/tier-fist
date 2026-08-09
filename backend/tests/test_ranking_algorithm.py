"""Spécification exécutable de l'algorithme de classement (spec §27 à §30, §62).

Ces tests ne touchent pas la base de données : ils décrivent le comportement
attendu de l'algorithme pur. Ils font autorité sur l'implémentation.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tierlists.services.ranking import assign_ranks, compute_rank_sizes, rank_groups


def scores(*values) -> list[tuple[str, Decimal]]:
    """[("I1", 8.90), ...] à partir d'une suite de valeurs décroissantes."""
    return [(f"I{index + 1}", Decimal(str(value))) for index, value in enumerate(values)]


# ---------------------------------------------------------------------------
# Tailles de rang
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "total,expected_s",
    [
        (1, 1),  # au moins un S, toujours
        (7, 1),
        (10, 1),
        (11, 2),
        (20, 2),
        (100, 10),
    ],
)
def test_taille_cible_du_rang_s(total, expected_s):
    """S_target = max(1, ceil(total × 10 %)) (spec §27.2)."""
    assert compute_rank_sizes(total)[0] == expected_s


@pytest.mark.parametrize(
    "total,expected",
    [
        (10, [1, 3, 2, 2, 2]),  # spec §27.4
        (11, [2, 3, 2, 2, 2]),  # spec §27.4
        (3, [1, 1, 1, 0, 0]),  # spec §27.6 : rangs vides autorisés
        (1, [1, 0, 0, 0, 0]),
        (2, [1, 1, 0, 0, 0]),
        (7, [1, 2, 2, 1, 1]),
        (20, [2, 5, 5, 4, 4]),
        (100, [10, 23, 23, 22, 22]),
    ],
)
def test_repartition_des_rangs(total, expected):
    """Le reste favorise les rangs les plus élevés (spec §27.4)."""
    assert compute_rank_sizes(total) == expected
    assert sum(compute_rank_sizes(total)) == total


def test_aucun_item():
    assert compute_rank_sizes(0) == [0, 0, 0, 0, 0]
    assert assign_ranks([]) == {}


# ---------------------------------------------------------------------------
# Exemples de référence de la spécification
# ---------------------------------------------------------------------------


def test_exemple_deterministe_spec_28():
    """Spec §28 : 10 items sans égalité."""
    groups = rank_groups(scores(8.90, 8.50, 8.30, 8.10, 7.90, 7.40, 7.00, 6.50, 6.00, 5.00))
    assert groups[1] == ["I1"]
    assert groups[2] == ["I2", "I3", "I4"]
    assert groups[3] == ["I5", "I6"]
    assert groups[4] == ["I7", "I8"]
    assert groups[5] == ["I9", "I10"]


def test_exemple_avec_egalite_spec_29():
    """Spec §29 : I1 et I2 ex æquo traversent la frontière S, tous deux en S."""
    groups = rank_groups(scores(8.90, 8.90, 8.20, 8.00, 7.80, 7.50, 7.00, 6.80, 6.20, 5.50))
    assert groups[1] == ["I1", "I2"]
    assert groups[2] == ["I3", "I4"]
    assert groups[3] == ["I5", "I6"]
    assert groups[4] == ["I7", "I8"]
    assert groups[5] == ["I9", "I10"]


def test_egalite_frontiere_s_spec_27_3():
    """Spec §27.3 : S_target = 2 mais B et C sont ex æquo -> S contient A, B, C."""
    items = [
        ("A", Decimal("8.71")),
        ("B", Decimal("8.50")),
        ("C", Decimal("8.50")),
        ("D", Decimal("8.20")),
    ]
    # 4 items -> S_target = 1 ; on force le cas de la spec avec 11 items fictifs
    # en vérifiant directement la règle sur la frontière calculée.
    padded = items + [(f"X{i}", Decimal("1.00")) for i in range(7)]
    assert compute_rank_sizes(len(padded))[0] == 2
    groups = rank_groups(padded)
    assert groups[1] == ["A", "B", "C"]


def test_tous_les_scores_identiques_spec_30():
    """Spec §30 : une égalité parfaite n'est jamais cassée -> tout en S."""
    items = [(f"I{i}", Decimal("6.00")) for i in range(1, 21)]
    groups = rank_groups(items)
    assert len(groups[1]) == 20
    assert groups[2] == groups[3] == groups[4] == groups[5] == []


# ---------------------------------------------------------------------------
# Égalités sur chaque frontière (spec §60)
# ---------------------------------------------------------------------------


def test_egalite_frontiere_a_b():
    """10 items, I4 et I5 ex æquo à la frontière A/B -> les deux en A."""
    groups = rank_groups(scores(9.0, 8.5, 8.2, 8.0, 8.0, 7.0, 6.5, 6.0, 5.5, 5.0))
    assert groups[1] == ["I1"]
    assert groups[2] == ["I2", "I3", "I4", "I5"]
    # A déborde : B contient mécaniquement moins d'items (spec §27.5).
    assert groups[3] == ["I6"]
    assert groups[4] == ["I7", "I8"]
    assert groups[5] == ["I9", "I10"]


def test_egalite_frontiere_b_c():
    """I6 et I7 ex æquo à la frontière B/C -> les deux en B."""
    groups = rank_groups(scores(9.0, 8.5, 8.2, 8.0, 7.5, 7.0, 7.0, 6.0, 5.5, 5.0))
    assert groups[1] == ["I1"]
    assert groups[2] == ["I2", "I3", "I4"]
    assert groups[3] == ["I5", "I6", "I7"]
    assert groups[4] == ["I8"]
    assert groups[5] == ["I9", "I10"]


def test_egalite_frontiere_c_d():
    """I8 et I9 ex æquo à la frontière C/D -> les deux en C."""
    groups = rank_groups(scores(9.0, 8.5, 8.2, 8.0, 7.5, 7.0, 6.5, 6.0, 6.0, 5.0))
    assert groups[1] == ["I1"]
    assert groups[2] == ["I2", "I3", "I4"]
    assert groups[3] == ["I5", "I6"]
    assert groups[4] == ["I7", "I8", "I9"]
    assert groups[5] == ["I10"]


def test_deux_items_de_meme_score_sont_toujours_dans_le_meme_rang():
    """Invariant global : aucun couple ex æquo réparti dans deux rangs (spec §27.5)."""
    values = [9.0, 9.0, 8.0, 8.0, 8.0, 7.0, 7.0, 6.0, 6.0, 6.0, 5.0, 5.0, 4.0, 3.0, 2.0]
    items = scores(*values)
    assignment = assign_ranks(items)
    by_score: dict[Decimal, set[int]] = {}
    for key, score in items:
        by_score.setdefault(score, set()).add(assignment[key])
    for score, ranks in by_score.items():
        assert len(ranks) == 1, f"score {score} réparti sur les rangs {ranks}"


# ---------------------------------------------------------------------------
# Petites Tier Lists
# ---------------------------------------------------------------------------


def test_un_seul_item():
    groups = rank_groups(scores(4.20))
    assert groups[1] == ["I1"]
    assert groups[2] == groups[3] == groups[4] == groups[5] == []


def test_deux_items():
    groups = rank_groups(scores(8.0, 3.0))
    assert groups[1] == ["I1"]
    assert groups[2] == ["I2"]
    assert groups[3] == groups[4] == groups[5] == []


def test_trois_items_spec_27_6():
    groups = rank_groups(scores(8.0, 6.0, 3.0))
    assert groups[1] == ["I1"]
    assert groups[2] == ["I2"]
    assert groups[3] == ["I3"]
    assert groups[4] == []
    assert groups[5] == []


@pytest.mark.parametrize("total", [1, 2, 3, 7, 10, 11, 20, 100])
def test_tous_les_items_sont_classes_une_seule_fois(total):
    items = [(f"I{i}", Decimal(total - i)) for i in range(total)]
    groups = rank_groups(items)
    placed = [key for rank in groups.values() for key in rank]
    assert sorted(placed) == sorted(key for key, _ in items)
    assert len(placed) == total
    assert len(groups[1]) >= 1


def test_ordre_interne_par_score_decroissant():
    """Spec §27.7 : à l'intérieur d'un rang, tri par score décroissant."""
    groups = rank_groups(scores(9.0, 8.5, 8.4, 8.3, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0))
    assert groups[2] == ["I2", "I3", "I4"]


def test_ex_aequo_ordonnes_par_cle_de_maniere_deterministe():
    """L'ordre secondaire est stable mais ne traduit aucune différence de score."""
    items = [("B", Decimal("5")), ("A", Decimal("5")), ("C", Decimal("5"))]
    assert rank_groups(items)[1] == ["A", "B", "C"]


def test_fonctionne_avec_des_scores_entiers():
    """Le pipeline réel compare des numérateurs entiers exacts."""
    groups = rank_groups([("I1", 120), ("I2", 100), ("I3", 100), ("I4", 50)])
    assert groups[1] == ["I1"]
    assert groups[2] == ["I2", "I3"]
