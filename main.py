import sys
from PyQt5.QtWidgets import QApplication
from src import MainWindow


def main():
    app = QApplication(sys.argv)

    # Optional: Load a stylesheet here for that "Dark Mode" look
    # app.setStyleSheet("QWidget { background-color: #333; color: #EEE; }")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()