from setuptools import setup
from os import path
from re import search

script_location = path.abspath(path.dirname(__file__))

# get required packages from requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

# get long description from README
with open(path.join(script_location, "README.md"), "r") as f:
    long_description = f.read()

# get version
with open("florodoro/version.py") as f:
    exec(f.read())

setup(
    name="florodoro",
    version=__version__,
    author="Tomáš Sláma",
    author_email="tomas@slama.dev",
    keywords="education pyqt5 plants pomodoro",
    url="https://github.com/xiaoxiae/Florodoro",
    description="A pomodoro timer that grows procedurally generated trees and flowers while you're studying.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],

    packages=["florodoro"],
    include_package_data = True,
    package_data = {'florodoro': ["sounds/*", "images/*"]},
    data_files=[("", ["LICENSE", "README.md", "requirements.txt", "CHANGELOG.md"])],

    entry_points={'console_scripts': ['florodoro=florodoro.__init__:run']},

    # requirements
    install_requires=requirements,
    python_requires='>=3.7.1',
)
