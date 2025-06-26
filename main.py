# main.py  — переключаемые Light / Dark темы
from __future__ import annotations
import sys, pathlib
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QAction, QMenu, QMessageBox
)
from PyQt5.QtGui      import QIcon, QFont
from PyQt5.QtCore     import QSettings
import qtawesome as qta         # pip install qtawesome
import qdarkstyle               # pip install qdarkstyle

from routes_tab import RoutesTab
from vp_tab     import VPTab
from mss_tab    import MSSTab


# ───────────────────  util  ───────────────────────────────────────────
CFG_ORG  = "PeernetLab"
CFG_APP  = "Peernet-Calc"
CFG_KEY  = "theme"              # "dark" / "light"

def awesome(name: str, color: str) -> QIcon:
    return qta.icon(name, color=color)


def build_stylesheet(theme: str) -> str:
    """возвращает полный CSS для 'dark' или 'light'."""
    if theme == "dark":
        base = qdarkstyle.load_stylesheet(qt_api="pyqt5")
        extra_fg   = "#eaeaea"
        extra_back = "#2c2e3c"
    else:                         # light
        base = """
        QWidget      { background:#f7f8fa; color:#2b2b2b; }
        QGroupBox    { border:1px solid #c2c4cf; margin-top:6px; }
        QGroupBox::title { subcontrol-origin: margin; left:8px; padding:0 3px; }
        QPushButton  { background:#00bcd4; color:#fff; border-radius:4px; height:28px; }
        QPushButton:hover { background:#26cbe4; }
        QHeaderView::section { background:#e1e3ec; padding:6px; font-weight:600; }
        QTabBar::tab { min-width:120px; height:30px; padding:4px 12px;
                       background:#c9ccd9; color:#2b2b2b; border:0; }
        QTabBar::tab:selected {
                       background:#00bcd4; color:#ffffff;
                       border-top-left-radius:6px; border-top-right-radius:6px; }
        """
        extra_fg = "#2b2b2b"
        extra_back = "#c9ccd9"

    extra = f"""
    /* общие доп. правки */
    * {{ font:11pt "Segoe UI"; }}
    QTableView::item {{ padding:4px; }}
    """
    return base + extra


def apply_theme(app: QApplication, theme: str) -> None:
    app.setStyleSheet(build_stylesheet(theme))
    app.setFont(QFont("Segoe UI", 11))


# ───────────────────  Main Window  ────────────────────────────────────
class PeernetMain(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Peernet-Calc  •  лаборатория")
        self.resize(1100, 700)
        self.setWindowIcon(awesome("fa5s.network-wired", "#00bcd4"))

        # tabs
        tabs = QTabWidget(documentMode=True)
        tabs.addTab(RoutesTab(), awesome("fa5s.route",          "#ff5252"), "Маршруты")
        tabs.addTab(VPTab(),     awesome("fa5s.shield-alt",     "#ffc857"), "ВП / ВНС")
        tabs.addTab(MSSTab(),    awesome("fa5s.project-diagram","plum"),     "Сценарии")
        self.setCentralWidget(tabs)

        # меню «Вид ▸ Тёмная тема»
        view_menu: QMenu = self.menuBar().addMenu("&Вид")
        self.act_dark = QAction("Тёмная тема", self, checkable=True)
        self.act_dark.toggled.connect(self.toggle_theme)
        view_menu.addAction(self.act_dark)

        # восстановить сохранённую тему
        settings = QSettings(CFG_ORG, CFG_APP)
        theme = settings.value(CFG_KEY, "dark")
        self.act_dark.setChecked(theme == "dark")   # вызовет toggle_theme()


    # ----------  theme switch  ----------------------------------------
    def toggle_theme(self, dark_on: bool) -> None:
        theme = "dark" if dark_on else "light"
        apply_theme(self.qApp, theme)               # qApp = QApplication.instance()
        QSettings(CFG_ORG, CFG_APP).setValue(CFG_KEY, theme)


    # небольшая обёртка, чтобы не искать QApplication.instance()
    @property
    def qApp(self) -> QApplication:
        return QApplication.instance()


# ───────────────────  entry-point  ────────────────────────────────────
def main() -> None:
    app = QApplication(sys.argv)

    # первый запуск — тёмная тема
    settings = QSettings(CFG_ORG, CFG_APP)
    cur_theme = settings.value(CFG_KEY, "dark")
    apply_theme(app, cur_theme)

    win = PeernetMain()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
