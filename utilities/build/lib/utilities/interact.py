import sys
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QLabel, QPushButton, QLineEdit, QCheckBox, QMainWindow, QWidget, QColorDialog, QComboBox, QSpinBox
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT
import matplotlib.pyplot as plt
import pandas as pd

class InteractiveGraph(QMainWindow):
    def __init__(self, dataframe, window_title="Graphique"):
        super().__init__()
        self.df = dataframe
        self.setWindowTitle(window_title)
        self.setGeometry(100, 100, 1000, 700)

        # Variables
        self.x_label = "Temps [s]"
        self.y_label = "Y-axis"
        self.y2_label = "Second Y-axis"
        self.show_grid = False

        # Main layout
        self.main_widget = QWidget()
        self.layout = QVBoxLayout(self.main_widget)

        # Matplotlib
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)

        # Controls Layout
        controls_layout = QHBoxLayout()

        # Grid checkbox
        self.grid_checkbox = QCheckBox("Show Grid")
        self.grid_checkbox.stateChanged.connect(self.toggle_grid)
        controls_layout.addWidget(self.grid_checkbox)

        # X-axis label
        controls_layout.addWidget(QLabel("X label:"))
        self.x_label_edit = QLineEdit(self.x_label)
        self.x_label_edit.textChanged.connect(self.update_x_label)
        controls_layout.addWidget(self.x_label_edit)

        # Y-axis label
        controls_layout.addWidget(QLabel("Y label:"))
        self.y_label_edit = QLineEdit(self.y_label)
        self.y_label_edit.textChanged.connect(self.update_y_label)
        controls_layout.addWidget(self.y_label_edit)

        # Y2-axis label
        controls_layout.addWidget(QLabel("Y2 label:"))
        self.y2_label_edit = QLineEdit(self.y2_label)
        self.y2_label_edit.textChanged.connect(self.update_y2_label)
        self.y2_label_edit.setEnabled(False)
        controls_layout.addWidget(self.y2_label_edit)

        self.layout.addLayout(controls_layout)

        # Lists Layout
        lists_layout = QHBoxLayout()

        # List 1: All columns
        self.list_all = QListWidget()
        self.list_all.setDragDropMode(QListWidget.DragDrop)
        self.list_all.setDefaultDropAction(Qt.MoveAction)
        self.list_all.setDragEnabled(True)
        self.list_all.setAcceptDrops(True)
        self.list_all.setDropIndicatorShown(True)
        self.populate_list(self.list_all, self.df.columns)
        self.list_all_label = QLabel("All Columns")
        list_all_layout = QVBoxLayout()
        list_all_layout.addWidget(self.list_all_label)
        list_all_layout.addWidget(self.list_all)
        lists_layout.addLayout(list_all_layout)

        # List 2: Y-axis columns
        self.list_y = QListWidget()
        self.list_y.setDragDropMode(QListWidget.DragDrop)
        self.list_y.setDefaultDropAction(Qt.MoveAction)
        self.list_y.setDragEnabled(True)
        self.list_y.setAcceptDrops(True)
        self.list_y.setDropIndicatorShown(True)
        self.list_y.itemChanged.connect(self.update_plot)
        self.list_y_label = QLabel("Y-Axis")
        list_y_layout = QVBoxLayout()
        list_y_layout.addWidget(self.list_y_label)
        list_y_layout.addWidget(self.list_y)
        lists_layout.addLayout(list_y_layout)

        # List 3: Y2-axis columns
        self.list_y2 = QListWidget()
        self.list_y2.setDragDropMode(QListWidget.DragDrop)
        self.list_y2.setDefaultDropAction(Qt.MoveAction)
        self.list_y2.setDragEnabled(True)
        self.list_y2.setAcceptDrops(True)
        self.list_y2.setDropIndicatorShown(True)
        self.list_y2.itemChanged.connect(self.update_plot)
        self.list_y2_label = QLabel("Y2-Axis")
        list_y2_layout = QVBoxLayout()
        list_y2_layout.addWidget(self.list_y2_label)
        list_y2_layout.addWidget(self.list_y2)
        lists_layout.addLayout(list_y2_layout)

        self.layout.addLayout(lists_layout)
        
        self.setCentralWidget(self.main_widget)

        # Connect events
        self.list_y.itemChanged.connect(self.update_y2_edit_state)
        self.list_y2.itemChanged.connect(self.update_y2_edit_state)

    def populate_list(self, list_widget, items):
        """Populate a list widget with items."""
        for item in items:
            list_item = QListWidgetItem(item)
            list_widget.addItem(list_item)

    def update_y2_edit_state(self):
        """Enable Y2 label editing if Y2-axis list is not empty."""
        self.y2_label_edit.setEnabled(self.list_y2.count() > 0)

    def toggle_grid(self):
        """Toggle grid visibility."""
        self.show_grid = self.grid_checkbox.isChecked()
        self.update_plot()

    def update_x_label(self, text):
        """Update X-axis label."""
        self.x_label = text
        self.update_plot()

    def update_y_label(self, text):
        """Update Y-axis label."""
        self.y_label = text
        self.update_plot()

    def update_y2_label(self, text):
        """Update Y2-axis label."""
        self.y2_label = text
        self.update_plot()

    def update_plot(self):
        """Update the matplotlib plot based on list contents."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Y-axis columns
        for i in range(self.list_y.count()):
            column = self.list_y.item(i).text()
            ax.plot(self.df.index, self.df[column], label=column)

        # Y2-axis columns
        if self.list_y2.count() > 0:
            ax2 = ax.twinx()
            for i in range(self.list_y2.count()):
                column = self.list_y2.item(i).text()
                ax2.plot(self.df.index, self.df[column], linestyle='--', label=column)
            ax2.set_ylabel(self.y2_label)

        ax.set_xlabel(self.x_label)
        ax.set_ylabel(self.y_label)
        ax.grid(self.show_grid)
        ax.legend()
        self.canvas.draw()

if __name__ == "__main__":
    d = {'col1': [0, 1, 2, 3], 'col2': [0, -1, -2, -3], 'col3': [1, 2, 3, 4]}
    df = pd.DataFrame(data=d)
    app = QApplication(sys.argv)
    window = InteractiveGraph(df)
    window.show()
    sys.exit(app.exec_())
