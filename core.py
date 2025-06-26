"""
core.py — полный набор расчётных функций для peernet-calc.
Python ≥ 3.10
"""
from __future__ import annotations

from functools import lru_cache
from math import comb, prod
from typing import Final

# ───────────────────────────────
# 1. TOR / I2P (формулы 1–2)
# ───────────────────────────────
def f_tor(n: int, k: int) -> int:
    """F_Tor(n,k) = ∏_{i=1..k}(n-i-1).  k ≤ n-2 → >=0, иначе 0."""
    if k < 0 or n < 2 or k > n - 2:
        return 0
    return prod(n - i - 1 for i in range(1, k + 1))


def f_i2p(n: int, k: int) -> int:
    """F_I2P — тот же продукт, но² (входной и выходной туннели)."""
    routes = f_tor(n, k)
    return routes * routes


# ───────────────────────────────
# 2. F₁(n,j) — без повторов (формула 3)
# ───────────────────────────────
def f1_no_rep(n: int, j: int) -> int:
    if n < j:
        return 0
    if j == 1 and n >= 3:
        return n - 2
    if j == 2 and n >= 2:
        return (n - 1) + (n - 2) ** 2
    if j == 3 and n >= 3:
        return (n - 2) * ((n - 1) + (n - 2) + (n - 2)*(n - 3))
    if 4 <= j <= n:
        inner = (n - 1) + (j - 2) * (n - 2) + (n - 2) * (n - j)
        return inner * prod(n - m for m in range(2, j))
    raise ValueError("некорректные n или j для F₁")


# ───────────────────────────────
# 3. F₂(j,n) — с повторами (формула 4)
# ───────────────────────────────
def f2_rep(j: int, n: int) -> int:
    return ((n - 1) ** (j + 1) - (-1) ** (j + 1)) // n


# ───────────────────────────────
# 4.  Перехват / успешность
# ───────────────────────────────
def _total_routes(n: int, j: int, repeat: bool) -> int:
    return f2_rep(j, n) if repeat else f1_no_rep(n, j)


def _safe_routes(n: int, j: int, m: int, repeat: bool) -> int:
    """
    Кол-во маршрутов, *избегающих* m скомпрометированных узлов.
    Идея из §3.4: убрать m вершин → осталось n-m узлов.
    """
    if m == 0:
        return _total_routes(n, j, repeat)
    if n - m < 2:        # кроме A и B ничего не осталось
        return 0
    return _total_routes(n - m, j, repeat)


def p_m(n: int, j: int, m: int, repeat: bool = True) -> int:
    """
    Pₘ(n,j) — маршруты, проходящие *хотя бы через один*
    из m скомпрометированных узлов: Total − Safe.
    """
    total = _total_routes(n, j, repeat)
    safe = _safe_routes(n, j, m, repeat)
    return max(total - safe, 0)


def vp(m: int, n: int, j: int, repeat: bool = True) -> float:
    """Вероятность перехвата (формула 5)."""
    total = _total_routes(n, j, repeat)
    intercepted = p_m(n, j, m, repeat)
    return intercepted / total if total else 0.0


def vus(m: int, n: int, j: int, repeat: bool = True) -> float:
    """Вероятность успешного соединения (формула 6)."""
    return 1.0 - vp(m, n, j, repeat)


# ───────────────────────────────
# 5.  MSS-сценарии  (формулы 7-8)
# ───────────────────────────────
@lru_cache(maxsize=None)
def _a(j: int, k: int, n: int) -> int:
    """A(j,k,n) с мемоизацией (формула 8)."""
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
    """N(j,k,n) — рекурсия по формуле 7."""
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
    print(f"P_m  (m={m})        →", p_m(n, j, m))
    print(f"VP   (m={m})        →", vp(m, n, j))
    print(f"VUS  (m={m})        →", vus(m, n, j))
    print(f"N_MSS(j={j},k={k})  →", n_mss(j, k, n))
