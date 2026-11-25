import sys
import traceback
from pathlib import Path


def data_dir() -> Path:
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    return base


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except ImportError:
        print("Не установлен PySide6. Выполните:  pip install -r requirements.txt")
        return 1

    from core.db import RecordsDB
    from ui.main_window import MainWindow
    from ui.theme import QSS

    app = QApplication(sys.argv)
    app.setApplicationName("Шагай наадан")
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    QLocale.setDefault(QLocale(QLocale.Russian, QLocale.Russia))
    app._translators = []
    for base in ("qtbase_ru", "qt_ru"):
        tr = QTranslator(app)
        if tr.load(base, QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
            app.installTranslator(tr)
            app._translators.append(tr)
    app.setStyleSheet(QSS)

    def excepthook(etype, value, tb):
        traceback.print_exception(etype, value, tb)
        QMessageBox.critical(None, "Непредвиденная ошибка", f"{etype.__name__}: {value}")

    sys.excepthook = excepthook

    try:
        db = RecordsDB(data_dir() / "records.db")
    except Exception as e:
        QMessageBox.critical(None, "База данных", f"Не удалось открыть файл рекордов:\n{e}\n\n"
                             "Рекорды будут храниться только до закрытия игры.")
        db = RecordsDB(":memory:")

    win = MainWindow(db)
    win.resize(1180, 780)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
