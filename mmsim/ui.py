import struct
import sys
from pathlib import Path

import zmq
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QListWidget
from PyQt5.QtWidgets import QSlider
from PyQt5.QtWidgets import QSplitter
from PyQt5.QtWidgets import QStatusBar
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget
from pyqtgraph import GraphicsLayoutWidget

from .graphics import MazeItem
from .mazes import load_maze
from .server import Server


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, host, port, path, parent=None):
        super().__init__(parent)

        self.path = path
        self.maze_files = sorted(
            fname.relative_to(self.path)
            for fname in self.path.glob('**/*.txt')
            if fname.is_file()
        )

        self.setWindowTitle('Micromouse maze simulator')
        self.resize(800, 600)

        self.history = []

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.search = QLineEdit()
        self.search.textChanged.connect(self.filter_mazes)

        self.files = QListWidget()
        self.files.currentItemChanged.connect(self.list_value_changed)

        self.graphics = GraphicsLayoutWidget()
        viewbox = self.graphics.addViewBox()
        viewbox.setAspectLocked()
        self.maze = MazeItem()
        viewbox.addItem(self.maze)

        self.slider = QSlider(QtCore.Qt.Horizontal)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(10)
        self.slider.setTickPosition(QSlider.TicksAbove)
        self.slider.valueChanged.connect(self.slider_value_changed)
        self.reset()

        files_layout = QVBoxLayout()
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.addWidget(self.search)
        files_layout.addWidget(self.files)
        files_widget = QWidget()
        files_widget.setLayout(files_layout)
        graphics_layout = QVBoxLayout()
        graphics_layout.setContentsMargins(0, 0, 0, 0)
        graphics_layout.addWidget(self.graphics)
        graphics_layout.addWidget(self.slider)
        graphics_widget = QWidget()
        graphics_widget.setLayout(graphics_layout)
        central_splitter = QSplitter()
        central_splitter.addWidget(files_widget)
        central_splitter.addWidget(graphics_widget)

        main_layout = QVBoxLayout()
        main_layout.addWidget(central_splitter)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_widget = QWidget()
        main_widget.setLayout(main_layout)

        self.setCentralWidget(main_widget)
        self.filter_mazes('')

        self.server = Server(host=host, port=port)
        self.server.start()

    def filter_mazes(self, text):
        keywords = text.lower().split(' ')
        self.files.clear()
        for fname in self.maze_files:
            for key in keywords:
                if key not in str(fname).lower():
                    break
            else:
                self.files.addItem(str(fname))
        self.files.setCurrentRow(0)

    def list_value_changed(self, after, before):
        if not after:
            return
        self.set_maze(after.text())

    def set_maze(self, fname):
        template_file = Path(fname)
        template = load_maze(self.path / template_file)
        self.maze.reset(template)
        self.reset()

    def reset(self):
        self.history = []
        self.slider.setValue(-1)
        self.slider.setRange(-1, -1)
        self.status.showMessage('Ready')

    def slider_update(self):
        self.slider.setTickInterval(len(self.history) / 10)
        self.slider.setRange(0, len(self.history) - 1)
        self.status_set_slider(self.slider.value())

    def slider_value_changed(self, value):
        self.status_set_slider(value)
        if not len(self.history):
            return
        state = self.history[value]
        position = state[:3]
        discovery = state[3:]
        self.maze.update_position(position)
        self.maze.update_discovery(discovery)

    def status_set_slider(self, value):
        self.status.showMessage('{}/{}'.format(value, len(self.history) - 1))

    def closeEvent(self, event):
        # TODO: join() server?
        pass


def run(host, port, path):
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow(host=host, port=port, path=path)
    main.show()
    sys.exit(app.exec_())
