from math import sin, pi


def smoothen_curve(x: float):
    """f(x) with a smoother beginning and end."""
    return (sin((x - 1 / 2) * pi) + 1) / 2
