![](https://raw.githubusercontent.com/xiaoxiae/Florodoro/master/florodoro/images/logo.svg)

---

A pomodoro timer that grows procedurally generated trees and flowers while you're studying.

![](https://raw.githubusercontent.com/xiaoxiae/Florodoro/master/florodoro/images/preview.svg)

## Running Florodoro
First, install the app by running
```
pip install florodoro
```

To launch the application, simply run the `florodoro` command from a terminal of your choice.

If you'd like to use the latest (unstable) version, install from TestPyPI using
```
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple florodoro
```

## Controls

### Top bar
- **Presets** – contains common pomodoro timings for study/break/cycle
- **Options**
	- **Notify** – notification options (sound/pop-ups)
	- **Plants** – plant settings (which ones to grow)
	- **Overstudy** – enables breaks and studies longer than set
- **Statistics** – shows statistics + an interactive plant gallery
- **About** – a small TLDR about the project

### Bottom bar
- **Study for ...** – how long to study for
- **Break for ...** – how long to break after study
- **Cycles: ...** – how many times to repeat study-break (0 means infinite)
- **Icon: Book** – start the study session
- **Icon: Coffee** – start a break
- **Icon: Pause/continue** – pause/continue an ongoing study/break
- **Icon: Reset** – reset everything

## Local development

### Setup
1. create virtual environment: `python3 -m venv venv`
2. activate it `. venv/bin/activate` (assuming you use Bash)
3. install the package locally: `python3 -m pip install -e .`
	- the `-e` flag ensures local changes are used when running the package
4. develop
5. run `florodoro` (make sure that `venv` is active)

_Note: this might not work when the path to the cloned reposity contains whitespace. I didn't look into the reason why (likely a bug in `venv`), just something to try if something fails._

### Publishing
All tagged commits in the `x.y.z` format are automatically published on PyPi using GitGub Actions.
If the commit is on the `testing` branch, the test PyPi instance is used.

The project follows [Semver](https://semver.org/) for version numbers and is currently under MAJOR version `0` (under rapid prototyping).
For as long as this is the case, the master branch will only contain MINOR versions, while the testing branch will contain PATCH versions.
