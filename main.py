from __future__ import annotations
"""main.py — Peernet‑Calc GUI with separate «Уравнения» menu that shows formula images.

Дополнение: подсветка пунктов меню и верхней менюшки при наведении курсора (как в проводнике Windows).
"""

import sys
import os

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QAction,
    QMenu,
    QDialog,
    QVBoxLayout,
    QMessageBox,
    QLabel,
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import QSettings, Qt

import qtawesome as qta
import qdarkstyle

from routes_tab import RoutesTab
from vp_tab import VPTab
from mss_tab import MSSTab

# ────────── constants & utils ──────────────────────────────────────
CFG_ORG, CFG_APP, CFG_KEY = "PeernetLab", "Peernet-Calc", "theme"
PICT_DIR = os.path.join(os.path.dirname(__file__), "pictures")
awesome = lambda name, color: qta.icon(name, color=color)


# ---------- stylesheet ---------------------------------------------------------
LIGHT_HOVER = "#cfe8ff"   # голубая подсветка как у Explorer (светлая тема)
DARK_HOVER  = "#2d8cff"   # синяя подсветка на тёмной теме


def build_stylesheet(theme: str) -> str:
    """Return complete application‑wide stylesheet for the chosen theme."""

    if theme == "dark":
        # базовый тёмный стиль берём из qdarkstyle
        base = qdarkstyle.load_stylesheet(qt_api="pyqt5")
        hover = DARK_HOVER
        text  = "#e9e9e9"
    else:
        # свой минималистичный светлый стиль
        base = (
            "QWidget{background:#f7f8fa;color:#2b2b2b;}"
            "QPushButton{background:#00bcd4;color:#fff;border-radius:4px;height:26px;}"
            "QPushButton:hover{background:#26cbe4;}"
            "QTabBar::tab{background:#c9ccd9;padding:4px 12px;min-width:110px;}"
            "QTabBar::tab:selected{background:#00bcd4;color:#fff;}"
        )
        hover = LIGHT_HOVER
        text  = "#2b2b2b"

    # общая подсветка пунктов меню (верхняя панель + выпадающее меню)
    highlight_css = (
        f"QMenuBar::item:selected{{background:{hover};color:{text};}}"
        f"QMenuBar::item:pressed {{background:{hover};color:{text};}}"
        f"QMenu::item:hover       {{background:{hover};color:{text};}}"
        f"QMenu::item:selected    {{background:{hover};color:{text};}}"
    )

    return base + highlight_css + "*{font:11pt 'Segoe UI';}"


def apply_theme(app: QApplication, theme: str):
    app.setStyleSheet(build_stylesheet(theme))
    app.setFont(QFont("Segoe UI", 11))


# ────────── вспомогательное окно «Уравнения» ────────────────────────
class EqDialog(QDialog):
    """Показывает картинку‑формулу в QLabel."""

    IMG = {
        "Маршруты":  "routes_tab.png",
        "ВП / ВНС":  "vp_tab.png",
        "Сценарии":  "mss_tab.png",
    }

    def __init__(self, caption: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Уравнения — {caption}")
        self.resize(600, 400)
        self.setAttribute(Qt.WA_DeleteOnClose)

        lay = QVBoxLayout(self)

        img_name = self.IMG.get(caption)
        if not img_name:
            QMessageBox.warning(self, "Нет картинки", f"Для «{caption}» файл не задан.")
            return

        path = os.path.join(PICT_DIR, img_name)
        if not os.path.exists(path):
            QMessageBox.warning(self, "Нет файла", f"Файл {path} не найден.")
            return

        lbl = QLabel(alignment=Qt.AlignCenter)
        lbl.setPixmap(QPixmap(path))
        lay.addWidget(lbl)


# ────────── главное окно ────────────────────────────────────────────
class PeernetMain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Peernet-Calc  •  лаборатория")
        self.resize(1000, 700)
        self.setWindowIcon(awesome("fa5s.network-wired", "#00bcd4"))

        # вкладки
        tabs = QTabWidget(documentMode=True)
        tabs.addTab(RoutesTab(), awesome("fa5s.route", "#ff5252"), "Маршруты")
        tabs.addTab(VPTab(),     awesome("fa5s.shield-alt", "#ffc857"), "ВП / ВНС")
        tabs.addTab(MSSTab(),    awesome("fa5s.project-diagram", "plum"), "Сценарии")
        self.setCentralWidget(tabs)

        # меню «Вид» ----------------------------------------------------
        menu_view = self.menuBar().addMenu("&Вид")
        self.act_dark = QAction("Тёмная тема", self, checkable=True)
        self.act_dark.toggled.connect(self.toggle_theme)
        menu_view.addAction(self.act_dark)

        # отдельное меню «Уравнения» -----------------------------------
        menu_eq = self.menuBar().addMenu("&Уравнения")
        for topic in ("Маршруты", "ВП / ВНС", "Сценарии"):
            act = QAction(topic, self)
            act.triggered.connect(lambda _, t=topic: EqDialog(t, self).show())
            menu_eq.addAction(act)

        # восстановление темы ------------------------------------------
        theme = QSettings(CFG_ORG, CFG_APP).value(CFG_KEY, "dark")
        self.act_dark.setChecked(theme == "dark")  # вызовет toggle_theme()

    # ---------- тема --------------------------------------------------
    def toggle_theme(self, dark_on: bool):
        theme = "dark" if dark_on else "light"
        apply_theme(self.qApp, theme)
        QSettings(CFG_ORG, CFG_APP).setValue(CFG_KEY, theme)

    @property
    def qApp(self):
        return QApplication.instance()


# ────────── entry‑point ─────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    apply_theme(app, QSettings(CFG_ORG, CFG_APP).value(CFG_KEY, "dark"))
    PeernetMain().show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
