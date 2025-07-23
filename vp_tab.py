"""vp_tab.py — вкладка «ВП / ВУС» для проекта PeerNet‑Calc
Полностью рабочая версия (17 июля 2025).

Функциональность
────────────────
• Одновременный вывод графиков для F₁ (Tor‑тип), F₃ (без повторений), F₄ (с повторениями).
• Переключатель «ВП / ВУС».
• Выбор переменной X (n или m) и диапазона её изменения.
• Таблица значений (X + столбцы по формулам) под превью‑графиком.
• Логарифмический масштаб Y, зум (Ctrl + колёсико) и кнопки ±.
• Работает как с PySide6, так и с PyQt5 (fallback).
"""

from __future__ import annotations
import os

# Matplotlib backend нужно объявить до первого импорта pyplot
os.environ.setdefault("MPLBACKEND", "Qt5Agg")

# ──────────────── Qt‑импорт: PySide6 → PyQt5 fallback ────────────────
try:
    from PySide6.QtWidgets import (
        QWidget, QGridLayout, QLabel, QSpinBox, QPushButton, QComboBox,
        QCheckBox, QGroupBox, QMessageBox, QRadioButton, QDialog,
        QVBoxLayout, QToolButton, QHBoxLayout, QTableWidget,
        QTableWidgetItem
    )
    from PySide6.QtCore import Qt
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvasQTAgg as Canvas, NavigationToolbar2QT,
    )
except ImportError:          # PyQt5 fallback
    from PyQt5.QtWidgets import (
        QWidget, QGridLayout, QLabel, QSpinBox, QPushButton, QComboBox,
        QCheckBox, QGroupBox, QMessageBox, QRadioButton, QDialog,
        QVBoxLayout, QToolButton, QHBoxLayout, QTableWidget,
        QTableWidgetItem
    )
    from PyQt5.QtCore import Qt
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvasQTAgg as Canvas, NavigationToolbar2QT,
    )

import matplotlib.pyplot as plt
import core    # локальный модуль с математикой


# ═══════════════ Формулы вероятности перехвата ════════════════
def _vp_f1_tor(m: int, n: int, j: int) -> float:
    """F₁ — Tor‑тип. Возвращает вероятность перехвата (ВП)."""
    total = core.f_tor(n, j) if n >= 3 else 0
    if total == 0:
        return 0.0
    if m == 0:                       # нет скомпрометированных узлов
        safe = total
    elif n - m < 2:                  # остались только A и B
        safe = 0
    else:
        safe = core.f_tor(n - m, j)
    return (total - safe) / total


# core.vp(...) возвращает вероятность УСПЕХА (ВУС); инвертируем → ВП
FORMULAS: dict[str, callable] = {
    "F₁ Tor‑тип":        _vp_f1_tor,                                # собственная формула
    "F₃ без повторений": lambda m, n, j: core.vp(m, n, j, False),   # selector=False
    "F₄ с повторениями": lambda m, n, j: core.vp(m, n, j, True),    # selector=True
}

COLORS = {
    "F₁ Tor‑тип":        "tab:red",
    "F₃ без повторений": "tab:brown",
    "F₄ с повторениями": "tab:blue",
}


# ═══════════════ Вспомогательное окно большого графика ═══════════════
class PlotWindow(QDialog):
    """Окно с увеличенным графиком и управлением зумом."""

    def __init__(self, fig, ax, *, w: int, h: int, title: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(title)
        self.resize(int(w * 100), int(h * 100))

        self.canvas = Canvas(fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        plus_btn = QToolButton(text="+")
        minus_btn = QToolButton(text="−")
        plus_btn.clicked.connect(lambda: self._zoom(ax, 0.8))
        minus_btn.clicked.connect(lambda: self._zoom(ax, 1.25))
        hl = QHBoxLayout(); hl.addWidget(plus_btn); hl.addWidget(minus_btn); hl.addStretch()

        vb = QVBoxLayout(self)
        vb.addWidget(self.toolbar)
        vb.addLayout(hl)
        vb.addWidget(self.canvas)

        # зум колёсиком с Ctrl
        self.canvas.mpl_connect("scroll_event", lambda ev: self._on_scroll(ev, ax))

    # ───────── helpers ─────────
    @staticmethod
    def _scaled(lims, c, s):
        lo, hi = lims
        return c + (lo - c) * s, c + (hi - c) * s

    def _zoom(self, ax, s):
        cx = sum(ax.get_xlim()) / 2
        cy = sum(ax.get_ylim()) / 2
        ax.set_xlim(*self._scaled(ax.get_xlim(), cx, s))
        ax.set_ylim(*self._scaled(ax.get_ylim(), cy, s))
        self.canvas.draw_idle()

    def _on_scroll(self, ev, ax):
        qev = ev.guiEvent
        if not qev or not (qev.modifiers() & Qt.ControlModifier):
            return
        scale = 0.8 if ev.button == "up" else 1.25
        ax.set_xlim(*self._scaled(ax.get_xlim(), ev.xdata, scale))
        ax.set_ylim(*self._scaled(ax.get_ylim(), ev.ydata, scale))
        self.canvas.draw_idle()


# ═════════════════════════════ VPTab ═══════════════════════════════
class VPTab(QWidget):
    """Вкладка «ВП / ВУС» с множественным графиком и таблицей значений."""

    def __init__(self):
        super().__init__()

        # превью‑график
        self.fig_prev, self.ax_prev = plt.subplots(figsize=(6, 4))
        self.canvas_prev = Canvas(self.fig_prev)

        grid = QGridLayout(self)
        self._build_single_block(grid)
        grid.addWidget(self.canvas_prev, 1, 0, 3, 6)
        self._build_plot_block(grid)

    # ──────────────────── единичный расчёт ───────────────────────
    def _build_single_block(self, g: QGridLayout):
        self.cmb_formula = QComboBox(); self.cmb_formula.addItems(FORMULAS.keys())
        self.spin_n = QSpinBox(minimum=3, maximum=300, value=10)
        self.spin_j = QSpinBox(minimum=1, maximum=299, value=3)
        self.spin_m = QSpinBox(minimum=0, maximum=299, value=1)

        self.rb_vp = QRadioButton("ВП"); self.rb_vp.setChecked(True)
        self.rb_vus = QRadioButton("ВУС")

        btn = QPushButton("Рассчитать"); btn.clicked.connect(self._single_calc)
        self.lbl_single = QLabel("…")

        g.addWidget(QLabel("Формула"), 0, 0)
        g.addWidget(self.cmb_formula,  0, 1)
        g.addWidget(self.rb_vp,        0, 2)
        g.addWidget(self.rb_vus,       0, 3)
        g.addWidget(QLabel("n"),       0, 4); g.addWidget(self.spin_n, 0, 5)
        g.addWidget(QLabel("j"),       0, 6); g.addWidget(self.spin_j, 0, 7)
        g.addWidget(QLabel("m"),       0, 8); g.addWidget(self.spin_m, 0, 9)
        g.addWidget(btn,               0, 10)
        g.addWidget(self.lbl_single,   0, 11, 1, 2)

    def _single_calc(self):
        try:
            n, j, m = self.spin_n.value(), self.spin_j.value(), self.spin_m.value()
            vp = FORMULAS[self.cmb_formula.currentText()](m, n, j)
            val = vp if self.rb_vp.isChecked() else 1.0 - vp
            typ = "ВП" if self.rb_vp.isChecked() else "ВУС"
            self.lbl_single.setText(f"<b>{self.cmb_formula.currentText()} — {typ}</b> = {val:.4f}")
        except Exception as e:
            self._err(str(e))

    # ───────── блок график / таблица ─────────
    def _build_plot_block(self, g: QGridLayout):
        grp = QGroupBox("График / значения"); gl = QGridLayout(grp)

        # чекбоксы формул
        self.chk_form: list[QCheckBox] = []
        for i, name in enumerate(FORMULAS.keys()):
            cb = QCheckBox(name); cb.setChecked(True)
            self.chk_form.append(cb)
            gl.addWidget(cb, i, 0, 1, 2)

        # выбор X‑переменной
        gl.addWidget(QLabel("X‑переменная"), len(FORMULAS), 0)
        self.cmb_x = QComboBox(); self.cmb_x.addItems(["n", "m"])
        self.cmb_x.currentIndexChanged.connect(self._toggle_fixed_inputs)
        gl.addWidget(self.cmb_x, len(FORMULAS), 1)

        row = len(FORMULAS) + 1
        # диапазон X
        self.spin_start = QSpinBox(minimum=1, maximum=300, value=10)
        self.spin_stop  = QSpinBox(minimum=2, maximum=300, value=20)
        self.spin_step  = QSpinBox(minimum=1, maximum=100, value=1)
        for label, spin in (("Start", self.spin_start), ("Stop", self.spin_stop), ("Step", self.spin_step)):
            gl.addWidget(QLabel(label), row, 0)
            gl.addWidget(spin,          row, 1)
            row += 1

        # фиксированные значения
        self.fix_n = QSpinBox(minimum=3, maximum=300, value=10)
        self.fix_j = QSpinBox(minimum=1, maximum=299, value=3)
        self.fix_m = QSpinBox(minimum=0, maximum=299, value=1)
        for label, spin in (("fix n", self.fix_n), ("fix j", self.fix_j), ("fix m", self.fix_m)):
            gl.addWidget(QLabel(label), row, 0)
            gl.addWidget(spin,          row, 1)
            row += 1

        # размеры фигуры
        self.fig_w = QSpinBox(minimum=4, maximum=20, value=10)
        self.fig_h = QSpinBox(minimum=3, maximum=15, value=7)
        for label, spin in (("width", self.fig_w), ("height", self.fig_h)):
            gl.addWidget(QLabel(label), row, 0)
            gl.addWidget(spin,          row, 1)
            row += 1

        # логарифмическая шкала
        self.chk_log = QCheckBox("Log Y"); self.chk_log.setChecked(False)
        gl.addWidget(self.chk_log, row, 0, 1, 2); row += 1

        # кнопка построения графика
        btn_plot = QPushButton("Построить график"); btn_plot.clicked.connect(self._plot)
        gl.addWidget(btn_plot, row, 0, 1, 2); row += 1

        # таблица значений
        self.tbl = QTableWidget()
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        gl.addWidget(self.tbl, row, 0, 4, 2)

        g.addWidget(grp, 1, 6, 3, 2)
        self._toggle_fixed_inputs()   # начальное состояние

    # ───────── helpers ─────────
    def _toggle_fixed_inputs(self):
        x_is_n = self.cmb_x.currentText() == "n"
        self.fix_n.setDisabled(x_is_n)
        self.fix_m.setDisabled(not x_is_n)
        self.fix_n.setSpecialValueText("—" if x_is_n else "")
        self.fix_m.setSpecialValueText("—" if not x_is_n else "")

    # ───────── построение графика ─────────
    def _plot(self):
        self.ax_prev.clear()
        s, e, st = self.spin_start.value(), self.spin_stop.value(), self.spin_step.value()
        if e < s or st <= 0:
            return self._err("Диапазон X неверен")

        rng = list(range(s, e + 1, st))
        x_is_n = self.cmb_x.currentText() == "n"
        fn, fj, fm = self.fix_n.value(), self.fix_j.value(), self.fix_m.value()
        if x_is_n:
            rng = [x for x in rng if x >= fj + 2]    # условие существования маршрутов
        if not rng:
            return self._err("Нет допустимых X")

        series: list[tuple[str, list[int], list[float]]] = []
        for cb in self.chk_form:
            if not cb.isChecked():
                continue
            name = cb.text()
            fun = FORMULAS[name]
            xs, ys = [], []
            for x in rng:
                n, j, m = (x, fj, fm) if x_is_n else (fn, fj, x)
                try:
                    y = fun(m, n, j)
                except Exception:
                    y = 0.0
                xs.append(x)
                ys.append(1.0 - y if self.rb_vus.isChecked() else y)
            series.append((name, xs, ys))

        if not series:
            return self._err("Ни одна формула не выбрана")

        title = f"j = {fj}" if x_is_n else f"n = {fn}"
        self._fill_table(rng, series)
        self._draw(self.ax_prev, series, title)
        self.canvas_prev.draw_idle()

        # отдельное окно
        w, h = self.fig_w.value(), self.fig_h.value()
        fig_big, ax_big = plt.subplots(figsize=(w, h))
        self._draw(ax_big, series, title)
        PlotWindow(fig_big, ax_big, w=w, h=h, title=title, parent=self).show()

    def _fill_table(self, xs: list[int], series):
        headers = [self.cmb_x.currentText()] + [name for name, _, _ in series]
        self.tbl.setColumnCount(len(headers))
        self.tbl.setHorizontalHeaderLabels(headers)
        self.tbl.setRowCount(len(xs))
        # X‑значения
        for row, x in enumerate(xs):
            self.tbl.setItem(row, 0, QTableWidgetItem(str(x)))
        # значения формул
        for col, (_, _, ys) in enumerate(series, start=1):
            for row, val in enumerate(ys):
                self.tbl.setItem(row, col, QTableWidgetItem(f"{val:.6f}"))
        self.tbl.resizeColumnsToContents()

    def _draw(self, ax, data, title: str):
        ax.clear()
        ax.set_title(title)
        ax.set_xlabel(self.cmb_x.currentText())
        ax.set_ylabel("ВП" if self.rb_vp.isChecked() else "ВУС")
        for name, xs, ys in data:
            ax.plot(xs, ys, "o-", label=name, color=COLORS.get(name, "black"))
        ax.grid(True, ls=":")
        if self.chk_log.isChecked():
            ax.set_yscale("log")
        ax.legend()

    def _err(self, msg: str):
        QMessageBox.critical(self, "Ошибка", msg, QMessageBox.Ok)
