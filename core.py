"""
core.py — все расчётные функции для peernet-calc.
Python ≥ 3.10
"""
from __future__ import annotations

from functools import lru_cache
from math import comb, prod
from typing import Callable, Final, overload

# ───────────────────────────────
# 1. TOR / I2P (формулы 1–2)
# ───────────────────────────────
def f_tor(n: int, k: int) -> int:
    """F_Tor(n,k) = ∏_{i=1..k}(n-i-1). k ≤ n-2 → ≥ 0, иначе 0."""
    if k < 0 or n < 2 or k > n - 2:
        return 0
    return prod(n - i - 1 for i in range(1, k + 1))


def f_i2p(n: int, k: int) -> int:
    """F_I2P = F_Tor² (входящий и исходящий тоннель)."""
    val = f_tor(n, k)
    return val * val


# ───────────────────────────────
# 2. F₁(n,j) — без повторов
# ───────────────────────────────
def f1_no_rep(n: int, j: int) -> int:
    """Формула из §3.2: уникальные узлы."""
    if n < j:
        return 0
    if j == 1:
        return max(n - 2, 0)
    if j == 2:
        return (n - 1) + (n - 2) ** 2
    if j == 3:
        return (n - 2) * ((n - 1) + (n - 2) + (n - 2) * (n - 3))
    if 4 <= j <= n:
        inner = (n - 1) + (j - 2) * (n - 2) + (n - 2) * (n - j)
        return inner * prod(n - m for m in range(2, j))
    raise ValueError("некорректные n или j для F₁")


# ───────────────────────────────
# 3. F₂(j,n) — c повторами
# ───────────────────────────────
def f2_rep(j: int, n: int) -> int:
    """Формула из §3.3 (c повторами узлов)."""
    return ((n - 1) ** (j + 1) - (-1) ** (j + 1)) // n


# ───────────────────────────────
# 4.  Перехват / успешность
# ───────────────────────────────
def _total_routes(
    n: int,
    j: int,
    selector: bool | Callable[[int, int], int],
) -> int:
    """Возвращает общее число маршрутов.

    selector:
        • True  → повторы разрешены (F₂)
        • False → без повторов (F₁)
        • callable(n,j) → пользовательская формула
    """
    if callable(selector):
        return selector(n, j)
    return f2_rep(j, n) if selector else f1_no_rep(n, j)


def _safe_routes(
    n: int,
    j: int,
    m: int,
    selector: bool | Callable[[int, int], int],
) -> int:
    """Маршруты, НЕ проходящие через m скомпрометированных узлов."""
    if m == 0:
        return _total_routes(n, j, selector)
    if n - m < 2:          # остались только A и B
        return 0
    return _total_routes(n - m, j, selector)


def p_m(
    n: int,
    j: int,
    m: int,
    selector: bool | Callable[[int, int], int] = True,
) -> int:
    """Количество маршрутов, проходящих ≥ 1 из m узлов."""
    total = _total_routes(n, j, selector)
    safe  = _safe_routes(n, j, m, selector)
    return max(total - safe, 0)


def vp(
    m: int,
    n: int,
    j: int,
    selector: bool | Callable[[int, int], int] = True,
) -> float:
    """Вероятность перехвата."""
    total = _total_routes(n, j, selector)
    return p_m(n, j, m, selector) / total if total else 0.0


def vus(
    m: int,
    n: int,
    j: int,
    selector: bool | Callable[[int, int], int] = True,
) -> float:
    """Вероятность успешного соединения."""
    return 1.0 - vp(m, n, j, selector)


# ───────────────────────────────
# 5.  MSS-сценарии (формулы 7-8)
# ───────────────────────────────
@lru_cache(maxsize=None)
def _a(j: int, k: int, n: int) -> int:
    """A(j,k,n) — вспомогательная рекурсия (формула 8)."""
    if j == 1:
        return 1
    if j == 2:
        return comb(n - 1, k) + comb(n - 2, k)
    return (
        comb(n - 2, k - 1) * comb(n - 1, k) * _a(j - 2, k, n)
        + comb(n - 2, k) * _a(j - 1, k, n)
    )


@lru_cache(maxsize=None)
def n_mss(j: int, k: int, n: int) -> int:
    """N(j,k,n) — полная формула 7."""
    if j == 1:
        return comb(n - 2, k - 1)
    return n_mss(j - 1, k, n) ** k // _a(j - 1, k, n) * _a(j, k, n)


# ───────────────────────────────
# 6.  Демонстрация
# ───────────────────────────────
if __name__ == "__main__":
    n, k, j, m = 7, 3, 4, 2

    print(f"Tor  (n={n},k={k})  →", f_tor(n, k))
    print(f"I2P  (n={n},k={k})  →", f_i2p(n, k))
    print(f"F1   (n={n},j={j})  →", f1_no_rep(n, j))
    print(f"F2   (j={j},n={n})  →", f2_rep(j, n))

    # пример словаря «формул» как в routes_tab
    FORMULAS_EX = {
        "F₁": f1_no_rep,
        "F₂": f2_rep,          # условно
    }
    sel_func = FORMULAS_EX["F₁"]

    print("\n— Перехват / успешность —")
    print("VP old-style  (repeat=True) →", vp(m, n, j, True))
    print("VP func-style (F₁)          →", vp(m, n, j, sel_func))
    print("VUS func-style              →", vus(m, n, j, sel_func))

    print("\n— MSS —")
    print(f"N_MSS(j={j},k={k}) →", n_mss(j, k, n))
