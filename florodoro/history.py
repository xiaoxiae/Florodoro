import os
import pickle
from typing import List

import yaml

from florodoro.plants import Plant


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
        """Add a break to the history. The date is the ENDING time."""
        self.history["breaks"].append({"date": date, "duration": duration})
        self.save()

    def add_study(self, date, duration: float, plant: Plant):
        """Add a break to the history. The date is the ENDING time."""
        self.history["studies"].append({
            "date": date,
            "duration": duration,
            "plant": pickle.dumps(plant)
        })
        self.save()

    def total_studied_time(self) -> float:
        """Return the total minutes of studied time."""
        return self._total_activity_time("studies")

    def total_break_time(self) -> float:
        """Return the total minutes of studied time."""
        return self._total_activity_time("breaks")

    def _total_activity_time(self, activity_type: str):
        """Calculate the total time of something."""
        # TODO: check for correct formatting, don't just crash if it's wrong
        total = 0
        for study in self.history[activity_type]:
            total += study["duration"]

        return total

    def total_plants_grown(self) -> int:
        """Return the total number of plants grown."""
        count = 0
        for study in self.get_studies():
            # TODO: check for correct formatting, don't just crash if it's wrong

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
