from __future__ import annotations

import os
from typing import Callable, List

os.environ["MPLBACKEND"] = "Qt5Agg"

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QWidget, QGridLayout, QLabel, QSpinBox, QPushButton,
                             QComboBox, QTableWidget, QTableWidgetItem, QCheckBox,
                             QGroupBox, QMessageBox, QDialog, QVBoxLayout,
                             QToolButton, QHBoxLayout, QSizePolicy)
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as Canvas,
    NavigationToolbar2QT,
)
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import core

# ──────────────────────── формулы/цвета ────────────────────────────
FORMULAS: dict[str, Callable[[int, int], int]] = {
    "F₁ Tor-тип":        core.f_tor,
    "F₃ без повторений": core.f1_no_rep,
    "F₄ с повторениями": lambda n, j: core.f2_rep(j, n),
}
COLORS = {"F₁ Tor-тип": "tab:red",
          "F₃ без повторений": "tab:brown",
          "F₄ с повторениями": "tab:blue"}
THIN = "\u202F"  # narrow no-break space

# ══════════════════ PlotWindow ══════════════════════════════════════
class PlotWindow(QDialog):
    def __init__(self, fig, ax, *, w: int, h: int, title: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(title)
        self.resize(int(w * 100), int(h * 100))

        self.canvas  = Canvas(fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        plus_btn  = QToolButton(text="+")
        minus_btn = QToolButton(text="−")
        plus_btn.clicked.connect(lambda: self._zoom(ax, 0.8))
        minus_btn.clicked.connect(lambda: self._zoom(ax, 1.25))
        extra = QHBoxLayout(); extra.addWidget(plus_btn); extra.addWidget(minus_btn); extra.addStretch()

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.toolbar)
        vbox.addLayout(extra)
        vbox.addWidget(self.canvas)

        self.canvas.mpl_connect("scroll_event",
                                lambda ev: self._on_scroll(ev, ax))

    # -------- zoom helpers -----------------------------------------
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
        qt_ev = ev.guiEvent
        has_ctrl = bool(qt_ev and qt_ev.modifiers() & Qt.ControlModifier)
        if not has_ctrl:
            return
        scale = 0.8 if ev.button == "up" else 1.25
        ax.set_xlim(*self._scaled(ax.get_xlim(), ev.xdata, scale))
        ax.set_ylim(*self._scaled(ax.get_ylim(), ev.ydata, scale))
        self.canvas.draw_idle()

# ══════════════════ RoutesTab ═══════════════════════════════════════
class RoutesTab(QWidget):
    def __init__(self):
        super().__init__()

        # ---------- предварительный график ---------------------------------
        self.fig_prev, self.ax_prev = plt.subplots(figsize=(6, 4))
        self.canvas_prev = Canvas(self.fig_prev)

        # ---------- общая сетка --------------------------------------------
        grid = QGridLayout(self)

        # 8 виртуальных столбцов: 0 … 7
        grid.setColumnStretch(0, 4)      # холст  (0-4)
        grid.setColumnStretch(5, 2)      # блок значений (5-7)
        grid.setColumnStretch(6, 2)

        # ── ВЕРХНЯЯ СТРОКА (Формула / n / j / кнопка / результат) ──
        header = self._build_single()          # ← теперь метод возвращает QWidget
        grid.addWidget(header, 0, 0, 1, 8)     # row=0, col=0, colspan=5

        # ── холст графика ───────────────────────────────────────────
        grid.addWidget(self.canvas_prev, 1, 0, 3, 5)   # 0-4

        # ── блок «График / значения» ───────────────────────────────
        self._build_plot_block(grid)          # внутри g.addWidget(grp, 1, 5, 3, 3)

    # -------- ед. расчёт -------------------------------------------
    def _build_single(self) -> QWidget:
        box = QWidget()
        h = QHBoxLayout(box)
        h.setContentsMargins(0, 0, 0, 0)

        self.cmb_formula = QComboBox();
        self.cmb_formula.addItems(FORMULAS)
        self.spin_n = QSpinBox(minimum=3, maximum=300, value=8)
        self.spin_j = QSpinBox(minimum=1, maximum=299, value=3)
        btn = QPushButton("Рассчитать");
        btn.setMinimumWidth(110)
        btn.clicked.connect(self._single)
        btn.clicked.connect(self._single)

        self.lbl_res = QLabel("…")
        self.lbl_res.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        h.addWidget(QLabel("Формула"))
        h.addWidget(self.cmb_formula)
        h.addWidget(QLabel("Кол-во узлов в сети (n)"));
        h.addWidget(self.spin_n)
        h.addWidget(QLabel("Кол-во промежуточных узлов (j)"));
        h.addWidget(self.spin_j)
        h.addWidget(btn)
        h.addWidget(self.lbl_res)
        h.addStretch()

        return box

    def _single(self):
        n, j = self.spin_n.value(), self.spin_j.value()
        name = self.cmb_formula.currentText()
        try:
            val = FORMULAS[name](n, j)
            txt = f"<b>{name}</b> = {format(val, ',d').replace(',', THIN)}"
            self.lbl_res.setText(txt)  # просто меняем текст
        except Exception as e:
            self._err(str(e))

    # -------- блок графика -----------------------------------------
    def _build_plot_block(self, g: QGridLayout):
        grp = QGroupBox("График / значения"); gl = QGridLayout(grp)

        self.chk_form: List[QCheckBox] = []
        for i, nm in enumerate(FORMULAS):
            cb = QCheckBox(nm); cb.setChecked(True)
            self.chk_form.append(cb); gl.addWidget(cb, i, 0, 1, 2)

        gl.addWidget(QLabel("Х-переменная"), len(FORMULAS), 0)
        self.cmb_var = QComboBox(); self.cmb_var.addItems(["Кол-во узлов в сети (n)", "Кол-во промежуточных узлов (j)"])
        self.cmb_var.currentIndexChanged.connect(self._toggle)
        gl.addWidget(self.cmb_var, len(FORMULAS), 1)

        row = len(FORMULAS) + 1
        self.start = QSpinBox(minimum=1, maximum=300, value=10)
        self.stop  = QSpinBox(minimum=2, maximum=300, value=20)
        self.step  = QSpinBox(minimum=1, maximum=100, value=1)
        for lbl, sp in ("Начало", self.start), ("Конец", self.stop), ("Шаг", self.step):
            gl.addWidget(QLabel(lbl), row, 0); gl.addWidget(sp, row, 1); row += 1

        self.fix_n = QSpinBox(minimum=3, maximum=300, value=10)
        self.fix_j = QSpinBox(minimum=1, maximum=299, value=3)
        gl.addWidget(QLabel("Фиксированное (n)"), row, 0); gl.addWidget(self.fix_n, row, 1); row += 1
        gl.addWidget(QLabel("Фиксированное (j)"), row, 0); gl.addWidget(self.fix_j, row, 1); row += 1

        self.fig_w = QSpinBox(minimum=4, maximum=20, value=8)
        self.fig_h = QSpinBox(minimum=4, maximum=20, value=8)
        gl.addWidget(QLabel("Ширина"),  row, 0); gl.addWidget(self.fig_w, row, 1); row += 1
        gl.addWidget(QLabel("Высота"), row, 0); gl.addWidget(self.fig_h, row, 1); row += 1

        self.chk_log = QCheckBox("Логарифмическая шкала")
        self.chk_log.setChecked(False)  # линейная шкала по умолчанию
        gl.addWidget(self.chk_log, row, 0, 1, 2); row += 1

        btn = QPushButton("Построить график"); btn.clicked.connect(self._plot)
        gl.addWidget(btn, row, 0, 1, 2); row += 1

        self.tbl_vals = QTableWidget(); gl.addWidget(self.tbl_vals, row, 0, 4, 2)
        g.addWidget(grp, 1, 5, 3, 4)
        self._toggle()
        grp.setMinimumWidth(260)  # сколько нужно
        grp.setMaximumWidth(500)  # опционно: верхний предел

    # -------- переключение	spin‑боксов -------------------------------
    def _toggle(self):
        x_is_n = self.cmb_var.currentIndex() == 0  # True → X = n

        # --- fix n -----------------------------------------------------
        if x_is_n:  # n — переменная, значит фикс n «гасим»
            self.fix_n.setDisabled(True)
            self.fix_n.setSpecialValueText("—")
            self.fix_n.setValue(self.fix_n.minimum())  # ← покажет прочерк
        else:  # n — фикс, включаем
            self.fix_n.setDisabled(False)
            self.fix_n.setSpecialValueText("")  # обычная цифра
            if self.fix_n.value() == self.fix_n.minimum():
                self.fix_n.setValue(10)  # любое «рабочее» число

        # --- fix j (симметрично) --------------------------------------
        if not x_is_n:  # j переменная → фикс j «гасим»
            self.fix_j.setDisabled(True)
            self.fix_j.setSpecialValueText("—")
            self.fix_j.setValue(self.fix_j.minimum())
        else:
            self.fix_j.setDisabled(False)
            self.fix_j.setSpecialValueText("")
            if self.fix_j.value() == self.fix_j.minimum():
                self.fix_j.setValue(3)

    # -------- построение графика и заполнение таблицы --------------
    def _plot(self):
        self.ax_prev.clear(); self.tbl_vals.clear()
        ch = self.cmb_var.currentIndex() == 0  # X = n?
        s, e, st = self.start.value(), self.stop.value(), self.step.value()
        if e < s or st <= 0:
            return self._err("Диапазон X неверен")

        rng = list(range(s, e + 1, st))
        fn, fj = self.fix_n.value(), self.fix_j.value()
        if ch:
            rng = [x for x in rng if x >= fj + 2]
        if not rng:
            return self._err("Нет допустимых X")

        dataset = []  # [(name, xs, ys)]
        for cb in self.chk_form:
            if not cb.isChecked():
                continue
            nm = cb.text(); fun = FORMULAS[nm]
            xs, ys = [], []
            for x in rng:
                n, j = (x, fj) if ch else (fn, x)
                try:
                    y = fun(n, j)
                except Exception:
                    y = 0
                if y:
                    xs.append(x); ys.append(y)
            if ys:
                dataset.append((nm, xs, ys))

        if not dataset:
            return self._err("Все значения = 0")

        title = f"j = {fj}" if ch else f"n = {fn}"
        self._draw(self.ax_prev, dataset, title)
        self.canvas_prev.draw_idle()

        # таблица значений
        self._fill_table(rng, dataset)

        # большое окно
        w, h = self.fig_w.value(), self.fig_h.value()
        fig_big, ax_big = plt.subplots(figsize=(w, h))
        self._draw(ax_big, dataset, title)
        PlotWindow(fig_big, ax_big, w=w, h=h, title=title, parent=self).show()

    def _fill_table(self, xs: List[int], dataset):
        cols = 1 + len(dataset)
        self.tbl_vals.setColumnCount(cols)
        headers = ["X"] + [nm for nm, _, _ in dataset]
        self.tbl_vals.setHorizontalHeaderLabels(headers)
        self.tbl_vals.setRowCount(len(xs))

        # X values
        for row, x in enumerate(xs):
            itm = QTableWidgetItem(str(x))
            itm.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tbl_vals.setItem(row, 0, itm)

        # other columns
        for col, (nm, x_list, y_list) in enumerate(dataset, start=1):
            mapping = dict(zip(x_list, y_list))
            for row, x in enumerate(xs):
                if x in mapping:
                    txt = format(mapping[x], ",d").replace(",", THIN)
                    itm = QTableWidgetItem(txt)
                    itm.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.tbl_vals.setItem(row, col, itm)

        self.tbl_vals.resizeColumnsToContents()

    # -------- draw & error -----------------------------------------
    def _draw(self, ax, data, title):
        var = self.cmb_var.currentText()
        ax.clear()
        for nm, xs, ys in data:
            ax.plot(xs, ys, "o-", color=COLORS.get(nm, "black"), label=nm)
        ax.set_xlabel(var); ax.set_ylabel("Маршруты")
        ax.set_title(title)
        if self.chk_log.isChecked():
            ax.set_yscale("log")
        else:
            ax.set_yscale("linear")
            ax.yaxis.set_major_formatter(mticker.EngFormatter())
        ax.grid(True, ls=":" ); ax.legend()

    def _err(self, txt: str):
        QMessageBox.critical(self, "Ошибка", txt, QMessageBox.Ok)
