import os
import sys
from abc import ABC, abstractmethod
from math import sin, pi, acos, degrees
from random import random, uniform, choice

from PyQt5.QtCore import QTimer, QTime, Qt, QDate, QDir, QUrl, QPointF, QSize, QRect
from PyQt5.QtGui import QFont, QPainter, QBrush, QPen, QColor
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtSvg import QSvgGenerator
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QPushButton, QSpinBox, QMenuBar, QAction, QSizePolicy, \
    QMessageBox
from PyQt5.QtWidgets import QVBoxLayout, QLabel


def smoothen_curve(x: float):
    """f(x) with a smoother beginning and end."""
    # TODO: move to utilities?
    return (sin((x - 1 / 2) * pi) + 1) / 2


class Drawable(ABC):
    """Something that has a draw function that takes a painter to be painted. Also contains some convenience methods
    for drawing the thing and saving it to an SVG."""

    @abstractmethod
    def draw(self, painter: QPainter, width: int, height: int):
        """Draw the drawable onto a painter, given its size."""
        pass

    def save(self, path: str, width: int, height: int):
        """Save the drawable to the specified file, given its size."""
        generator = QSvgGenerator()
        generator.setFileName(path)
        generator.setSize(QSize(width, height))
        generator.setViewBox(QRect(0, 0, width, height))

        painter = QPainter(generator)
        self.draw(painter, width, height)
        painter.end()


class Plant(ABC):
    @abstractmethod
    def generate(self):
        """Generate the parameters necessary for displaying the plant grow."""
        pass


class Tree(Drawable, Plant):
    """A simple tree class that all trees originate from."""
    age = 0
    maxAge = None

    def generateBranches(self, count):
        # positions of branches up the tree, + their orientations (where they're turned towards)
        self.branches = [(uniform(self.width_coefficient * 0.45, self.width_coefficient * 0.55),
                          (((i - 1 / 2) * 2) if count == 2 else (-1 if random() < 0.5 else 1)) * acos(
                              uniform(0.4, 0.6))) for i in
                         range(count)]

    def generate(self):
        # so we don't go from 0 to 1, but from 0.5 to 1
        self.age_coefficient = (self.maxAge + 1) / 2

        # to somewhat randomize the width and the height of the tree stuff
        self.width_coefficient = uniform(0.9, 1.1)
        self.height_coefficient = uniform(0.9, 1.1)

        # generate somewhere between 1 and 2 branches
        self.generateBranches(round(uniform(1, 2 * self.age_coefficient)))

        # the width/height of the main branch
        self.base_width = lambda width: width / 15 * self.width_coefficient * self.age_coefficient
        self.base_height = lambda height: height / 1.7 * self.height_coefficient * self.age_coefficient

        # the width/height of the other branches
        self.branch_width = lambda width: width / 18 * self.width_coefficient * self.age_coefficient
        self.branch_height = lambda height: height / 2.7 * self.height_coefficient * self.age_coefficient

    def set_current_age(self, age: float):
        """Set the current age of the tree (normalized from 0 to 1). Changes the way it is drawn."""
        self.age = age

    def change_max_age(self, maxAge: float):
        """Change the tree's max age, re-generating it in the process."""
        self.maxAge = maxAge
        self.generate()

    def get_adjusted_age(self):
        """Return the age, adjusted to increase to 1 slower."""
        return self.age ** 2

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setBrush(QBrush(QColor(77, 51, 0)))

        # main branch
        painter.drawPolygon(QPointF(-self.base_width(width) * smoothen_curve(self.age), 0),
                            QPointF(self.base_width(width) * smoothen_curve(self.age), 0),
                            QPointF(0, self.base_height(height) * smoothen_curve(self.age)))

        # other branches
        for h, rotation in self.branches:
            painter.save()

            # translate/rotate to the position from which the branches grow
            painter.translate(0, self.base_height(height * h * smoothen_curve(self.age)))
            painter.rotate(degrees(rotation))

            painter.drawPolygon(
                QPointF(-self.branch_width(width) * smoothen_curve(self.get_adjusted_age()) * (1 - h), 0),
                QPointF(self.branch_width(width) * smoothen_curve(self.get_adjusted_age()) * (1 - h), 0),
                QPointF(0, self.branch_height(height) * smoothen_curve(self.get_adjusted_age()) * (1 - h)))

            painter.restore()

    def draw(self, painter: QPainter, width: int, height: int):
        if self.maxAge is None:
            return

        painter.translate(width / 2, height)
        painter.scale(1, -1)

        self._draw(painter, width, height)


class OrangeTree(Tree):

    def generate(self):
        super().generate()

        # orange trees will always have 2 branches
        # it just looks better
        self.generateBranches(2)

        # the size (percentage of width/height) + the position of the circle on the branch
        # the last one is the main ellipse
        self.branch_circles = [(uniform(self.width_coefficient * 0.25, self.width_coefficient * 0.32),
                                uniform(self.width_coefficient * 0.8, self.width_coefficient)) for _ in
                               range(len(self.branches) + 1)]

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(QColor(243, 148, 30)))

        for i, branch in enumerate(self.branches):
            h, rotation = branch

            painter.save()

            # translate/rotate to the position from which the branches grow
            painter.translate(0, self.base_height(height * h * smoothen_curve(self.age)))
            painter.rotate(degrees(rotation))

            top_of_branch = self.branch_height(height) * smoothen_curve(self.get_adjusted_age()) * (1 - h)
            circle_on_branch_position = top_of_branch * self.branch_circles[i][1]
            r = ((width + height) / 2) * self.branch_circles[i][0] * smoothen_curve(self.get_adjusted_age()) * (1 - h)

            painter.setBrush(QBrush(QColor(243, 148, 30)))
            painter.drawEllipse(QPointF(0, circle_on_branch_position), r, r)

            painter.restore()

        top_of_branch = self.base_height(height) * smoothen_curve(self.age)
        circle_on_branch_position = top_of_branch * self.branch_circles[-1][1]
        r = ((width + height) / 2) * self.branch_circles[-1][0] * smoothen_curve(self.get_adjusted_age()) * (1 - h)

        painter.drawEllipse(QPointF(0, circle_on_branch_position), r, r)

        super()._draw(painter, width, height)


class GreenTree(Tree):

    def generate(self):
        super().generate()

        self.green_width = lambda width: width / 3 * self.width_coefficient * self.age_coefficient
        self.green_height = lambda height: height / 1.2 * self.height_coefficient * self.age_coefficient

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(QColor(0, 119, 0)))
        offset = self.base_height(height * 0.3 * smoothen_curve(self.age))
        painter.drawPolygon(QPointF(-self.green_width(width) * smoothen_curve(self.age), offset),
                            QPointF(self.green_width(width) * smoothen_curve(self.age), offset),
                            QPointF(0, min(self.green_height(height) * smoothen_curve(self.age) + offset,
                                           height * 0.95)))

        super()._draw(painter, width, height)


class Canvas(QWidget):
    """A widget that takes a drawable object and constantly draws it."""

    def __init__(self, obj: Drawable = None, parent=None):
        super(Canvas, self).__init__(parent)
        self.object = obj
        self.setFixedSize(300, 300)
        self.setContentsMargins(20, 20, 20, 20)

    def save(self, path: str):
        """Save the drawable object to the specified file."""
        self.object.save(path, self.width(), self.height())

    def set_drawable(self, obj: Drawable):
        """Set the drawable that the canvas draws."""
        self.object = obj

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setClipRect(0, 0, self.width(), self.height())

        if self.object is None:
            return

        # draw the drawable
        painter.save()
        self.object.draw(painter, self.width(), self.height())
        painter.restore()

        # draw a border
        pen = QPen(Qt.SolidLine)
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawRect(QRect(0, 0, self.width(), self.height()))

        painter.end()


class Window(QWidget):

    def __init__(self):
        super().__init__()

        os.chdir(os.path.dirname(os.path.realpath(__file__)))

        self.SOUNDS_FOLDER = "sounds/"
        self.PLANTS_FOLDER = "plants/"

        self.DEFAULT_STUDY_TIME = 45
        self.DEFAULT_BREAK_TIME = 15

        self.MAX_PLANT_AGE = 90  # maximum number of minutes to make the plant optimal in size

        self.MAX_TIME = 180
        self.STEP = 5

        self.INITIAL_TEXT = "Start!"

        self.STUDY_TEXT = "Study"
        self.BREAK_TEXT = "Break"

        self.PAUSE_TEXT = "Pause"
        self.CONTINUE_TEXT = "Continue"

        self.BREAK_COLOR = "#B37700"

        self.menuBar = QMenuBar(self)
        self.options_menu = self.menuBar.addMenu('Options')

        self.sound_action = QAction("&Sound", self, checkable=True, checked=True)
        self.options_menu.addAction(self.sound_action)

        self.menuBar.addAction(
            QAction(
                "&About",
                self,
                triggered=lambda: QMessageBox.information(
                    self,
                    "About",
                    "This application was created by Tomáš Sláma. It is heavily inspired by the Android app Forest, "
                    "but with all of the plants generated procedurally. It's <a href='https://github.com/xiaoxiae/Trimer'>open source</a> and licensed "
                    "under MIT, so do as you please with the code and anything else related to the project.",
                ),
            )
        )

        self.menuBar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)

        main_vertical_layout = QVBoxLayout()
        main_vertical_layout.setContentsMargins(0, 0, 0, 0)

        main_vertical_layout.addWidget(self.menuBar)

        self.main_label = QLabel(self)
        self.main_label.setAlignment(Qt.AlignCenter)
        self.main_label.setFont(QFont('Arial', 120, QFont.Bold))
        self.main_label.setText(self.INITIAL_TEXT)

        self.canvas = Canvas()

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.main_label)
        h_layout.addWidget(self.canvas)

        main_vertical_layout.addLayout(h_layout)

        h_layout = QHBoxLayout()

        self.study_time_spinbox = QSpinBox(self, minimum=1, maximum=self.MAX_TIME, value=self.DEFAULT_STUDY_TIME,
                                           singleStep=self.STEP)
        self.break_time_spinbox = QSpinBox(self, minimum=1, maximum=self.MAX_TIME, value=self.DEFAULT_BREAK_TIME,
                                           singleStep=self.STEP)

        self.study_button = QPushButton(self, text=self.STUDY_TEXT, clicked=self.start)
        self.break_button = QPushButton(self, text=self.BREAK_TEXT, clicked=self.start_break)
        self.break_button.setStyleSheet(f'color:{self.BREAK_COLOR};')

        self.pause_button = QPushButton(self, text=self.PAUSE_TEXT, clicked=self.toggle_pause)
        self.pause_button.setDisabled(True)

        h_layout.addWidget(self.study_time_spinbox)
        h_layout.addWidget(self.break_time_spinbox)
        h_layout.addWidget(self.study_button)
        h_layout.addWidget(self.break_button)
        h_layout.addWidget(self.pause_button)

        main_vertical_layout.addLayout(h_layout)

        self.setLayout(main_vertical_layout)

        self.study_timer = QTimer(self)
        self.study_timer.timeout.connect(self.decrease_remaining_time)
        self.study_timer_frequency = 1 / 60 * 1000
        self.study_timer.setInterval(int(self.study_timer_frequency))

        self.player = QMediaPlayer(self)

        self.show()
        self.canvas.hide()

    def start_break(self):
        """Starts the break, instead of the study."""
        self.start(do_break=True)

    def start(self, do_break=False):
        """The function for starting either the study or break timer (depending on do_break)."""
        self.study_button.setDisabled(not do_break)
        self.break_button.setDisabled(True)

        self.pause_button.setDisabled(False)
        self.pause_button.setText(self.PAUSE_TEXT)

        # study_done is set depending on whether we finished studying (are having a break) or not
        self.study_done = do_break

        self.main_label.setStyleSheet('' if not do_break else f'color:{self.BREAK_COLOR};')

        # the total time to study for (spinboxes are minutes)
        self.leftover_time = (self.study_time_spinbox if not do_break else self.break_time_spinbox).value() * 60
        self.total_time = self.leftover_time

        # don't start showing canvas and growing the plant when we're not studying
        if not do_break:
            self.plant = choice([OrangeTree, GreenTree])()
            self.canvas.set_drawable(self.plant)
            self.plant.change_max_age(min(1, (self.total_time / 60) / self.MAX_PLANT_AGE))
            self.plant.set_current_age(0)
            self.canvas.show()

        self.study_timer.stop()  # it could be running - we could be currently in a break
        self.study_timer.start()

    def toggle_pause(self):
        # stop the timer, if it's running
        if self.study_timer.isActive():
            self.study_timer.stop()
            self.pause_button.setText(self.CONTINUE_TEXT)

        # if not, resume
        else:
            self.study_timer.start()
            self.pause_button.setText(self.PAUSE_TEXT)

    def update_time_label(self, time):
        """Update the text of the time label, given some time in seconds."""
        hours = int(time // 3600)
        minutes = int((time // 60) % 60)
        seconds = int(time % 60)

        # smooth timer: hide minutes/hours if there are none
        if hours == 0:
            if minutes == 0:
                self.main_label.setText(str(seconds))
            else:
                self.main_label.setText(str(minutes) + QTime(0, 0, seconds).toString(":ss"))
        else:
            self.main_label.setText(str(hours) + QTime(0, minutes, seconds).toString(":mm:ss"))

    def play_sound(self, name: str):
        """Play a file from the sound directory. Extension is not included, will be added automatically."""
        if not self.sound_action.isChecked():
            return

        for file in os.listdir(self.SOUNDS_FOLDER):
            # if the file starts with the provided name and only contains an extension after, try to play it
            if file.startswith(name) and file[len(name):][0] == ".":
                path = QDir.current().absoluteFilePath(self.SOUNDS_FOLDER + file)
                url = QUrl.fromLocalFile(path)
                content = QMediaContent(url)
                self.player.setMedia(content)
                self.player.play()

    def decrease_remaining_time(self):
        """Decrease the remaining time by the timer frequency. Updates clock/plant growth."""
        self.update_time_label(self.leftover_time)
        self.leftover_time -= self.study_timer_frequency / 1000

        if self.leftover_time <= 0:
            if self.study_done:
                self.study_timer.stop()

                self.main_label.setStyleSheet('')
                self.break_button.setDisabled(False)
                self.pause_button.setDisabled(True)

                self.play_sound("break_done")

                self.main_label.setText(self.INITIAL_TEXT)
                self.canvas.hide()
            else:
                self.start(do_break=True)

                name = QDate.currentDate().toString(Qt.ISODate) + "|" + QTime.currentTime().toString("hh:mm:ss")

                # TODO: what to do with this?
                # with open("trimer.log", "a") as f:
                #    f.write(name + " - finished studying for " + str(self.total_time // 60) + " minutes." + "\n")

                if not os.path.exists(self.PLANTS_FOLDER):
                    os.mkdir(self.PLANTS_FOLDER)

                self.canvas.save(self.PLANTS_FOLDER + name + ".svg")

                self.play_sound("study_done")
        else:
            # if there is leftover time and we haven't finished studying, grow the plant
            if not self.study_done:
                self.plant.set_current_age(1 - (self.leftover_time / self.total_time))
                self.canvas.update()


app = QApplication(sys.argv)
window = Window()
app.exit(app.exec_())
