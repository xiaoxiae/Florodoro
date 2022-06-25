![](https://raw.githubusercontent.com/xiaoxiae/Florodoro/master/florodoro/images/logo.svg)

---

A pomodoro timer that grows procedurally generated trees and flowers while you're studying.

![](https://raw.githubusercontent.com/xiaoxiae/Florodoro/master/florodoro/images/preview.svg)

## Running Florodoro
First, install the app by running `pip install florodoro`.
To launch the application, simply run the `florodoro` command from a terminal of your choice.

If you'd like to use the latest (unstable) version, install from TestPyPI using `pip install -i https://test.pypi.org/simple/ florodoro`

## Controls

### Top bar
- **Presets** – contains common pomodoro timings for study/break/cycle
- **Options**
	- **Notify** – notification options (sound/pop-ups)
	- **Plants** – plant settings (which ones to grow)
	- **Overstudy** – enables doing a break earlier/later than specified, allowing for more "organic" study sessions
- **Statistics** – shows statistics regarding time studied; includes an interactive gallery of the grown plants
- **About** – a small TLDR about the project

### Bottom bar
- **Study for ...** – how long to study for
- **Break for ...** – how long to break after study
- **Icon: Cycles ...** – how many times to repeat study-break
- **Icon: Book** – start the study session
- **Icon: Coffee** – start a break
- **Icon: Pause/continue** – pause/continue an ongoing study/break
- **Icon: Reset** – reset everything

## Local development

### Setup
1. create virtual environment: `python3 -m venv venv`
2. activate it `. venv/bin/activate` (assuming you use Bash)
3. install the package locally: `python3 -m pip install --editable .`
	- the `--editable` flag ensures local changes are used when running the package
4. develop
5. run `florodoro` (make sure that `venv` is active)

_Note: this might not work when the path to the cloned reposity contains whitespace. I didn't look into the reason why (likely a bug in `venv`), just something to try if something fails._

### Publish
All tagged commits are automatically published on PyPi using GitGub Actions.
If the commit is on the `testing` branch, the test PyPi instance is used, otherwise the main one is.
