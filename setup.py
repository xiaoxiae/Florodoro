from setuptools import setup, find_packages
from glob import glob
from os import path

script_location = path.abspath(path.dirname(__file__))

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    # information about the package
    name="florodoro",
    version="0.2.9",
    author="Tomáš Sláma",
    author_email="tomas@slama.dev",
    keywords="education pyqt5 plants pomodoro",
    url="https://github.com/xiaoxiae/Florodoro",
    description="A pomodoro timer that grows procedurally generated trees and flowers while you're studying.",
    long_description=open(path.join(script_location, "README.md"), "r").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],

    # where to look for files
    packages=["florodoro"],
    include_package_data = True,
    package_data = {'florodoro': ["sounds/*", "images/*"]},
    data_files=[("", ["LICENSE.txt", "README.md"])],

    entry_points={'console_scripts': ['florodoro=florodoro.__init__:run']},

    # requirements
    install_requires=requirements,
    python_requires='>=3.7.1',
)
