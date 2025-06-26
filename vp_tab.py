# vp_tab.py – вкладка «ВП / ВНС» (VP / VUS)
from __future__ import annotations
import os
os.environ["MPLBACKEND"] = "Qt5Agg"

from PyQt5.QtWidgets import (
    QWidget, QGridLayout, QLabel, QSpinBox, QComboBox,
    QPushButton, QRadioButton, QGroupBox, QMessageBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
import matplotlib.pyplot as plt

import core
from routes_tab import FORMULAS                         # F₁…F₄

# ────────────────────────────────────────────────────────────────────
class VPTab(QWidget):
    """Вкладка «ВП / ВНС»: одиночное значение + гибкий график."""

    def __init__(self) -> None:
        super().__init__()

        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        self.canvas       = Canvas(self.fig)

        g = QGridLayout(self)
        self._build_single(g)
        self._build_plot(g)
        g.addWidget(self.canvas, 9, 0, 1, 4)

    # ---------- 1. одиночный расчёт ---------------------------------
    def _build_single(self, g: QGridLayout) -> None:
        self.cmb_formula_single = QComboBox(); self.cmb_formula_single.addItems(FORMULAS)
        self.spin_n = QSpinBox(minimum=3, maximum=300, value=7)
        self.spin_j = QSpinBox(minimum=1, maximum=299, value=3)
        self.spin_m = QSpinBox(minimum=0, maximum=298, value=2)
        self.cmb_mode_single = QComboBox(); self.cmb_mode_single.addItems(["Вероятность перехвата", "Вероятность успешного соединения"])
        self.lbl_single = QLabel("—")
        btn = QPushButton("Рассчитать"); btn.clicked.connect(self._calc_single)

        g.addWidget(QLabel("Формула"), 0, 0); g.addWidget(self.cmb_formula_single, 0, 1)
        g.addWidget(QLabel("Количество узлов в сети (n)"),       1, 0); g.addWidget(self.spin_n, 1, 1)
        g.addWidget(QLabel("Количество промежуточных узлов (j)"),       2, 0); g.addWidget(self.spin_j, 2, 1)
        g.addWidget(QLabel("Количество скомпрометрированных узлов (m)"),       3, 0); g.addWidget(self.spin_m, 3, 1)
        g.addWidget(self.cmb_mode_single, 4, 0, 1, 2)
        g.addWidget(btn, 5, 0, 1, 2)
        g.addWidget(self.lbl_single, 6, 0, 1, 2)

    def _calc_single(self) -> None:
        n, j, m = self.spin_n.value(), self.spin_j.value(), self.spin_m.value()
        if m > n-2:
            self._err(f"m = {m}  >  n-2 (={n-2})"); return

        name   = self.cmb_formula_single.currentText()
        repeat = name.startswith("F₄")
        total  = FORMULAS[name](n, j)
        vp     = core.p_m(n, j, m, repeat) / total if total else 0.0
        res    = vp if self.cmb_mode_single.currentText() == "VP" else (1 - vp)
        self.lbl_single.setText(f"{self.cmb_mode_single.currentText()} = {res:.6f}")

    # ---------- 2. блок «график» ------------------------------------
    def _build_plot(self, g: QGridLayout) -> None:
        grp = QGroupBox("График"); gl = QGridLayout(grp)

        # выбор формулы именно для графика
        self.cmb_formula_plot = QComboBox(); self.cmb_formula_plot.addItems(FORMULAS)
        gl.addWidget(QLabel("Формула"), 0, 0); gl.addWidget(self.cmb_formula_plot, 0, 1, 1, 2)

        # переключатели оси X
        self.rb_n = QRadioButton("Количество узлов в сети (n)"); self.rb_n.setChecked(True)
        self.rb_j = QRadioButton("Количество промежуточных узлов (j)")
        self.rb_m = QRadioButton("Количество скомпрометированных узлов (m)")
        for i,rb in enumerate((self.rb_n, self.rb_j, self.rb_m), 1):
            rb.toggled.connect(self._sync_fix_state)
            gl.addWidget(rb, 1, i)
        gl.addWidget(QLabel("Изменять"), 1, 0)

        # диапазон
        self.start = QSpinBox(minimum=1, maximum=300, value=3)
        self.stop  = QSpinBox(minimum=2, maximum=300, value=30)
        self.step  = QSpinBox(minimum=1, maximum=50,  value=1)
        gl.addWidget(QLabel("Начало"),2,0); gl.addWidget(self.start,2,1)
        gl.addWidget(QLabel("Конец"), 3,0); gl.addWidget(self.stop,3,1)
        gl.addWidget(QLabel("Шаг"),   4,0); gl.addWidget(self.step,4,1)

        # фикс-значения
        self.fix_n = self._spin_fix(10);  self.fix_j = self._spin_fix(3);  self.fix_m = self._spin_fix(1)
        gl.addWidget(QLabel("Фикс n"),5,0); gl.addWidget(self.fix_n,5,1)
        gl.addWidget(QLabel("Фикс j"),6,0); gl.addWidget(self.fix_j,6,1)
        gl.addWidget(QLabel("Фикс m"),7,0); gl.addWidget(self.fix_m,7,1)

        # VP / VUS для графика
        self.cmb_mode_plot = QComboBox(); self.cmb_mode_plot.addItems(["Вероятность перехвата", "Вероятность успешного соединения"])
        gl.addWidget(self.cmb_mode_plot, 8, 0, 1, 2)

        btn = QPushButton("Построить"); btn.clicked.connect(self._plot)
        gl.addWidget(btn, 9, 0, 1, 3)

        g.addWidget(grp, 0, 2, 9, 2)
        self._sync_fix_state()                           # первичное включ/выключ

    # вспом. — создаёт spin для фикс-значений с текстом '—' при 0
    def _spin_fix(self, default: int) -> QSpinBox:
        sp = QSpinBox(minimum=0, maximum=300, value=default)
        sp.setSpecialValueText("—")
        return sp

    # блокирует спины и показывает «—» -------------------------------
    def _sync_fix_state(self) -> None:
        var = "n" if self.rb_n.isChecked() else ("j" if self.rb_j.isChecked() else "m")
        for name, sp in (("n", self.fix_n), ("j", self.fix_j), ("m", self.fix_m)):
            if var == name:
                sp.setEnabled(False); sp.setValue(0)
            else:
                sp.setEnabled(True)
                if sp.value() == 0: sp.setValue(1 if name!="n" else 3)

    # построение графика ---------------------------------------------
    def _plot(self) -> None:
        self.ax.clear()

        var = "n" if self.rb_n.isChecked() else ("j" if self.rb_j.isChecked() else "m")
        st, en, step = self.start.value(), self.stop.value(), self.step.value()
        if step <= 0 or en < st:
            self._err("Проверьте диапазон."); return
        rng = range(st, en + 1, step)

        n_fix, j_fix, m_fix = self.fix_n.value(), self.fix_j.value(), self.fix_m.value()
        name   = self.cmb_formula_plot.currentText()
        repeat = name.startswith("F₄")
        mode   = self.cmb_mode_plot.currentText()

        xs, ys = [], []
        for x in rng:
            n, j, m = n_fix, j_fix, m_fix
            if   var == "n": n = x
            elif var == "j": j = x
            else:            m = x

            if m > n - 2:
                self._err(f"m = {m} > n-2 (={n-2}) в точке {x}"); return

            total = FORMULAS[name](n, j)
            vp    = core.p_m(n, j, m, repeat) / total if total else 0.0
            ys.append(vp if mode == "VP" else 1 - vp)
            xs.append(x)

        self.ax.plot(xs, ys, "o-")
        self.ax.set_xlabel(var); self.ax.set_ylabel(mode)
        self.ax.set_ylim(0, 1); self.ax.grid(True, ls=":")
        self.canvas.draw_idle()

    # вывод ошибки ----------------------------------------------------
    def _err(self, txt: str) -> None:
        QMessageBox.critical(self, "Ошибка", txt, QMessageBox.Ok)
