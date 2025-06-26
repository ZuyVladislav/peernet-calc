# routes_tab.py
from __future__ import annotations
import itertools, os
os.environ["MPLBACKEND"] = "Qt5Agg"          # строго до pyplot!

from PyQt5.QtWidgets import (
    QWidget, QGridLayout, QLabel, QSpinBox, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QCheckBox,
    QGroupBox, QMessageBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
import matplotlib.pyplot as plt
import core

FORMULAS = {
    "F₁ Tor-тип"   : lambda n, j: core.f_tor(n, j),
    "F₂ I2P-тип"   : lambda n, j: core.f_i2p(n, j),
    "F₃ без повторений"  : core.f1_no_rep,
    "F₄ с повторениями" : lambda n, j: core.f2_rep(j, n),
}
FORMULA_COLORS = {
    "F₁ Tor-тип"        : "tab:red",
    "F₂ I2P-тип"        : "tab:purple",
    "F₃ без повторений" : "tab:brown",
    "F₄ с повторениями" : "tab:blue",
}

class RoutesTab(QWidget):
    """Вкладка «Маршруты» — одно значение + график."""

    # ─────────────────────────────────────────────────────────
    def __init__(self) -> None:
        super().__init__()
        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        self.canvas       = Canvas(self.fig)

        grid = QGridLayout(self)
        self._build_single_block(grid)
        self._build_plot_block(grid)

        grid.addWidget(self.canvas, 6, 0, 1, 5)

    # ---------- одиночный расчёт -------------------------------------
    def _build_single_block(self, g: QGridLayout) -> None:
        self.cmb_formula = QComboBox(); self.cmb_formula.addItems(FORMULAS)
        self.spin_n = QSpinBox(minimum=3, maximum=300, value=7)
        self.spin_j = QSpinBox(minimum=1, maximum=299, value=3)

        btn = QPushButton("Рассчитать"); btn.clicked.connect(self._single)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Формула", "Значение"])
        self.table.horizontalHeader().setStretchLastSection(True)

        g.addWidget(QLabel("Формула"), 0, 0); g.addWidget(self.cmb_formula, 0, 1, 1, 3)
        g.addWidget(QLabel("Количество узлов в сети (n)"),       1, 0); g.addWidget(self.spin_n,      1, 1)
        g.addWidget(QLabel("Количество промежуточных узлов (j)"),       2, 0); g.addWidget(self.spin_j,      2, 1)
        g.addWidget(btn,               3, 0, 1, 4)
        g.addWidget(self.table,        4, 0, 1, 4)

    def _single(self) -> None:
        n, j = self.spin_n.value(), self.spin_j.value()
        name = self.cmb_formula.currentText()
        try:
            val = FORMULAS[name](n, j)
        except Exception as e:
            self._err(str(e)); return
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem(name))
        self.table.setItem(0, 1, QTableWidgetItem(f"{val:,}"))

    # ---------- график ------------------------------------------------
    def _build_plot_block(self, g: QGridLayout) -> None:
        grp = QGroupBox("График");
        gl = QGridLayout(grp)

        # --- чек-боксы формул ------------------------------------------------
        self.chk_form = []
        for i, name in enumerate(FORMULAS):
            chk = QCheckBox(name);
            chk.setChecked(i < 2)
            self.chk_form.append(chk)
            gl.addWidget(chk, i, 0, 1, 2)

        # --- выбор переменной ------------------------------------------------
        gl.addWidget(QLabel("Изменять"), len(FORMULAS), 0)
        self.cmb_var = QComboBox()
        self.cmb_var.addItems(["Количество узлов в сети (n)", "Количество промежуточных узлов (j)"])
        self.cmb_var.currentIndexChanged.connect(self._toggle_fix_spin)  # ← ★
        gl.addWidget(self.cmb_var, len(FORMULAS), 1)

        # --- диапазон --------------------------------------------------------
        row = len(FORMULAS) + 1
        self.start = QSpinBox(minimum=1, maximum=300, value=3)
        self.stop = QSpinBox(minimum=2, maximum=300, value=30)
        self.step = QSpinBox(minimum=1, maximum=100, value=1)
        gl.addWidget(QLabel("Начало"), row, 0);
        gl.addWidget(self.start, row, 1)
        gl.addWidget(QLabel("Конец"), row + 1, 0);
        gl.addWidget(self.stop, row + 1, 1)
        gl.addWidget(QLabel("Шаг"), row + 2, 0);
        gl.addWidget(self.step, row + 2, 1)

        # --- фиксированные значения -----------------------------------------
        self.fix_n = QSpinBox(minimum=3, maximum=300, value=10)
        self.fix_j = QSpinBox(minimum=1, maximum=299, value=3)
        gl.addWidget(QLabel("Фикс n"), row + 3, 0);
        gl.addWidget(self.fix_n, row + 3, 1)
        gl.addWidget(QLabel("Фикс j"), row + 4, 0);
        gl.addWidget(self.fix_j, row + 4, 1)

        # --- кнопка ----------------------------------------------------------
        btn = QPushButton("Построить график");
        btn.clicked.connect(self._plot)
        gl.addWidget(btn, row + 5, 0, 1, 2)

        g.addWidget(grp, 0, 4, 6, 1)

        self._toggle_fix_spin()  # ← ★

    # ---------- новый метод -----------------------------------------------
    def _toggle_fix_spin(self) -> None:
        """Блокируем spin-box выбранной переменной и показываем «—»."""
        var_is_n = self.cmb_var.currentIndex() == 0  # True, если изменяем n

        # ----------- n ---------------------------------------------------
        if var_is_n:
            self._store_n = self.fix_n.value()  # запоминаем прежнее n
            self.fix_n.blockSignals(True)
            self.fix_n.setValue(self.fix_n.minimum())  # мин. = 3 → отображается «—»
            self.fix_n.blockSignals(False)
        else:
            if hasattr(self, "_store_n"):
                self.fix_n.setValue(self._store_n)  # возвращаем
        self.fix_n.setDisabled(var_is_n)
        self.fix_n.setSpecialValueText("—" if var_is_n else "")

        # ----------- j ---------------------------------------------------
        if not var_is_n:
            self._store_j = self.fix_j.value()  # запоминаем прежнее j
            self.fix_j.blockSignals(True)
            self.fix_j.setValue(self.fix_j.minimum())  # мин. = 1 → «—»
            self.fix_j.blockSignals(False)
        else:
            if hasattr(self, "_store_j"):
                self.fix_j.setValue(self._store_j)
        self.fix_j.setDisabled(not var_is_n)
        self.fix_j.setSpecialValueText("—" if not var_is_n else "")

    def _plot(self) -> None:
        """Строит выбранные формулы в лог-масштабе."""
        self.ax.clear()

        # --- какие координаты по X -----------------------------------
        var_txt = self.cmb_var.currentText()  # "Количество узлов ..." | "Количество промежуточных ..."
        var = "n" if self.cmb_var.currentIndex() == 0 else "j"

        # --- диапазон -------------------------------------------------
        start = self.start.value()
        stop = self.stop.value()
        step = self.step.value()
        if step <= 0 or stop < start:
            self._err("Проверьте start / stop / step");
            return

        # автосдвиг нуля: F1/F4 дают результат, только когда n ≥ j+2
        if var == "n":
            start = max(start, self.fix_j.value() + 2)

        rng = range(start, stop + 1, step)

        # --- рисуем ---------------------------------------------------
        fixed_n, fixed_j = self.fix_n.value(), self.fix_j.value()
        drawn = False
        for chk in self.chk_form:
            if not chk.isChecked():
                continue

            func = FORMULAS[chk.text()]
            xs, ys = [], []

            for x in rng:
                n, j = (x, fixed_j) if var == "n" else (fixed_n, x)
                y = func(n, j)
                if y:  # пропускаем нули
                    xs.append(x);
                    ys.append(y)

            if ys:  # есть что рисовать
                color = FORMULA_COLORS.get(chk.text(), "black")  # фиксированный цвет
                self.ax.plot(xs, ys, "o-", label=chk.text(), color=color)
                drawn = True

        if not drawn:
            self._err("В указанном диапазоне все значения = 0");
            return

        # --- оформление ------------------------------------------------
        self.ax.set_xlabel(var)
        self.ax.set_ylabel("Маршруты")
        self.ax.set_yscale("log")
        self.ax.grid(True, ls=":")
        self.ax.legend()
        self.canvas.draw_idle()

    # ---------- вспомогательное --------------------------------------
    def _err(self, txt: str) -> None:
        QMessageBox.critical(self, "Ошибка", txt, QMessageBox.Ok)
