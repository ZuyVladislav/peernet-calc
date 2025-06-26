# mss_tab.py – вкладка «Сценарии» (N_MSS)
from __future__ import annotations
import os; os.environ["MPLBACKEND"] = "Qt5Agg"       # обязательно до pyplot

try:                               # PySide6 → PyQt5 fallback
    from PySide6.QtWidgets import (
        QWidget, QGridLayout, QLabel, QSpinBox, QPushButton,
        QRadioButton, QGroupBox, QMessageBox
    )
except ImportError:
    from PyQt5.QtWidgets import (
        QWidget, QGridLayout, QLabel, QSpinBox, QPushButton,
        QRadioButton, QGroupBox, QMessageBox
    )

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
import matplotlib.pyplot as plt
import core


# ────────────────────────────────────────────────────────────────────
class MSSTab(QWidget):
    """ ▸ одиночный расчёт  N_MSS(j,k,n)
        ▸ график по n / j / k  с автопропуском недопустимых точек (k ≤ n-2) """

    def __init__(self) -> None:
        super().__init__()

        # единая фигура для вкладки
        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        self.canvas = Canvas(self.fig)

        g = QGridLayout(self)

        # ----- входные поля -----------------------------------------
        self.spin_n = self._sp(7, 3)
        self.spin_j = self._sp(4, 1)
        self.spin_k = self._sp(3, 1)

        calc = QPushButton("Рассчитать"); calc.clicked.connect(self._single)
        self.lbl_out = QLabel("—")

        g.addWidget(QLabel("Количество узлов в сети (n)"), 0, 0); g.addWidget(self.spin_n, 0, 1)
        g.addWidget(QLabel("Количество промежуточных узлов (j)"), 1, 0); g.addWidget(self.spin_j, 1, 1)
        g.addWidget(QLabel("Количество стартовых пакетов (k)"), 2, 0);   g.addWidget(self.spin_k, 2, 1)
        g.addWidget(calc, 3, 0, 1, 2)
        g.addWidget(self.lbl_out, 4, 0, 1, 2)

        # ----- блок графика -----------------------------------------
        self._build_plot_box(g)

        g.addWidget(self.canvas, 7, 0, 1, 4)

    # ───── одиночный расчёт ─────────────────────────────────────────
    def _single(self) -> None:
        n, j, k = self.spin_n.value(), self.spin_j.value(), self.spin_k.value()
        if k > n - 2:
            self._err(f"k = {k} > n-2 (= {n-2}) при n = {n}")
            return
        try:
            val = core.n_mss(j, k, n)
        except Exception as exc:
            self._err(str(exc)); return
        self.lbl_out.setText(f"N_MSS = {val:,}")

    # ───── построение графика ───────────────────────────────────────
    def _plot(self) -> None:
        self.ax.clear()

        # какую переменную изменяем
        if   self.rb_n.isChecked(): var = "n"
        elif self.rb_j.isChecked(): var = "j"
        else:                       var = "k"

        st, en, step = self.start.value(), self.stop.value(), self.step.value()
        if step <= 0 or en < st:
            self._err("Проверьте диапазон: start ≤ stop, step > 0"); return

        n0, j0, k0 = self.fix_n.value(), self.fix_j.value(), self.fix_k.value()
        xs, ys = [], []

        for x in range(st, en + 1, step):
            n, j, k = n0, j0, k0
            if   var == "n": n = x
            elif var == "j": j = x
            else:            k = x

            if k > n - 2:
                continue            # точка недопустима

            try:
                ys.append(core.n_mss(j, k, n))
            except Exception as exc:
                self._err(str(exc)); return
            xs.append(x)

        if not ys:
            self._err("Во всём диапазоне нет точек, удовлетворяющих k ≤ n-2"); return

        self.ax.plot(xs, ys, "o-")
        self.ax.set_xlabel(var); self.ax.set_ylabel("N_MSS")
        self.ax.set_yscale("log"); self.ax.grid(True, ls=":")
        self.canvas.draw_idle()

    # ───── GUI helpers ───────────────────────────────────────────────
    def _build_plot_box(self, grid: QGridLayout) -> None:
        grp = QGroupBox("График"); gl = QGridLayout(grp)

        # выбор оси X
        self.rb_n = QRadioButton("Количество узлов в сети (n)"); self.rb_n.setChecked(True)
        self.rb_j = QRadioButton("Количество промежуточных узлов (j)")
        self.rb_k = QRadioButton("Количество стартовых пакетов (k)")
        for rb in (self.rb_n, self.rb_j, self.rb_k):
            rb.toggled.connect(self._toggle_fixes)

        gl.addWidget(QLabel("Изменять"), 0, 0)
        gl.addWidget(self.rb_n, 0, 1); gl.addWidget(self.rb_j, 0, 2); gl.addWidget(self.rb_k, 0, 3)

        # диапазон
        self.start = self._sp(3, 1); self.stop = self._sp(30, 2); self.step = self._sp(1, 1)
        gl.addWidget(QLabel("Начало"), 1, 0); gl.addWidget(self.start, 1, 1)
        gl.addWidget(QLabel("Конец"), 2, 0);  gl.addWidget(self.stop,  2, 1)
        gl.addWidget(QLabel("Шаг"),   3, 0);  gl.addWidget(self.step,  3, 1)

        # фиксированные
        self.fix_n = self._sp(10, 3)
        self.fix_j = self._sp(2,  1)
        self.fix_k = self._sp(1,  1)
        gl.addWidget(QLabel("Фикс n"), 4, 0); gl.addWidget(self.fix_n, 4, 1)
        gl.addWidget(QLabel("Фикс j"), 5, 0); gl.addWidget(self.fix_j, 5, 1)
        gl.addWidget(QLabel("Фикс k"), 6, 0); gl.addWidget(self.fix_k, 6, 1)

        # кнопка
        btn = QPushButton("Построить"); btn.clicked.connect(self._plot)
        gl.addWidget(btn, 7, 0, 1, 4)

        grid.addWidget(grp, 0, 3, 6, 1)
        self._toggle_fixes()          # инициализируем видимость

    # главное изменение: «тире» вместо значения + запоминание старых
    def _toggle_fixes(self) -> None:
        """Переключает spin-box'ы фиксов: блокирует выбранную переменную
        и показывает «—», сохраняя предыдущее значение."""
        var = "n" if self.rb_n.isChecked() else "j" if self.rb_j.isChecked() else "k"

        for name, spin in (("n", self.fix_n), ("j", self.fix_j), ("k", self.fix_k)):
            if var == name:
                # запомнить старое и показать «—»
                setattr(self, f"_store_{name}", spin.value())
                spin.blockSignals(True)
                spin.setValue(spin.minimum())          # min → specialValueText
                spin.blockSignals(False)
                spin.setDisabled(True)
                spin.setSpecialValueText("—")
            else:
                # вернуть сохранённое (если было) и включить
                if hasattr(self, f"_store_{name}"):
                    spin.setValue(getattr(self, f"_store_{name}"))
                spin.setDisabled(False)
                spin.setSpecialValueText("")

    @staticmethod
    def _sp(val: int, minimum: int = 0) -> QSpinBox:
        s = QSpinBox(minimum=minimum, maximum=300, value=val)
        return s

    @staticmethod
    def _err(msg: str) -> None:
        QMessageBox.critical(None, "Ошибка", msg, QMessageBox.Ok)