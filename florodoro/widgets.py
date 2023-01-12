import pickle
from typing import Optional

import qtawesome
from PyQt5.QtChart import QStackedBarSeries, QBarSet, QChart, QBarCategoryAxis, QChartView
from PyQt5.QtCore import QMargins, Qt
from PyQt5.QtGui import QPainter, QBrush
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QSlider, QGridLayout, QFrame, \
    QFileDialog

from florodoro.plants import Drawable, Plant


class Canvas(QWidget):
    """A widget that takes a drawable object and draws it."""

    def __init__(self, *args, **kwargs):
        super(Canvas, self).__init__(*args, **kwargs)
        self.object: Optional[Drawable] = None

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

        self.object.draw(painter, self.width(), self.height())

        painter.end()


class Statistics(QWidget):
    """A statistics widget that displays information about studied time, shows grown plants, etc..."""

    def __init__(self, history, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.history = history

        chart = self.generate_chart()

        self.SPACING = 10
        self.MIN_WIDTH = 400
        self.MIN_HEIGHT = 200

        chart.setMinimumWidth(self.MIN_WIDTH)
        chart.setMinimumHeight(self.MIN_HEIGHT)

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
        self.canvas.setMinimumWidth(self.MIN_HEIGHT)
        self.canvas.setMinimumHeight(self.MIN_HEIGHT)

        stacked_layout = QVBoxLayout()
        stacked_layout.addLayout(label_layout)
        stacked_layout.addWidget(self.canvas)

        image_control = QHBoxLayout()

        text_color = self.palette().text().color()

        # a hack to get float (we're gonna be dividing by the maximum)
        self.age_slider = QSlider(Qt.Horizontal, minimum=0, maximum=1000, value=1000,
                                  valueChanged=self.slider_value_changed)

        self.left_button = QPushButton(self, clicked=self.left,
                                       icon=qtawesome.icon('fa5s.angle-left', color=text_color))
        self.right_button = QPushButton(self, clicked=self.right,
                                        icon=qtawesome.icon('fa5s.angle-right', color=text_color))
        self.save_button = QPushButton(self, clicked=self.save,
                                       icon=qtawesome.icon('fa5s.download', color=text_color))

        image_control.addWidget(self.left_button)
        image_control.addWidget(self.right_button)
        image_control.addSpacing(self.SPACING)
        image_control.addWidget(self.age_slider)
        image_control.addSpacing(self.SPACING)
        image_control.addWidget(self.save_button)

        image_layout.addLayout(stacked_layout)
        image_layout.addLayout(image_control)
        image_layout.setContentsMargins(self.SPACING, self.SPACING, self.SPACING, self.SPACING)

        separator = QFrame()
        separator.setStyleSheet(f"background-color: {self.palette().text().color().name()}")
        separator.setFixedWidth(1)

        main_layout = QGridLayout()
        main_layout.setHorizontalSpacing(self.SPACING * 2)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(2, 0)
        main_layout.addWidget(chart, 0, 0)
        main_layout.addWidget(separator, 0, 1)
        main_layout.addLayout(image_layout, 0, 2)

        self.setLayout(main_layout)

        self.move()  # go to the most recent plant

        self.refresh()

    def generate_chart(self):
        """Generate the bar graph for the widget."""
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

    def slider_value_changed(self):
        """Called when the slider value has changed. Sets the age of the plant and updates it."""
        if self.plant is not None:
            # makes it a linear function from 0 to whatever the duration was, so the plant appears to grow normally
            self.plant.set_age(
                self.plant.inverse_age_coefficient_function(self.age_slider.value() / self.age_slider.maximum() *
                                                            self.plant.age_coefficient_function(
                                                                self.plant_study["duration"])))
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

        # manually set the range of the y axis, because it doesn't for some reason
        yAxis = self.chart.axes(Qt.Vertical)[0]
        yAxis.setRange(0, max(study_minutes))

    def left(self):
        """Move to the left (older) plant."""
        self.move(-1)

    def right(self):
        """Move to the right (newer) plant."""
        self.move(1)

    def move(self, delta: int = 0):
        """Move to the left/right plant by delta. If no plant is currently being displayed or delta is 0, pick the
        latest one."""
        studies = self.history.get_studies()

        self.age_slider.setValue(self.age_slider.maximum())

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
        self.slider_value_changed()  # it didn't, but the code should act as if it did (update plant)

    def save(self):
        """Save the current state of the plant to a file."""
        if self.plant is not None:
            name, _ = QFileDialog.getSaveFileName(self, 'Save File', "", "SVG files (*.svg)")

            if name == "":
                return

            if not name.endswith(".svg"):
                name += ".svg"

            self.plant.save(name, 1000, 1000)


class SpacedQWidget(QWidget):
    """A dummy class for adding spacing to the left and right of a QWidget. Used in a QMenuBar's QWidgetAction, because
    I haven't found a way to add spacing to the left/right of a QSlider."""

    def __init__(self, widget: QWidget, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.SPACING = 5

        layout = QHBoxLayout()
        layout.addSpacing(self.SPACING)
        layout.addWidget(widget)
        layout.addSpacing(self.SPACING)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)
