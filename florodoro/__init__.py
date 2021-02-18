import argparse
import os
import pickle
import sys
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from functools import partial
from math import sin, pi, acos, degrees
from random import random, uniform, choice, randint
from typing import List, Optional

import qtawesome as qta
import yaml
from PyQt5.QtChart import QChart, QChartView, QBarSet, QBarCategoryAxis, QStackedBarSeries
from PyQt5.QtCore import QTimer, QTime, Qt, QDir, QUrl, QPointF, QSize, QRect, QRectF, QMargins
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor, QIcon, QPainterPath, QKeyEvent
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtSvg import QSvgGenerator
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QPushButton, QSpinBox, QAction, QSizePolicy, \
    QMessageBox, QMenuBar, QStackedLayout, QSlider, QFileDialog, QGridLayout, QFrame, QWidgetAction
from PyQt5.QtWidgets import QVBoxLayout, QLabel
from plyer import notification


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


class Plant(Drawable):
    age = 0  # every plant has a current age (from 0 to 1)
    maxAge = None  # and a max age (from 0 to 1)

    green_color = QColor(0, 119, 0)
    white_color = QColor(255, 255, 255)

    def set_current_age(self, age: float):
        """Set the current age of the plant (normalized from 0 to 1). Changes the way it is drawn."""
        self.age = age

    def set_max_age(self, maxAge: float):
        """Change the plant's max age, re-generating it in the process."""
        self.maxAge = maxAge
        self.generate()

    def get_adjusted_age(self):
        """Return the age, adjusted to increase to 1 slower (some parts of the plant grow slower than others)."""
        return self.age ** 2

    def draw(self, painter: QPainter, width: int, height: int):
        if self.maxAge is None:
            return

        w = min(width, height)
        h = min(width, height)

        # position to the bottom center of the canvas
        painter.translate(width / 2, height)
        painter.scale(1, -1)

        self._draw(painter, w, h)

    def generate(self):
        # so we don't go from 0 to 1, but from 0.5 to 1
        # a coefficient to multiply all parts of the given plant by that depend on its maximum age
        self.age_coefficient = (self.maxAge + 1) / 2

        # make the sizes somewhat random and organic
        self.deficit_coefficient = uniform(0.9, 1)


class Flower(Plant):

    def generate_leafs(self, count):
        """Generate the leafs of the flower."""
        # position / size coefficient (smaller/larger leafs) / rotation
        self.leafs = [(uniform(self.deficit_coefficient * 0.25, self.deficit_coefficient * 0.40), uniform(0.9, 1.1),
                       (((i - 1 / 2) * 2) if count == 2 else (-1 if random() < 0.5 else 1))) for i in
                      range(count)]

    def flower_center_x(self, width):
        """The x coordinate of the center of the flower."""
        return width / 9 * self.x_coefficient

    def flower_center_y(self, height):
        """The y coordinate of the center of the flower."""
        return height / 2.5 * self.deficit_coefficient * self.age_coefficient

    def leaf_size(self, width):
        """The size of the leaf."""
        return width / 7 * self.deficit_coefficient * self.age_coefficient

    def generate(self):
        super().generate()

        # the ending x position of the flower -- so it tilts one way or another
        self.x_coefficient = uniform(0.4, 1) * (-1 if random() < 0.5 else 1)

        self.generate_leafs(2)

        self.stem_width = uniform(3.5, 4) * self.age_coefficient

    def _draw(self, painter: QPainter, width: int, height: int):
        self.x = self.flower_center_x(width) * smoothen_curve(self.age)
        self.y = self.flower_center_y(height) * smoothen_curve(self.age)

        painter.setPen(QPen(self.green_color, self.stem_width * smoothen_curve(self.age)))

        # draw the stem
        path = QPainterPath()
        path.quadTo(0, self.y * 0.6, self.x, self.y)
        painter.drawPath(path)

        # draw the leaves
        for position, coefficient, rotation in self.leafs:
            painter.save()

            # find the point on the stem and rotate the leaf accordingly
            painter.translate(path.pointAtPercent(position))
            painter.rotate(degrees(rotation))

            # rotate according to where the flower is leaning towards
            if self.y != 0:
                painter.rotate(-degrees(sin(self.x / self.y)))

            # make it so both leaves are facing the same direction
            if rotation < 0:
                painter.scale(-1, 1)

            painter.setBrush(QBrush(self.green_color))
            painter.setPen(QPen(0))

            # draw the leaf
            leaf = QPainterPath()
            leaf.setFillRule(Qt.WindingFill)
            ls = self.leaf_size(width) * smoothen_curve(self.age) ** 2 * coefficient
            leaf.quadTo(0.4 * ls, 0.5 * ls, 0, ls)
            leaf.cubicTo(0, 0.5 * ls, -0.4 * ls, 0.4 * ls, 0, 0)
            painter.drawPath(leaf)

            painter.restore()


class CircularFlower(Flower):
    """A class for creating a flower."""

    # colors of the Florodoro logo
    colors = [
        QColor(139, 139, 255),  # blue-ish
        QColor(72, 178, 173),  # green-ish
        QColor(255, 85, 85),  # red-ish
        QColor(238, 168, 43),  # orange-ish
        QColor(226, 104, 155),  # pink-ish
    ]

    def triangle_pellet(self, painter: QPainter, pellet_size):
        """A pellet that is pointy and triangular (1st in logo)"""
        pellet_size *= 1.5

        pellet = QPainterPath()
        pellet.setFillRule(Qt.WindingFill)
        pellet.quadTo(0.9 * pellet_size, 0.5 * pellet_size, 0, pellet_size)
        pellet.quadTo(-0.5 * pellet_size, 0.4 * pellet_size, 0, 0)
        painter.drawPath(pellet)

    def circular_pellet(self, painter: QPainter, pellet_size):
        """A perfectly circular pellet (2nd in logo)."""
        painter.drawEllipse(QRectF(0, 0, pellet_size, pellet_size))

    def round_pellet(self, painter: QPainter, pellet_size):
        """A pellet that is round but not a circle (3rd in the logo)."""
        pellet_size *= 1.3

        pellet = QPainterPath()
        pellet.setFillRule(Qt.WindingFill)

        for c in [1, -1]:
            pellet.quadTo(c * pellet_size * 0.8, pellet_size * 0.9, 0, pellet_size if c != -1 else 0)

        painter.drawPath(pellet)

    def dip_pellet(self, painter: QPainter, pellet_size):
        """A pellet that has a dip in the middle (4th in the logo)."""
        pellet_size *= 1.2

        pellet = QPainterPath()
        pellet.setFillRule(Qt.WindingFill)

        for c in [1, -1]:
            pellet.quadTo(c * pellet_size, pellet_size * 1.4, 0, pellet_size if c != -1 else 0)

        painter.drawPath(pellet)

    def pellet_size(self, width):
        """Return the size of the pellet."""
        return width / 9 * self.deficit_coefficient * self.age_coefficient

    def generate(self):
        super().generate()

        # color of the flower
        self.color = choice(self.colors)

        self.number_of_pellets = randint(5, 7)

        # the center of the plant is smaller, compared to other pellet sizes
        self.center_pellet_smaller_coefficient = uniform(0.75, 0.85)

        self.pellet_drawing_function = choice(
            [self.circular_pellet, self.triangle_pellet, self.dip_pellet, self.round_pellet])

        # the m and n pellets don't look good with any other number of leafs (other than 5)
        if self.pellet_drawing_function in [self.dip_pellet, self.round_pellet]:
            self.number_of_pellets = 5

    def _draw(self, painter: QPainter, width: int, height: int):
        super()._draw(painter, width, height)

        painter.save()

        # move to the position of the flower
        painter.translate(self.x, self.y)

        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self.color))

        pellet_size = self.pellet_size(width) * smoothen_curve(self.age)

        # draw each of the pellets
        for i in range(self.number_of_pellets):
            self.pellet_drawing_function(painter, pellet_size)
            painter.rotate(360 / self.number_of_pellets)

        # the center of the flower
        painter.setBrush(QBrush(self.white_color))
        pellet_size *= self.center_pellet_smaller_coefficient
        painter.drawEllipse(QRectF(-pellet_size / 2, -pellet_size / 2, pellet_size, pellet_size))

        painter.restore()


class Tree(Plant):
    """A simple tree class that all trees originate from."""
    brown_color = QColor(77, 51, 0)

    def generateBranches(self, count):
        # positions of branches up the tree, + their orientations (where they're turned towards)
        self.branches = [(uniform(self.deficit_coefficient * 0.45, self.deficit_coefficient * 0.55),
                          (((i - 1 / 2) * 2) if count == 2 else (-1 if random() < 0.5 else 1)) * acos(
                              uniform(0.4, 0.6))) for i in
                         range(count)]

    def base_width(self, width):
        return width / 15 * self.deficit_coefficient * self.age_coefficient

    def base_height(self, height):
        return height / 1.7 * self.deficit_coefficient * self.age_coefficient

    def branch_width(self, width):
        return width / 18 * self.deficit_coefficient * self.age_coefficient

    def branch_height(self, height):
        return height / 2.7 * self.deficit_coefficient * self.age_coefficient

    def generate(self):
        super().generate()

        # generate somewhere between 1 and 2 branches
        self.generateBranches(round(uniform(1, 2 * self.age_coefficient)))

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setBrush(QBrush(self.brown_color))

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


class OrangeTree(Tree):
    """A tree with orange ellipses as leafs."""
    orange_color = QColor(243, 148, 30)

    def generate(self):
        super().generate()

        # orange trees will always have 2 branches
        # it just looks better
        self.generateBranches(2)

        # the size (percentage of width/height) + the position of the circle on the branch
        # the last one is the main ellipse
        self.branch_circles = [(uniform(self.deficit_coefficient * 0.30, self.deficit_coefficient * 0.37),
                                uniform(self.deficit_coefficient * 0.9, self.deficit_coefficient)) for _ in
                               range(len(self.branches) + 1)]

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self.orange_color))

        for i, branch in enumerate(self.branches):
            h, rotation = branch

            painter.save()

            # translate/rotate to the position from which the branches grow
            painter.translate(0, self.base_height(height * h * smoothen_curve(self.age)))
            painter.rotate(degrees(rotation))

            top_of_branch = self.branch_height(height) * smoothen_curve(self.get_adjusted_age()) * (1 - h)
            circle_on_branch_position = top_of_branch * self.branch_circles[i][1]

            r = ((width + height) / 2) * self.branch_circles[i][0] * smoothen_curve(self.get_adjusted_age()) * (
                    1 - h) * self.age_coefficient

            painter.setBrush(QBrush(self.orange_color))
            painter.drawEllipse(QPointF(0, circle_on_branch_position), r, r)

            painter.restore()

        top_of_branch = self.base_height(height) * smoothen_curve(self.age)
        circle_on_branch_position = top_of_branch * self.branch_circles[-1][1]

        # make the main ellipse slightly larger
        increase_size = 1.3
        r = ((width + height) / 2) * self.branch_circles[-1][0] * smoothen_curve(self.get_adjusted_age()) * (
                1 - h) * self.age_coefficient * increase_size

        painter.drawEllipse(QPointF(0, circle_on_branch_position), r, r)

        super()._draw(painter, width, height)


class GreenTree(Tree):
    """A tree with a green triangle as leafs."""

    def green_width(self, width):
        return width / 3.2 * self.deficit_coefficient * self.age_coefficient

    def green_height(self, height):
        return height / 1.5 * self.deficit_coefficient * self.age_coefficient

    def offset(self, height):
        return min(height * .95, self.base_height(height * 0.3 * smoothen_curve(self.age)))

    def generate(self):
        super().generate()

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self.green_color))

        painter.drawPolygon(QPointF(-self.green_width(width) * smoothen_curve(self.age), self.offset(height)),
                            QPointF(self.green_width(width) * smoothen_curve(self.age), self.offset(height)),
                            QPointF(0, self.green_height(height) * smoothen_curve(self.age) + self.offset(height)))

        super()._draw(painter, width, height)


class DoubleGreenTree(GreenTree):
    """A tree with a double green triangle as leafs."""

    def second_green_width(self, width):
        return width / 3.5 * self.deficit_coefficient * self.age_coefficient

    def second_green_height(self, height):
        return height / 2.4 * self.deficit_coefficient * self.age_coefficient

    def generate(self):
        super().generate()

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self.green_color))

        offset = self.base_height(height * 0.3 * smoothen_curve(self.age))
        second_offset = (self.green_height(height) - self.second_green_height(height)) * smoothen_curve(self.age)

        painter.drawPolygon(
            QPointF(-self.second_green_width(width) * smoothen_curve(self.age) ** 2, offset + second_offset),
            QPointF(self.second_green_width(width) * smoothen_curve(self.age) ** 2, offset + second_offset),
            QPointF(0, min(
                self.second_green_height(height) * smoothen_curve(self.age) + offset + second_offset,
                height * 0.95)))

        super()._draw(painter, width, height)


class Canvas(QWidget):
    """A widget that takes a drawable object and constantly draws it."""

    def __init__(self, *args, **kwargs):
        super(Canvas, self).__init__(*args, **kwargs)
        self.object = None

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

        painter.end()


class Statistics(QWidget):
    """A statistics widget that displays information about studied time, shows grown plants, etc..."""

    def __init__(self, history, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.history = history

        chart = self.generate_chart()

        chart.setMinimumWidth(400)
        chart.setMinimumHeight(200)

        image_layout = QVBoxLayout()

        self.plant_study = None  # the study record the plant is a part of
        self.plant: Optional[Plant] = None  # the plant being displayed

        self.plant_date_label = QLabel(self)
        self.plant_date_label.setAlignment(Qt.AlignLeft)

        self.plant_duration_label = QLabel(self)
        self.plant_duration_label.setAlignment(Qt.AlignRight)

        label_layout = QHBoxLayout()
        label_layout.addWidget(self.plant_date_label)
        label_layout.addWidget(self.plant_duration_label)

        self.canvas = Canvas(self)
        self.canvas.setMinimumWidth(200)
        self.canvas.setMinimumHeight(200)

        stacked_layout = QVBoxLayout()
        stacked_layout.addLayout(label_layout)
        stacked_layout.addWidget(self.canvas)

        image_control = QHBoxLayout()

        text_color = self.palette().text().color()
        self.left_button = QPushButton(self, clicked=self.left, icon=qta.icon('fa5s.angle-left', color=text_color))
        self.age_slider = QSlider(Qt.Horizontal, minimum=0, maximum=1000, value=1000,
                                  valueChanged=self.sliderValueChanged)
        self.right_button = QPushButton(self, clicked=self.right, icon=qta.icon('fa5s.angle-right', color=text_color))
        self.save_button = QPushButton(self, clicked=self.save, icon=qta.icon('fa5s.download', color=text_color))

        image_control.addWidget(self.left_button)
        image_control.addWidget(self.right_button)
        image_control.addSpacing(10)
        image_control.addWidget(self.age_slider)
        image_control.addSpacing(10)
        image_control.addWidget(self.save_button)

        image_layout.addLayout(stacked_layout)
        image_layout.addLayout(image_control)
        image_layout.setContentsMargins(10, 10, 10, 10)

        separator = QFrame()
        separator.setStyleSheet(f"background-color: {self.palette().text().color().name()}")
        separator.setFixedWidth(1)

        main_layout = QGridLayout()
        main_layout.setHorizontalSpacing(20)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(2, 0)
        main_layout.addWidget(chart, 0, 0)
        main_layout.addWidget(separator, 0, 1)
        main_layout.addLayout(image_layout, 0, 2)

        self.setLayout(main_layout)

        self.move()

        self.refresh()

    def generate_chart(self):
        """Generate the bar graph."""
        # TODO: start here when custom tags are implemented
        self.tags = [QBarSet(tag) for tag in ["Study"]]

        series = QStackedBarSeries()

        for set in self.tags:
            series.append(set)

        self.chart = QChart()
        self.chart.addSeries(series)
        self.chart.setTitle("Total time studied (minutes per day)")

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        axis = QBarCategoryAxis()
        axis.append(days)

        self.chart.createDefaultAxes()
        self.chart.setAxisX(axis, series)
        self.chart.legend().setAlignment(Qt.AlignBottom)
        self.chart.legend().setVisible(False)
        self.chart.setTheme(QChart.ChartThemeQt)
        self.chart.setBackgroundVisible(False)
        self.chart.setBackgroundRoundness(0)
        self.chart.setMargins(QMargins(0, 0, 0, 0))
        self.chart.setTitleBrush(QBrush(self.palette().text().color()))

        yAxis = self.chart.axes(Qt.Vertical)[0]
        yAxis.setGridLineVisible(False)
        yAxis.setLabelFormat("%d")
        yAxis.setLinePenColor(self.palette().text().color())
        yAxis.setLabelsColor(self.palette().text().color())

        xAxis = self.chart.axes(Qt.Horizontal)[0]
        xAxis.setGridLineVisible(False)
        xAxis.setLinePenColor(self.palette().text().color())
        xAxis.setLabelsColor(self.palette().text().color())

        chartView = QChartView(self.chart)
        chartView.setRenderHint(QPainter.Antialiasing)

        return chartView

    def sliderValueChanged(self):
        """Called when the slider value has changed."""
        if self.plant is not None:
            self.plant.set_current_age(self.age_slider.value() / self.age_slider.maximum())
            self.canvas.update()

    def refresh(self):
        """Refresh the labels."""
        # clear tag values
        for tag in self.tags:
            tag.remove(0, tag.count())

        study_minutes = [0] * 7
        for study in self.history.get_studies():
            # TODO: don't just crash
            study_minutes[study["date"].weekday()] += study["duration"]

        for minutes in study_minutes:
            self.tags[0] << minutes

        # manually set
        yAxis = self.chart.axes(Qt.Vertical)[0]
        yAxis.setRange(0, max(study_minutes))

    def left(self):
        """Move to the left (newer) picture."""
        self.move(-1)

    def right(self):
        """Move to the right (older) picture."""
        self.move(1)

    def move(self, delta: int = 0):
        """Move to another plant by delta. If no plant is currently being displayed, pick the latest one."""
        studies = self.history.get_studies()

        # if there are no plants to display, don't do anything
        if len(studies) == 0:
            return

        # if no plant is being displayed or 0 is provided, pick the last one
        if self.plant is None or delta == 0:
            index = -1

        # if one is, find it and move by delta
        else:
            current_index = self.history.get_studies().index(self.plant_study)

            index = max(min(current_index + delta, len(studies) - 1), 0)

        # TODO: check for correct formatting, don't just crash if it's wrong
        self.plant = pickle.loads(studies[index]["plant"])
        self.plant_study = studies[index]

        # TODO: check for correct formatting, don't just crash if it's wrong
        self.plant_date_label.setText(self.plant_study["date"].strftime("%-d/%-m/%Y"))
        self.plant_duration_label.setText(f"{int(self.plant_study['duration'])} minutes")

        self.canvas.set_drawable(self.plant)
        self.sliderValueChanged()  # it didn't, but the code should act as if it did

    def save(self):
        """Save the current state of the plant to a file."""
        if self.plant is not None:
            name, _ = QFileDialog.getSaveFileName(self, 'Save File', "", "SVG files (*.svg)")

            if not name.endswith(".svg"):
                name += ".svg"

            self.plant.save(name, 1000, 1000)


class History:
    """A class for working with the Florodoro history."""

    def __init__(self, path):
        self.path = path

        self.history = {}
        self.load()

    def save(self):
        """Save the current history to the history file."""
        with open(self.path, "w") as f:
            f.write(yaml.dump(self.history))

    def load(self):
        """Load the history from the history file."""
        if os.path.exists(self.path):
            with open(self.path) as file:
                self.history = yaml.load(file, Loader=yaml.FullLoader)

                # ignore the result if isn't a dictionary
                if not isinstance(self.history, dict):
                    self.history = {}

        # create the activities that we save
        for activity in ("breaks", "studies"):
            if activity not in self.history:
                self.history[activity] = []

    def add_break(self, date, duration: float):
        """Add a break to the history."""
        self.history["breaks"].append({"date": date, "duration": duration})
        self.save()

    def add_study(self, date, duration: float, current_cycle: int, total_cycles: int, plant: Plant):
        """Add a break to the history."""
        self.history["studies"].append({
            "date": date,
            "duration": duration,
            "current_cycle": current_cycle,
            "total_cycles": total_cycles,
            "plant": pickle.dumps(plant)
        })
        self.save()

    def total_studied_time(self) -> float:
        """Return the total minutes of studied time."""
        return self._total_time("studies")

    def total_break_time(self) -> float:
        """Return the total minutes of studied time."""
        return self._total_time("breaks")

    def _total_time(self, activity_type: str):
        """Calculate the total time of something."""
        # TODO: check for correct formatting, don't just crash if it's wrong
        total = 0
        for study in self.history[activity_type]:
            total += study["duration"]

        return total

    def total_plants_grown(self) -> int:
        """Return the total number of plants grown."""
        # TODO: check for correct formatting, don't just crash if it's wrong
        count = 0
        for study in self.get_studies():
            if study["plant"] is not None:
                count += 1

        return count

    def get_studies(self, sort=True) -> List:
        """Return all of the studies. Possibly sort on date."""
        studies = self.history["studies"]

        # TODO: check for correct formatting, don't just crash if it's wrong
        if sort:
            studies = sorted(studies, key=lambda x: x["date"])

        return studies

    def get_breaks(self) -> List:
        """Return all of the studies."""
        return self.history["breaks"]


class SpacedQWidget(QWidget):
    """A dummy class for adding spacing to the left and right of a QWidget. Used in a QMenuBar's QWidgetAction, because
    I haven't found a way to add spacing to the left/right of a QSlider."""

    def __init__(self, widget: QWidget, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QHBoxLayout()
        layout.addSpacing(5)
        layout.addWidget(widget)
        layout.addSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)


class Florodoro(QWidget):

    def parseArguments(self):
        parser = argparse.ArgumentParser(
            description="A pomodoro timer that grows procedurally generated trees and flowers while you're studying.",
        )

        parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            help="run the app in debug mode",
        )

        return parser.parse_args()

    def __init__(self):
        super().__init__()

        arguments = self.parseArguments()

        self.DEBUG = arguments.debug

        os.chdir(os.path.dirname(os.path.realpath(__file__)))

        self.MIN_WIDTH = 600
        self.MIN_HEIGHT = 350

        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMinimumHeight(self.MIN_HEIGHT)

        self.ROOT_FOLDER = os.path.expanduser("~/.florodoro/")

        self.HISTORY_FILE_PATH = self.ROOT_FOLDER + "history" + ("" if not self.DEBUG else "-debug") + ".yaml"
        self.CONFIGURATION_FILE_PATH = self.ROOT_FOLDER + "config" + ("" if not self.DEBUG else "-debug") + ".yaml"

        self.history = History(self.HISTORY_FILE_PATH)

        self.SOUNDS_FOLDER = "sounds/"
        self.PLANTS_FOLDER = "plants/"
        self.IMAGE_FOLDER = "images/"

        self.TEXT_COLOR = self.palette().text().color()
        self.BREAK_COLOR = "#B37700"

        self.APP_NAME = "Florodoro"

        self.STUDY_ICON = qta.icon('fa5s.book', color=self.TEXT_COLOR)
        self.BREAK_ICON = qta.icon('fa5s.coffee', color=self.BREAK_COLOR)
        self.CONTINUE_ICON = qta.icon('fa5s.play', color=self.TEXT_COLOR)
        self.PAUSE_ICON = qta.icon('fa5s.pause', color=self.TEXT_COLOR)
        self.RESET_ICON = qta.icon('fa5s.undo', color=self.TEXT_COLOR)

        self.PLANTS = [GreenTree, DoubleGreenTree, OrangeTree, CircularFlower]
        self.PLANT_NAMES = ["Spruce", "Double spruce", "Maple", "Flower"]

        self.DEFAULT_STUDY_TIME = 45
        self.DEFAULT_BREAK_TIME = 15

        self.MAX_PLANT_AGE = 90  # maximum number of minutes to make the plant optimal in size

        self.WIDGET_SPACING = 10

        self.MAX_TIME = 180
        self.STEP = 5

        self.INITIAL_TEXT = "Start!"

        self.menuBar = QMenuBar(self)
        self.presets_menu = self.menuBar.addMenu('&Presets')

        self.presets_menu.addAction(
            QAction("Classic (25 : 5 : 4)", self, triggered=partial(self.load_preset, 25, 5, 4)))
        self.presets_menu.addAction(
            QAction("Extended (45 : 10 : 2)", self, triggered=partial(self.load_preset, 45, 10, 2)))

        self.options_menu = self.menuBar.addMenu('&Options')

        self.notify_menu = self.options_menu.addMenu("&Notify")

        self.sound_action = QAction("&Sound", self, checkable=True, checked=not self.DEBUG,
                                    triggered=lambda _: self.volume_slider.setDisabled(
                                        not self.sound_action.isChecked()))

        self.notify_menu.addAction(self.sound_action)

        self.volume_slider = QSlider(Qt.Horizontal, minimum=0, maximum=100, value=85)
        slider_action = QWidgetAction(self)
        slider_action.setDefaultWidget(SpacedQWidget(self.volume_slider))
        self.notify_menu.addAction(slider_action)

        self.popup_action = QAction("&Pop-up", self, checkable=True, checked=True)
        self.notify_menu.addAction(self.popup_action)

        self.menuBar.addAction(
            QAction(
                "&Statistics",
                self,
                triggered=lambda: self.statistics.show() if self.statistics.isHidden() else self.statistics.hide()
            )
        )

        self.menuBar.addAction(
            QAction(
                "&About",
                self,
                triggered=lambda: QMessageBox.information(
                    self,
                    "About",
                    "This application was created by Tomáš Sláma. It is heavily inspired by the Android app Forest, "
                    "but with all of the plants generated procedurally. It's <a href='https://github.com/xiaoxiae/Florodoro'>open source</a> and licensed "
                    "under MIT, so do as you please with the code and anything else related to the project.",
                ),
            )
        )

        self.plant_menu = self.options_menu.addMenu("&Plants")

        self.overstudy_action = QAction("Overstudy", self, checkable=True)
        self.options_menu.addAction(self.overstudy_action)

        self.plant_images = []
        self.plant_checkboxes = []

        # dynamically create widgets for each plant
        for plant, name in zip(self.PLANTS, self.PLANT_NAMES):
            self.plant_images.append(tempfile.NamedTemporaryFile(suffix=".svg"))
            tmp = plant()
            tmp.set_max_age(1)
            tmp.set_current_age(1)
            tmp.save(self.plant_images[-1].name, 200, 200)

            setattr(self.__class__, name,
                    QAction(self, icon=QIcon(self.plant_images[-1].name), text=name, checkable=True, checked=True))

            action = getattr(self.__class__, name)

            self.plant_menu.addAction(action)
            self.plant_checkboxes.append(action)

        # the current plant that we're growing
        # if set to none, no plant is growing
        self.plant = None

        self.menuBar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)

        main_vertical_layout = QVBoxLayout(self)
        main_vertical_layout.setContentsMargins(0, 0, 0, 0)
        main_vertical_layout.setSpacing(0)
        main_vertical_layout.addWidget(self.menuBar)

        self.canvas = Canvas(self)

        self.statistics = Statistics(self.history)

        font = self.font()
        font.setPointSize(100)

        self.main_label = QLabel(self, alignment=Qt.AlignCenter)
        self.main_label.setFont(font)
        self.main_label.setText(self.INITIAL_TEXT)

        font.setPointSize(26)
        self.cycle_label = QLabel(self)
        self.cycle_label.setAlignment(Qt.AlignTop)
        self.cycle_label.setMargin(20)
        self.cycle_label.setFont(font)

        main_horizontal_layout = QHBoxLayout(self)

        self.study_time_spinbox = QSpinBox(self, prefix="Study for: ", suffix="min.", minimum=1, maximum=self.MAX_TIME,
                                           value=self.DEFAULT_STUDY_TIME,
                                           singleStep=self.STEP)

        self.break_time_spinbox = QSpinBox(self, prefix="Break for: ", suffix="min.", minimum=1, maximum=self.MAX_TIME,
                                           value=self.DEFAULT_BREAK_TIME,
                                           singleStep=self.STEP,
                                           styleSheet=f'color:{self.BREAK_COLOR};')

        self.cycles_spinbox = QSpinBox(self, prefix="Cycles: ", minimum=1, value=1)

        # keep track of remaining number of cycles and the starting number of cycles
        self.remaining_cycles = 0
        self.total_cycles = 0

        # whether we're currently studying
        self.is_study_ongoing = False

        # whether we notified the user already during overstudy
        self.already_notified_during_overstudy = False

        stacked_layout = QStackedLayout(self, stackingMode=QStackedLayout.StackAll)
        stacked_layout.addWidget(self.main_label)
        stacked_layout.addWidget(self.cycle_label)
        stacked_layout.addWidget(self.canvas)

        main_vertical_layout.addLayout(stacked_layout)

        self.setStyleSheet("")

        self.study_button = QPushButton(self, clicked=self.start, icon=self.STUDY_ICON)
        self.break_button = QPushButton(self, clicked=self.start_break, icon=self.BREAK_ICON)
        self.pause_button = QPushButton(self, clicked=self.toggle_pause, icon=self.PAUSE_ICON)
        self.reset_button = QPushButton(self, clicked=self.reset, icon=self.RESET_ICON)

        main_horizontal_layout.addWidget(self.study_time_spinbox)
        main_horizontal_layout.addWidget(self.break_time_spinbox)
        main_horizontal_layout.addWidget(self.cycles_spinbox)
        main_horizontal_layout.addWidget(self.study_button)
        main_horizontal_layout.addWidget(self.break_button)
        main_horizontal_layout.addWidget(self.pause_button)
        main_horizontal_layout.addWidget(self.reset_button)

        main_vertical_layout.addLayout(main_horizontal_layout)

        self.setLayout(main_vertical_layout)

        self.study_timer_frequency = 1 / 60 * 1000
        self.study_timer = QTimer(self, interval=int(self.study_timer_frequency), timeout=self.decrease_remaining_time)

        self.player = QMediaPlayer(self)

        self.setWindowIcon(QIcon(self.IMAGE_FOLDER + "icon.svg"))
        self.setWindowTitle(self.APP_NAME)

        # set initial UI state
        self.reset()

        # a list of name, getter and setter things to load/save when the app opens/closes
        # also dynamically get settings for selecting/unselecting plants
        self.CONFIGURATION_ATTRIBUTES = [("study-time", self.study_time_spinbox.value,
                                          self.study_time_spinbox.setValue),
                                         ("break-time", self.break_time_spinbox.value,
                                          self.break_time_spinbox.setValue),
                                         ("cycles", self.cycles_spinbox.value, self.cycles_spinbox.setValue),
                                         ("sound", self.sound_action.isChecked, self.sound_action.setChecked),
                                         ("sound-volume", self.volume_slider.value, self.volume_slider.setValue),
                                         ("pop-ups", self.popup_action.isChecked, self.popup_action.setChecked),
                                         ("overstudy", self.overstudy_action.isChecked,
                                          self.overstudy_action.setChecked)] + \
                                        [(name.lower(), getattr(self.__class__, name).isChecked,
                                          getattr(self.__class__, name).setChecked) for _, name in
                                         zip(self.PLANTS, self.PLANT_NAMES)]

        self.load_settings()

        self.show()

    def load_settings(self):
        """Loads the settings file (if it exists)."""
        if os.path.exists(self.CONFIGURATION_FILE_PATH):
            with open(self.CONFIGURATION_FILE_PATH) as file:
                configuration = yaml.load(file, Loader=yaml.FullLoader)

                # don't crash if config is broken
                if not isinstance(configuration, dict):
                    return

                for key in configuration:
                    for name, _, setter in self.CONFIGURATION_ATTRIBUTES:
                        if key == name:
                            setter(configuration[key])

    def save_settings(self):
        """Saves the settings file (if it exists)."""
        if not os.path.exists(self.ROOT_FOLDER):
            os.mkdir(self.ROOT_FOLDER)

        with open(self.CONFIGURATION_FILE_PATH, 'w') as file:
            configuration = {}

            for name, getter, _ in self.CONFIGURATION_ATTRIBUTES:
                configuration[name] = getter()

            file.write(yaml.dump(configuration))

    def closeEvent(self, event):
        """Called when the app is being closed. Overridden to also save Florodoro settings."""
        self.save_settings()
        super().closeEvent(event)

    def load_preset(self, study_value: int, break_value: int, cycles: int):
        """Load a pomodoro preset."""
        self.study_time_spinbox.setValue(study_value)
        self.break_time_spinbox.setValue(break_value)
        self.cycles_spinbox.setValue(cycles)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Debug-related keyboard controls."""
        if self.DEBUG:
            if event.key() == Qt.Key_Escape:
                possible_plants = [plant for i, plant in enumerate(self.PLANTS) if self.plant_checkboxes[i].isChecked()]

                if len(possible_plants) != 0:
                    self.plant = choice(possible_plants)()
                    self.canvas.set_drawable(self.plant)
                    self.plant.set_max_age(1)
                    self.plant.set_current_age(1)
                    self.canvas.update()

    def start_break(self):
        """Starts the break, instead of the study."""
        # if we're overstudying, this can be pressed when studying, so save that we did so
        if self.overstudy_action.isChecked() and self.is_study_ongoing:
            self.save_study(ignore_remainder=False)

        self.start(do_break=True)

    def start(self, do_break=False):
        """The function for starting either the study or break timer (depending on do_break)."""
        self.study_button.setEnabled(do_break)
        self.break_button.setEnabled(self.overstudy_action.isChecked() and not do_break)
        self.reset_button.setDisabled(False)

        self.pause_button.setDisabled(False)
        self.pause_button.setIcon(self.PAUSE_ICON)

        # if we're initially starting to do cycles, reset their count
        # don't reset on break, because we could be doing a standalone break
        if self.remaining_cycles == 0 and not do_break:
            self.remaining_cycles = self.cycles_spinbox.value()
            self.total_cycles = self.remaining_cycles
        else:
            # if we're not studing and are about to when there is still leftover time, we're ending the break quicker than intended
            # therefore, reduce cycles by 1, since they would have been if the timer were to run out during break
            if not self.is_study_ongoing and not do_break and self.get_leftover_time() / self.total_time > 0:
                self.remaining_cycles -= 1

                if self.remaining_cycles == 0:
                    self.reset()
                    return

        # set depending on whether we are currently studying or not
        self.is_study_ongoing = not do_break
        self.already_notified_during_overstudy = False

        self.main_label.setStyleSheet('' if not do_break else f'color:{self.BREAK_COLOR};')

        # the total time to study for (spinboxes are minutes)
        # since it's rounded down and it looks better to start at the exact time, 0.99 is added
        self.total_time = (self.study_time_spinbox if not do_break else self.break_time_spinbox).value() * 60 + 0.99
        self.ending_time = datetime.now() + timedelta(minutes=self.total_time / 60)

        # so it's displayed immediately
        self.update_time_label(self.total_time)
        self.update_cycles_label()

        # don't start showing canvas and growing the plant when we're not studying
        if not do_break:
            possible_plants = [plant for i, plant in enumerate(self.PLANTS) if self.plant_checkboxes[i].isChecked()]

            if len(possible_plants) != 0:
                self.plant = choice(possible_plants)()
                self.canvas.set_drawable(self.plant)
                self.plant.set_max_age(min(1, (self.total_time / 60) / self.MAX_PLANT_AGE))
                self.plant.set_current_age(0)
            else:
                self.plant = None

        self.study_timer.stop()  # it could be running - we could be currently in a break
        self.study_timer.start()

    def toggle_pause(self):
        """Called when the pause button is pressed. Either stops the timer or starts it again, while also doing stuff
        to the pause icons."""
        # stop the timer, if it's running
        if self.study_timer.isActive():
            self.study_timer.stop()
            self.pause_button.setIcon(self.CONTINUE_ICON)
            self.pause_time = datetime.now()

        # if not, resume
        else:
            self.ending_time += datetime.now() - self.pause_time
            self.study_timer.start()
            self.pause_button.setIcon(self.PAUSE_ICON)

    def reset(self):
        """Reset the UI."""
        self.study_timer.stop()
        self.pause_button.setIcon(self.PAUSE_ICON)

        self.main_label.setStyleSheet('')
        self.study_button.setDisabled(False)
        self.break_button.setDisabled(False)
        self.pause_button.setDisabled(True)
        self.reset_button.setDisabled(True)

        if self.plant is not None:
            self.plant.set_current_age(0)

        self.remaining_cycles = 0

        self.main_label.setText(self.INITIAL_TEXT)
        self.cycle_label.setText('')

    def update_time_label(self, time):
        """Update the text of the time label, given some time in seconds."""
        sign = -1 if time < 0 else 1

        time = abs(time)

        hours = int(time // 3600)
        minutes = int((time // 60) % 60)
        seconds = int(time % 60)

        # smooth timer: hide minutes/hours if there are none
        result = "-" if sign == -1 else ""
        if hours == 0:
            if minutes == 0:
                result += str(seconds)
            else:
                result += str(minutes) + QTime(0, 0, seconds).toString(":ss")
        else:
            result += str(hours) + QTime(0, minutes, seconds).toString(":mm:ss")

        self.main_label.setText(result)

    def play_sound(self, name: str):
        """Play a file from the sound directory. Extension is not included, will be added automatically."""
        for file in os.listdir(self.SOUNDS_FOLDER):
            # if the file starts with the provided name and only contains an extension after, try to play it
            if file.startswith(name) and file[len(name):][0] == ".":
                path = QDir.current().absoluteFilePath(self.SOUNDS_FOLDER + file)
                url = QUrl.fromLocalFile(path)
                content = QMediaContent(url)
                self.player.setMedia(content)
                self.player.setVolume(self.volume_slider.value())
                self.player.play()

    def show_notification(self, message: str):
        """Show the specified notification using plyer."""
        notification.notify(self.APP_NAME, message, self.APP_NAME, os.path.abspath(self.IMAGE_FOLDER + "icon.svg"))

    def update_cycles_label(self):
        """Update the cycles label, if we're currently studying and it wouldn't be 1/1."""
        if self.total_cycles != 1 and self.is_study_ongoing:
            self.cycle_label.setText(f"{self.total_cycles - self.remaining_cycles + 1}/{self.total_cycles}")

    def get_leftover_time(self):
        """Return time until the timer runs out."""
        return (self.ending_time - datetime.now()).total_seconds()

    def decrease_remaining_time(self):
        """Decrease the remaining time by the timer frequency. Updates clock/plant growth."""
        if self.DEBUG:
            self.ending_time -= timedelta(seconds=30)

        self.update_time_label(self.get_leftover_time())

        if self.get_leftover_time() <= 0:
            if self.is_study_ongoing:
                # only notify once per study, since this would be called all the time during overstudy
                if not self.already_notified_during_overstudy:
                    if self.sound_action.isChecked():
                        self.play_sound("study_done")

                    if self.popup_action.isChecked():
                        self.show_notification("Studying finished, take a break!")

                    self.already_notified_during_overstudy = True

                if not self.overstudy_action.isChecked():
                    self.save_study()  # save before break!
                    self.start_break()
            else:
                self.history.add_break(datetime.now(), self.total_time // 60)
                self.statistics.refresh()

                if self.sound_action.isChecked():
                    self.play_sound("break_done")

                if self.popup_action.isChecked():
                    self.show_notification("Break is over!")

                self.remaining_cycles -= 1
                if self.remaining_cycles <= 0:  # <=, because we could have just started a simple break
                    self.reset()
                else:
                    self.start()
                    self.update_cycles_label()

        else:
            # if there is leftover time and we haven't finished studying, grow the plant
            if self.is_study_ongoing:
                if self.plant is not None:
                    self.plant.set_current_age(1 - (self.get_leftover_time() / self.total_time))

                self.canvas.update()

    def save_study(self, ignore_remainder=True):
        """Save the record of the current study to the history file. By default, ignore the leftover time, since it
        will be a tiny number."""
        date = datetime.now()

        duration = (self.total_time - self.get_leftover_time()) / 60

        if ignore_remainder:
            duration = float(int(duration))

        self.history.add_study(date, duration,
                               self.total_cycles - self.remaining_cycles + 1,
                               self.total_cycles, self.plant)

        self.statistics.move()  # move to the last plant
        self.statistics.refresh()


def run():
    app = QApplication(sys.argv)
    Florodoro()
    app.exit(app.exec_())


if __name__ == '__main__':
    run()
