from abc import abstractmethod, ABC
from math import degrees, sin, acos, sqrt
from random import uniform, random, randint, choice
from typing import Callable

from PyQt5.QtCore import QSize, QRect, QPointF, QRectF, Qt
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QPen, QBrush
from PyQt5.QtSvg import QSvgGenerator

from florodoro.utilities import smoothen_curve


class Drawable(ABC):
    """Something that has a draw function that takes a painter to be painted.
    Also contains some convenience methods for drawing the thing and saving it to an SVG."""

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


class Color:
    green = QColor(0, 119, 0)
    white = QColor(255, 255, 255)
    brown = QColor(77, 51, 0)
    orange = QColor(243, 148, 30)

    logo_colors = [
        QColor(139, 139, 255),  # blue-ish
        QColor(72, 178, 173),  # green-ish
        QColor(255, 85, 85),  # red-ish
        QColor(238, 168, 43),  # orange-ish
        QColor(226, 104, 155),  # pink-ish
    ]


class Plant(Drawable):
    age: float = 0

    # coefficient that change how quickly the plant grows
    age_coefficient = 15
    age_exponent = 2

    def __init__(self):
        # make the sizes somewhat random
        self.deficit_coefficient = uniform(0.9, 1)

    def set_age(self, age: float):
        """Set the current age of the plant (in minutes)."""
        self.age = age

    def age_coefficient_function(self, x) -> float:
        """The function that calculates the normalized age [0, 1] from actual age (in minutes)."""
        return - 1 / ((x / self.age_coefficient) ** self.age_exponent + 1) + 1

    def inverse_age_coefficient_function(self, x) -> float:
        """The inverse to the age function."""
        return float('inf') if x == 1 else (self.age_coefficient * x ** (1 / self.age_exponent)) / (1 - x) ** (
                1 / self.age_exponent)

    def get_age_coefficient(self) -> float:
        """Return the age, adjusted from 0 to 1."""
        return self.age_coefficient_function(self.age)

    def get_slower_age_coefficient(self) -> float:
        """Return the age, adjusted from 0 to 1, but increasing slower."""
        return self.get_age_coefficient() ** 3

    @abstractmethod
    def _draw(self, painter: QPainter, width: int, height: int):
        """The actual implementation of the plant drawn."""
        pass

    def draw(self, painter: QPainter, width: int, height: int):
        """Draw the plant on the painter, given the width and height."""
        w = min(width, height)
        h = min(width, height)

        # position to the bottom center of the canvas
        painter.translate(width / 2, height)
        painter.scale(1, -1)

        self._draw(painter, w, h)


class Flower(Plant):

    def __init__(self):
        super().__init__()

        # the ending x position of the flower -- so it tilts one way or another
        self.x_coefficient = uniform(0.4, 1) * (-1 if random() < 0.5 else 1)

        self.generate_leafs(2)

        self.stem_width = uniform(3.5, 4)

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
        return height / 2.5 * self.deficit_coefficient

    def leaf_size(self, width):
        """The size of the leaf."""
        return width / 7 * self.deficit_coefficient

    def _draw(self, painter: QPainter, width: int, height: int):
        self.x = self.flower_center_x(width) * smoothen_curve(self.get_age_coefficient())
        self.y = self.flower_center_y(height) * smoothen_curve(self.get_age_coefficient())

        painter.setPen(QPen(Color.green, self.stem_width * smoothen_curve(self.get_age_coefficient())))

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

            painter.setBrush(QBrush(Color.green))
            painter.setPen(QPen(0))

            # draw the leaf
            leaf = QPainterPath()
            leaf.setFillRule(Qt.WindingFill)
            ls = self.leaf_size(width) * smoothen_curve(self.get_age_coefficient()) ** 2 * coefficient
            leaf.quadTo(0.4 * ls, 0.5 * ls, 0, ls)
            leaf.cubicTo(0, 0.5 * ls, -0.4 * ls, 0.4 * ls, 0, 0)
            painter.drawPath(leaf)

            painter.restore()


class CircularFlower(Flower):
    """A class for creating a flower."""

    def __init__(self):
        super().__init__()

        # color of the flower
        self.color = choice(Color.logo_colors)

        self.number_of_pellets = randint(5, 7)

        # the center of the plant is smaller, compared to other pellet sizes
        self.center_pellet_smaller_coefficient = uniform(0.75, 0.85)

        self.pellet_drawing_function: Callable[[QPainter, float], None] = choice(
            [self.circular_pellet, self.triangle_pellet, self.dip_pellet, self.round_pellet])

        # the m and n pellets don't look good with any other number of leafs (other than 5)
        if self.pellet_drawing_function in [self.dip_pellet, self.round_pellet]:
            self.number_of_pellets = 5

    def triangle_pellet(self, painter: QPainter, pellet_size: float):
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
        return width / 9 * self.deficit_coefficient

    def _draw(self, painter: QPainter, width: int, height: int):
        super()._draw(painter, width, height)

        painter.save()

        # move to the position of the flower
        painter.translate(self.x, self.y)

        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self.color))

        pellet_size = self.pellet_size(width) * smoothen_curve(self.get_age_coefficient())

        # draw each of the pellets
        for i in range(self.number_of_pellets):
            self.pellet_drawing_function(painter, pellet_size)
            painter.rotate(360 / self.number_of_pellets)

        # draw the center of the flower
        painter.setBrush(QBrush(Color.white))
        pellet_size *= self.center_pellet_smaller_coefficient
        painter.drawEllipse(QRectF(-pellet_size / 2, -pellet_size / 2, pellet_size, pellet_size))

        painter.restore()


class Tree(Plant):
    """A simple tree class that all trees originate from."""

    def __init__(self):
        super().__init__()

        # generate somewhere between 1 and 2 branches
        self.generateBranches(round(uniform(1, 2)))

    def generateBranches(self, count):
        # positions of branches up the tree, + their orientations (where they're turned towards)
        self.branches = [(uniform(self.deficit_coefficient * 0.45, self.deficit_coefficient * 0.55),
                          (((i - 1 / 2) * 2) if count == 2 else (-1 if random() < 0.5 else 1)) * acos(
                              uniform(0.4, 0.6))) for i in
                         range(count)]

    def base_width(self, width):
        """The width of the base of the tree."""
        return width / 15 * self.deficit_coefficient

    def base_height(self, height):
        """The height of the base of the tree."""
        return height / 1.7 * self.deficit_coefficient

    def branch_width(self, width):
        """The width of a branch of the tree."""
        return width / 18 * self.deficit_coefficient

    def branch_height(self, height):
        """The height of a branch of the tree."""
        return height / 2.7 * self.deficit_coefficient

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setBrush(QBrush(Color.brown))

        # main branch
        painter.drawPolygon(QPointF(-self.base_width(width) * smoothen_curve(self.get_age_coefficient()), 0),
                            QPointF(self.base_width(width) * smoothen_curve(self.get_age_coefficient()), 0),
                            QPointF(0, self.base_height(height) * smoothen_curve(self.get_age_coefficient())))

        # other branches
        for h, rotation in self.branches:
            painter.save()

            # translate/rotate to the position from which the branches grow
            painter.translate(0, self.base_height(height * h * smoothen_curve(self.get_age_coefficient())))
            painter.rotate(degrees(rotation))

            painter.drawPolygon(
                QPointF(-self.branch_width(width) * smoothen_curve(self.get_slower_age_coefficient()) * (1 - h), 0),
                QPointF(self.branch_width(width) * smoothen_curve(self.get_slower_age_coefficient()) * (1 - h), 0),
                QPointF(0, self.branch_height(height) * smoothen_curve(self.get_slower_age_coefficient()) * (1 - h)))

            painter.restore()


class OrangeTree(Tree):
    """A tree with orange ellipses as leafs."""

    def __init__(self):
        super().__init__()

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
        painter.setBrush(QBrush(Color.orange))

        for i, branch in enumerate(self.branches):
            h, rotation = branch

            painter.save()

            # translate/rotate to the position from which the branches grow
            painter.translate(0, self.base_height(height * h * smoothen_curve(self.get_age_coefficient())))
            painter.rotate(degrees(rotation))

            top_of_branch = self.branch_height(height) * smoothen_curve(self.get_slower_age_coefficient()) * (1 - h)
            circle_on_branch_position = top_of_branch * self.branch_circles[i][1]

            r = ((width + height) / 2) * self.branch_circles[i][0] * self.get_slower_age_coefficient() * (
                    1 - h) * self.get_age_coefficient()

            painter.setBrush(QBrush(Color.orange))
            painter.drawEllipse(QPointF(0, circle_on_branch_position), r, r)

            painter.restore()

        top_of_branch = self.base_height(height) * smoothen_curve(self.get_age_coefficient())
        circle_on_branch_position = top_of_branch * self.branch_circles[-1][1]

        # make the main ellipse slightly larger
        increase_size = 1.3
        r = ((width + height) / 2) * self.branch_circles[-1][0] * self.get_age_coefficient() * (
                1 - self.branches[-1][0]) * increase_size

        painter.drawEllipse(QPointF(0, circle_on_branch_position), r, r)

        super()._draw(painter, width, height)


class GreenTree(Tree):
    """A tree with a green triangle as leafs."""

    def __init__(self):
        super().__init__()

    def green_width(self, width):
        """The width of the top part of the leafs."""
        return width / 3.2 * self.deficit_coefficient

    def green_height(self, height):
        """The height of the top part of the leafs."""
        return height / 1.5 * self.deficit_coefficient

    def offset(self, height):
        return min(height * 0.95, self.base_height(height * 0.3 * smoothen_curve(self.get_age_coefficient())))

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(Color.green))

        painter.drawPolygon(
            QPointF(-self.green_width(width) * smoothen_curve(self.get_age_coefficient()), self.offset(height)),
            QPointF(self.green_width(width) * smoothen_curve(self.get_age_coefficient()), self.offset(height)),
            QPointF(0, self.green_height(height) * smoothen_curve(self.get_age_coefficient()) + self.offset(height)))

        super()._draw(painter, width, height)


class DoubleGreenTree(GreenTree):
    """A tree with a double green triangle as leafs."""

    def __init__(self):
        super().__init__()

    def second_green_width(self, width):
        return width / 3.5 * self.deficit_coefficient

    def second_green_height(self, height):
        return height / 2.4 * self.deficit_coefficient

    def _draw(self, painter: QPainter, width: int, height: int):
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(Color.green))

        offset = self.base_height(height * 0.3 * smoothen_curve(self.get_age_coefficient()))
        second_offset = (self.green_height(height) - self.second_green_height(height)) * smoothen_curve(
            self.get_age_coefficient())

        painter.drawPolygon(
            QPointF(-self.second_green_width(width) * smoothen_curve(self.get_age_coefficient()) ** 2,
                    offset + second_offset),
            QPointF(self.second_green_width(width) * smoothen_curve(self.get_age_coefficient()) ** 2,
                    offset + second_offset),
            QPointF(0, min(
                self.second_green_height(height) * smoothen_curve(self.get_age_coefficient()) + offset + second_offset,
                height * 0.95)))

        super()._draw(painter, width, height)
