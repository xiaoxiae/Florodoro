import argparse
import os
import sys
import tempfile
from datetime import datetime, timedelta
from functools import partial
from random import choice

import qtawesome
import yaml
from PyQt5.QtCore import QTimer, QTime, Qt, QDir, QUrl
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QPushButton, QSpinBox, QAction, QSizePolicy, \
    QMessageBox, QMenuBar, QStackedLayout, QSlider, QWidgetAction
from PyQt5.QtWidgets import QVBoxLayout, QLabel
from plyer import notification

from florodoro.history import History
from florodoro.plants import GreenTree, DoubleGreenTree, OrangeTree, CircularFlower
from florodoro.widgets import Canvas, Statistics, SpacedQWidget


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

        self.STUDY_ICON = qtawesome.icon('fa5s.book', color=self.TEXT_COLOR)
        self.BREAK_ICON = qtawesome.icon('fa5s.coffee', color=self.BREAK_COLOR)
        self.CONTINUE_ICON = qtawesome.icon('fa5s.play', color=self.TEXT_COLOR)
        self.PAUSE_ICON = qtawesome.icon('fa5s.pause', color=self.TEXT_COLOR)
        self.RESET_ICON = qtawesome.icon('fa5s.undo', color=self.TEXT_COLOR)

        self.PLANTS = [GreenTree, DoubleGreenTree, OrangeTree, CircularFlower]
        self.PLANT_NAMES = ["Spruce", "Double spruce", "Maple", "Flower"]

        self.WIDGET_SPACING = 10

        self.MAX_TIME = 180
        self.STEP = 5

        self.INITIAL_TEXT = "Start!"

        self.menuBar = QMenuBar(self)
        self.presets_menu = self.menuBar.addMenu('&Presets')

        self.presets = {
            "Classic": (25, 5, 4),
            "Extended": (45, 12, 2),
            "Sitcomodoro": (65, 25, 1),
        }

        for name in self.presets:
            study_time, break_time, cycles = self.presets[name]

            self.presets_menu.addAction(
                QAction(f"{name} ({study_time} : {break_time} : {cycles})", self,
                        triggered=partial(self.load_preset, study_time, break_time, cycles)))

        self.DEFAULT_PRESET = "Classic"

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
            tmp.set_age(float('inf'))
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
                                           singleStep=self.STEP)

        self.break_time_spinbox = QSpinBox(self, prefix="Break for: ", suffix="min.", minimum=1, maximum=self.MAX_TIME,
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
        # load the default preset
        self.load_preset(*self.presets[self.DEFAULT_PRESET])

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
                self.plant.set_age(0)
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
            self.plant.set_age(0)

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

        # if we haven't finished studying, grow the plant
        if self.is_study_ongoing:
            if self.plant is not None:
                self.plant.set_age(self.duration())

            self.canvas.update()

    def duration(self):
        """Get the current duration of whatever is currently going on."""
        return (self.total_time - self.get_leftover_time()) / 60

    def save_study(self, ignore_remainder=True):
        """Save the record of the current study to the history file. By default, ignore the leftover time, since it
        will be a tiny number."""
        date = datetime.now()

        d = self.duration()

        if ignore_remainder:
            d = float(int(d))

        self.history.add_study(date, d, self.plant)

        self.statistics.move()  # move to the last plant
        self.statistics.refresh()


def run():
    app = QApplication(sys.argv)
    Florodoro()
    app.exit(app.exec_())


if __name__ == '__main__':
    run()
