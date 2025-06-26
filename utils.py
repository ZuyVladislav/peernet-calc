# utils.py
"""
Утилиты для peernet-calc:
* validators  — быстрые проверки диапазонов и логики.
* export      — запись pandas-DataFrame в CSV / XLSX / PDF.
"""

from __future__ import annotations
from pathlib import Path
from typing import Tuple

import pandas as pd

# ----------------------------------------------------------------------
# 1. Validators
# ----------------------------------------------------------------------
class ValidationError(ValueError):
    """Ошибки проверки аргументов."""


def validate_params(n: int, k: int, j: int, m: int) -> None:
    """
    Проверяет допустимость входных параметров.

    * n  – число узлов в сети  (>= 3);
    * k  – число промежуточных узлов (<= n-2);
    * j  – длина каскада (<= n);
    * m  – число скомпрометированных узлов (<= n-2).

    Поднимает ValidationError, если что-то не так.
    """
    if n < 3:
        raise ValidationError("n должно быть ≥ 3.")
    if not (1 <= k <= n - 2):
        raise ValidationError("k должно быть в диапазоне 1‥n-2.")
    if not (1 <= j <= n):
        raise ValidationError("j должно быть 1‥n.")
    if not (0 <= m <= n - 2):
        raise ValidationError("m должно быть 0‥n-2.")
    if j < k:  # пример дополнительной бизнес-логики
        raise ValidationError("Для каскада j нельзя брать меньше k.")


# ----------------------------------------------------------------------
# 2. Export helpers
# ----------------------------------------------------------------------
def _prepare_path(path: str | Path, ext: str) -> Path:
    path = Path(path)
    if path.suffix.lower() != f".{ext}":
        path = path.with_suffix(f".{ext}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def to_csv(df: pd.DataFrame, path: str | Path) -> Path:
    """Сохраняет DataFrame в CSV (UTF-8)."""
    path = _prepare_path(path, "csv")
    df.to_csv(path, index=False)
    return path


def to_xlsx(df: pd.DataFrame, path: str | Path) -> Path:
    """Сохраняет DataFrame в XLSX (openpyxl)."""
    path = _prepare_path(path, "xlsx")
    df.to_excel(path, index=False, engine="openpyxl")
    return path


def to_pdf(df: pd.DataFrame, path: str | Path, title: str = "peernet-calc") -> Path:
    """
    Быстрый экспорт в PDF через matplotlib.
    Каждый столбец – в отдельной колонке таблицы.
    """
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    path = _prepare_path(path, "pdf")
    with PdfPages(path) as pdf:
        fig, ax = plt.subplots(figsize=(8.3, 11.7))  # A4 портрет
        ax.axis("off")
        tbl = ax.table(
            cellText=df.values,
            colLabels=df.columns,
            loc="center",
            cellLoc="center",
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8)
        tbl.scale(1, 1.2)
        ax.set_title(title, pad=20, fontsize=12, weight="bold")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
    return path


# ----------------------------------------------------------------------
# convenience: экспорт одним вызовом
# ----------------------------------------------------------------------
def export(
    df: pd.DataFrame,
    basepath: str | Path,
    formats: Tuple[str, ...] = ("csv", "xlsx"),
) -> None:
    """
    Экспортирует DataFrame во все указанные форматы.

    `formats`  – кортеж из {'csv', 'xlsx', 'pdf'}.
    """
    for fmt in formats:
        fmt = fmt.lower()
        if fmt == "csv":
            to_csv(df, basepath)
        elif fmt == "xlsx":
            to_xlsx(df, basepath)
        elif fmt == "pdf":
            to_pdf(df, basepath)
        else:
            raise ValueError(f"Неизвестный формат {fmt}")
