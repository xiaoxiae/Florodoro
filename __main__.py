import sys
from subprocess import Popen

from PyQt5.QtCore import QTimer, QTime, Qt, QDate
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QPushButton, QSpinBox
from PyQt5.QtWidgets import QVBoxLayout, QLabel


class Window(QWidget):

    def __init__(self):
        super().__init__()

        self.DEFAULT_STUDY_TIME = 45
        self.DEFAULT_BREAK_TIME = 15

        self.MAX_TIME = 180
        self.STEP = 5

        self.START_TEXT = "Start"
        self.PAUSE_TEXT = "Pause"
        self.CONTINUE_TEXT = "Continue"

        v_layout = QVBoxLayout()
        font = QFont('Arial', 120, QFont.Bold)

        self.timeLabel = QLabel(self)
        self.timeLabel.setAlignment(Qt.AlignCenter)

        self.timeLabel.setFont(font)

        v_layout.addWidget(self.timeLabel)

        h_layout = QHBoxLayout()

        self.study_time_spinbox = QSpinBox(self, minimum=1, maximum=self.MAX_TIME, value=self.DEFAULT_STUDY_TIME,
                                           singleStep=self.STEP)
        self.break_time_spinbox = QSpinBox(self, minimum=1, maximum=self.MAX_TIME, value=self.DEFAULT_BREAK_TIME,
                                           singleStep=self.STEP)

        self.start_button = QPushButton(self, text=self.START_TEXT, clicked=self.start)
        self.pause_button = QPushButton(self, text=self.PAUSE_TEXT, clicked=self.pause)
        self.pause_button.setDisabled(True)

        h_layout.addWidget(self.study_time_spinbox)
        h_layout.addWidget(self.break_time_spinbox)
        h_layout.addWidget(self.start_button)
        h_layout.addWidget(self.pause_button)

        v_layout.addLayout(h_layout)

        self.setLayout(v_layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.decreaseRemainingTime)

        self.player = QMediaPlayer()

    def start(self):
        self.start_button.setDisabled(True)
        self.pause_button.setDisabled(False)
        self.pause_button.setText(self.PAUSE_TEXT)

        # set, whether we finished studying and are having a break
        # this is inially false, since we just started the session
        self.study_done = False

        # the total time to study for (spinboxes are minutes)
        self.total_time = self.study_time_spinbox.value() * 60
        self.total_start_time = self.study_time_spinbox.value()

        self.timer.stop()  # it could be running - we could be currently in a break
        self.timer.start(0)  # immediately show the current time

    def pause(self):
        # don't pause when we're having a break
        if self.study_done:
            return

        if self.timer.isActive():
            # remember leftover miliseconds
            self.leftover_timer_miliseconds = self.timer.remainingTime()

            self.timer.stop()
            self.pause_button.setText(self.CONTINUE_TEXT)
        else:
            # use the leftover miliseconds for smoother pause continuation
            self.timer.start(self.leftover_timer_miliseconds)

            self.pause_button.setText(self.PAUSE_TEXT)

    def updateTimeLabel(self, time):
        """Update the text of the time label, given some time in seconds."""
        hours = time // 3600
        minutes = (time // 60) % 60
        seconds = time % 60

        if hours == 0:
            if minutes == 0:
                self.timeLabel.setText(str(seconds))
            else:
                self.timeLabel.setText(str(minutes) + QTime(0, 0, seconds).toString(":ss"))
        else:
            self.timeLabel.setText(str(hours) + QTime(0, minutes, seconds).toString(":mm:ss"))

    def playSound(self, name: str):
        """Play a file, relative to the current directory."""
        fullpath = QDir.current().absoluteFilePath(name)
        url = QUrl.fromLocalFile(fullpath)
        content = QMediaContent(url)
        self.player.setMedia(content)
        self.player.play()

    def decreaseRemainingTime(self):
        # make sure that the interval is a second, because we could have continued the timer
        # with the leftover seconds when pausing...
        self.timer.setInterval(1000)

        self.updateTimeLabel(self.total_time)

        self.total_time -= 1

        if self.total_time == 0:
            if self.study_done:
                self.timer.stop()

                self.pause_button.setDisabled(True)
                self.playSound("break.m4a")
            else:
                self.total_time = self.break_time_spinbox.value() * 60
                self.study_done = True
                self.start_button.setDisabled(False)

                with open("trimer.log", "a") as f:
                    f.write(QDate.currentDate().toString(Qt.ISODate) + "|" + QTime.currentTime().toString(
                        "hh:mm:ss") + " - finished studying for " + str(self.total_start_time) + " minutes." + "\n")

                self.playSound("study.m4a")


App = QApplication(sys.argv)
window = Window()
window.show()
App.exit(App.exec_())
