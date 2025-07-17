from __future__ import annotations
import os; os.environ["MPLBACKEND"] = "Qt5Agg"       # обязательно до импортов pyplot

try:  # PySide6 → PyQt5 fallback
    from PySide6.QtWidgets import (
        QWidget, QGridLayout, QLabel, QSpinBox, QPushButton,
        QComboBox, QListWidget, QListWidgetItem, QCheckBox, QGroupBox, QMessageBox,
        QRadioButton, QDialog, QVBoxLayout, QToolButton, QHBoxLayout
    )
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QStyleFactory
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas, NavigationToolbar2QT
except ImportError:
    from PyQt5.QtWidgets import (
        QWidget, QGridLayout, QLabel, QSpinBox, QPushButton,
        QComboBox, QListWidget, QListWidgetItem, QCheckBox, QGroupBox, QMessageBox,
        QRadioButton, QDialog, QVBoxLayout, QToolButton, QHBoxLayout
    )
    from PyQt5.QtCore import Qt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas, NavigationToolbar2QT

import matplotlib.pyplot as plt
import core

# ───────────────────── формулы и цвета для ВП/ВУС ─────────────────────
def vp_tor(m: int, n: int, j: int) -> float:
    """Вероятность перехвата по формуле F₁ (Tor-тип)."""
    total = core.f_tor(n, j) if n >= 3 else 0  # F₁: общее число маршрутов
    if m == 0:
        safe = total  # без компрометированных узлов: все маршруты безопасны
    elif n - m < 2:
        safe = 0      # удалены слишком много узлов (остались ≤ A и B)
    else:
        safe = core.f_tor(n - m, j)
    intercepted = max(total - safe, 0)
    return intercepted / total if total else 0.0

FORMULAS: dict[str, callable] = {
    "F₁ Tor-тип":        vp_tor,
    "F₃ без повторений": lambda m, n, j: core.vp(m, n, j, repeat=False),
    "F₄ с повторениями": lambda m, n, j: core.vp(m, n, j, repeat=True),
}
COLORS = {
    "F₁ Tor-тип":        "tab:red",
    "F₃ без повторений": "tab:brown",
    "F₄ с повторениями": "tab:blue",
}

# ══════════════════════════ PlotWindow ════════════════════════════
class PlotWindow(QDialog):
    def __init__(self, fig, ax, *, w: int, h: int, title: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(title)
        self.resize(int(w * 100), int(h * 100))

        self.canvas = Canvas(fig)
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

        # Прокрутка с Ctrl для зумирования
        self.canvas.mpl_connect("scroll_event",
                                lambda ev: self._on_scroll(ev, ax))

    # --- zoom helpers ---
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
        """Масштабирование графика при прокрутке с зажатым Ctrl."""
        qt_ev = ev.guiEvent
        # Обрабатываем только события прокрутки с удержанием Ctrl
        if not qt_ev or not (qt_ev.modifiers() & Qt.ControlModifier):
            return
        scale = 0.8 if ev.button == "up" else 1.25
        ax.set_xlim(*self._scaled(ax.get_xlim(), ev.xdata, scale))
        ax.set_ylim(*self._scaled(ax.get_ylim(), ev.ydata, scale))
        self.canvas.draw_idle()

# ═══════════════════════════ VPTab ═════════════════════════════
class VPTab(QWidget):
    """Вкладка «ВП / ВУС» — расчёт вероятности перехвата/успеха соединения."""
    def __init__(self):
        super().__init__()
        # Figure/canvas for preview graph
        self.fig_prev, self.ax_prev = plt.subplots(figsize=(6, 4))
        self.canvas_prev = Canvas(self.fig_prev)

        grid = QGridLayout(self)
        self._build_single(grid)                           # верхний ряд с единичным расчётом
        grid.addWidget(self.canvas_prev, 1, 0, 3, 6)      # область графика-превью
        self._build_plot_block(grid)                       # группа "График / значения"

    # ----- Единичный расчёт ВП/ВУС -----
    def _build_single(self, g: QGridLayout):
        # Выбор формулы и параметров
        self.cmb_formula = QComboBox(); self.cmb_formula.addItems(FORMULAS.keys())
        self.spin_n = QSpinBox(minimum=3, maximum=300, value=10)
        self.spin_j = QSpinBox(minimum=1, maximum=299, value=3)
        self.spin_m = QSpinBox(minimum=0, maximum=299, value=1)

        # Переключатели для ВП и ВУС
        self.rb_vp = QRadioButton("ВП"); self.rb_vp.setChecked(True)
        self.rb_vus = QRadioButton("ВУС")

        btn_calc = QPushButton("Рассчитать"); btn_calc.clicked.connect(self._single)
        self.lbl_res = QLabel("…")

        # Расположение элементов в сетке (1 строка)
        g.addWidget(QLabel("Формула"),        0, 0)
        g.addWidget(self.cmb_formula,        0, 1)
        g.addWidget(self.rb_vp,             0, 2)
        g.addWidget(self.rb_vus,            0, 3)
        g.addWidget(QLabel("n"),             0, 4); g.addWidget(self.spin_n, 0, 5)
        g.addWidget(QLabel("j"),             0, 6); g.addWidget(self.spin_j, 0, 7)
        g.addWidget(QLabel("m"),             0, 8); g.addWidget(self.spin_m, 0, 9)
        g.addWidget(btn_calc,                0, 10); g.addWidget(self.lbl_res, 0, 11, 1, 2)

    def _single(self):
        n = self.spin_n.value()
        j = self.spin_j.value()
        m = self.spin_m.value()
        formula_name = self.cmb_formula.currentText()
        try:
            # Выбор функции расчёта по формуле
            fun = FORMULAS[formula_name]
            value = fun(m, n, j)  # вычисление ВП (по умолчанию)
            if self.rb_vus.isChecked():
                value = 1.0 - value  # для ВУС берём комплементарное значение
            # Форматирование результата с указанием формулы и типа вероятности
            param_type = "ВП" if self.rb_vp.isChecked() else "ВУС"
            self.lbl_res.setText(f"<b>{formula_name} — {param_type}</b> = {value:.4f}")
        except Exception as e:
            self._err(str(e))

    # ----- Блок построения графика -----
    def _build_plot_block(self, g: QGridLayout):
        grp = QGroupBox("График / значения"); gl = QGridLayout(grp)

        # Флажки выбора формул F₁, F₃, F₄
        self.chk_form: list[QCheckBox] = []
        for i, name in enumerate(FORMULAS.keys()):
            cb = QCheckBox(name); cb.setChecked(True)
            self.chk_form.append(cb)
            gl.addWidget(cb, i, 0, 1, 2)
        # Переключатель переменной X (n или m)
        gl.addWidget(QLabel("X-переменная"), len(FORMULAS), 0)
        self.cmb_var = QComboBox(); self.cmb_var.addItems(["n", "m"])
        self.cmb_var.currentIndexChanged.connect(self._toggle)
        gl.addWidget(self.cmb_var, len(FORMULAS), 1)

        row = len(FORMULAS) + 1
        # Диапазон изменения X
        self.start = QSpinBox(minimum=1, maximum=300, value=10)
        self.stop  = QSpinBox(minimum=2, maximum=300, value=20)
        self.step  = QSpinBox(minimum=1, maximum=100, value=1)
        for lbl, sp in (("Start", self.start), ("Stop", self.stop), ("Step", self.step)):
            gl.addWidget(QLabel(lbl), row, 0); gl.addWidget(sp, row, 1); row += 1

        # Фиксированные значения (недоступные при выбранной переменной)
        self.fix_n = QSpinBox(minimum=3, maximum=300, value=10)
        self.fix_j = QSpinBox(minimum=1, maximum=299, value=3)
        self.fix_m = QSpinBox(minimum=0, maximum=299, value=1)
        gl.addWidget(QLabel("fix n"), row, 0); gl.addWidget(self.fix_n, row, 1); row += 1
        gl.addWidget(QLabel("fix j"), row, 0); gl.addWidget(self.fix_j, row, 1); row += 1
        gl.addWidget(QLabel("fix m"), row, 0); gl.addWidget(self.fix_m, row, 1); row += 1

        # Параметры размера графика
        self.fig_w = QSpinBox(minimum=4, maximum=20, value=10)
        self.fig_h = QSpinBox(minimum=3, maximum=15, value=7)
        gl.addWidget(QLabel("width"),  row, 0); gl.addWidget(self.fig_w, row, 1); row += 1
        gl.addWidget(QLabel("height"), row, 0); gl.addWidget(self.fig_h, row, 1); row += 1

        # Масштаб по Y (Log scale)
        self.chk_log = QCheckBox("Log Y"); self.chk_log.setChecked(False)
        gl.addWidget(self.chk_log, row, 0, 1, 2); row += 1

        # Кнопка построения и список значений
        btn_plot = QPushButton("Построить график"); btn_plot.clicked.connect(self._plot)
        gl.addWidget(btn_plot, row, 0, 1, 2); row += 1
        self.lst_vals = QListWidget()
        gl.addWidget(self.lst_vals, row, 0, 4, 2)

        # Размещение группы на общей сетке вкладки
        g.addWidget(grp, 1, 6, 3, 2)
        self._toggle()  # установить начальное состояние фиксов

    def _toggle(self):
        """Активирует/деактивирует spin-боксы фиксированных значений в зависимости от выбранной X-переменной."""
        x_is_n = (self.cmb_var.currentIndex() == 0)   # True, если X — n, иначе X — m
        # При X = n отключаем ввод fix_n, включаем fix_m и fix_j
        self.fix_n.setDisabled(x_is_n); self.fix_m.setDisabled(not x_is_n)
        # fix_j всегда остается включенным, т.к. j не выбирается как X-переменная
        self.fix_j.setDisabled(False)
        # Отображаем "—" в отключенном spin-box (иначе пустая строка)
        self.fix_n.setSpecialValueText("—" if x_is_n else "")
        self.fix_m.setSpecialValueText("—" if not x_is_n else "")

    # -------- Построение графиков --------
    def _plot(self):
        # Очистка предыдущего графика и списка значений
        self.ax_prev.clear()
        self.lst_vals.clear()

        x_is_n = (self.cmb_var.currentIndex() == 0)
        s, e, st = self.start.value(), self.stop.value(), self.step.value()
        if e < s or st <= 0:
            return self._err("Диапазон X неверен")

        rng = range(s, e + 1, st)
        fn, fj, fm = self.fix_n.value(), self.fix_j.value(), self.fix_m.value()
        if x_is_n:
            # Для X = n отфильтровываем значения, где n < j + 2 (маршруты невозможны)
            rng = [x for x in rng if x >= fj + 2]
        if not rng:
            return self._err("Нет допустимых X")

        dataset = []
        # Проходим по отмеченным формулам и вычисляем значения
        for cb in self.chk_form:
            if not cb.isChecked():
                continue
            name = cb.text()
            fun = FORMULAS[name]
            xs, ys = [], []
            for x in rng:
                # Подставляем значения переменных: изменяемый X и фиксированные параметры
                if x_is_n:
                    n, j, m = x, fj, fm
                else:  # X = m
                    n, j, m = fn, fj, x
                try:
                    val = fun(m, n, j)
                except Exception:
                    val = 0.0
                if val:
                    # Если выбрана ВУС, используем дополняющее значение
                    if self.rb_vus.isChecked():
                        val = 1.0 - val
                    xs.append(x); ys.append(val)
                    # Добавляем только значение (без подписи формулы и X):contentReference[oaicite:3]{index=3}
                    self.lst_vals.addItem(QListWidgetItem(f"{val:.4f}"))
            if ys:
                dataset.append((name, xs, ys))

        if not dataset:
            return self._err("Все значения = 0")

        # Заголовок графика с указанием фиксированного параметра (j или n):contentReference[oaicite:4]{index=4}
        title = f"j = {fj}" if x_is_n else f"n = {fn}"
        # Отрисовка на превью-графике
        self._draw(self.ax_prev, dataset, title)
        self.canvas_prev.draw_idle()
        # Отрисовка на большом графике в отдельном окне
        w, h = self.fig_w.value(), self.fig_h.value()
        fig_big, ax_big = plt.subplots(figsize=(w, h))
        self._draw(ax_big, dataset, title)
        PlotWindow(fig_big, ax_big, w=w, h=h, title=title, parent=self).show()

    def _draw(self, ax, data, title: str):
        """Отрисовка линий графика по данным `data` на оси `ax`."""
        var_label = self.cmb_var.currentText()
        ax.clear()
        for name, xs, ys in data:
            ax.plot(xs, ys, "o-", color=COLORS.get(name, "black"), label=name)
        ax.set_xlabel(var_label)
        # В подписи оси Y указываем выбранный тип вероятности (ВП или ВУС)
        ax.set_ylabel("ВП" if self.rb_vp.isChecked() else "ВУС")
        ax.set_title(title)
        # Линейный или логарифмический масштаб по Y
        if self.chk_log.isChecked():
            ax.set_yscale("log")
        else:
            ax.set_yscale("linear")
        ax.grid(True, ls=":")
        ax.legend()

    def _err(self, msg: str):
        QMessageBox.critical(self, "Ошибка", msg, QMessageBox.Ok)