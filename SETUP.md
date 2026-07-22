# Chord Progression Generator — Windows Setup Guide

A genre-aware chord progression generator with guitar voicings, audio
playback, MIDI export, and an interactive session for rearranging chords.

This guide builds the project from scratch using PowerShell on your
Dell OptiPlex (or any Windows machine).

---

## 1. Check Python is installed

```powershell
python --version
```

You want Python 3.9+. If it's not installed, grab it from
[python.org](https://www.python.org/downloads/) — during install, check
**"Add python.exe to PATH"**.

If `python` isn't recognized but you know it's installed, try:

```powershell
py --version
```

(Windows sometimes only registers the `py` launcher. Swap `python` for
`py` in every command below if that's your case.)

---

## 2. Create a project folder

```powershell
mkdir chord-gen
cd chord-gen
```

---

## 3. Create a virtual environment

Keeps these dependencies isolated from the rest of your Python setup.

```powershell
python -m venv venv
```

Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

Your prompt should now start with `(venv)`.

> **If you get an error about "running scripts is disabled on this
> system"**, PowerShell's execution policy is blocking the activation
> script. Fix it for your user only (doesn't require admin):
>
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
>
> Then re-run the `Activate.ps1` command above.

---

## 4. Install dependencies

```powershell
pip install numpy sounddevice mido
```

- **numpy** — generates the sine-wave audio for chord playback
- **sounddevice** — plays that audio through your speakers
- **mido** — writes standard `.mid` files for FL Studio

If `sounddevice` fails to install or errors on first run with something
about PortAudio, install the wheel-bundled version explicitly:

```powershell
pip install sounddevice --force-reinstall
```

It ships its own PortAudio binary on Windows, so no separate driver
install should be needed.

---

## 5. Add the script

Save `chord_gen.py` (from this conversation) into the `chord-gen` folder
you just created. You can drag-and-drop it from wherever you downloaded
it, or open it directly in your editor and paste the contents in.

Your folder should now look like:

```
chord-gen\
  venv\
  chord_gen.py
```

---

## 6. Verify it works

```powershell
python chord_gen.py --key A --mode minor --genre shoegaze --guitar
```

You should see a progression printed with roman numerals, chord names,
and guitar shapes. If that prints cleanly, the core generator works.

Test audio playback:

```powershell
python chord_gen.py --key A --genre shoegaze --play
```

You should hear each chord ring out through your speakers. If nothing
plays and no error appears, check Windows Sound Settings to confirm the
correct output device is set as default — `sounddevice` uses whatever
Windows considers the default device.

Test MIDI export:

```powershell
python chord_gen.py --key A --genre shoegaze --export test.mid
```

A `test.mid` file should appear in the `chord-gen` folder. Drag it into
FL Studio's playlist to confirm it imports correctly.

---

## 7. Everyday usage

Every time you come back to this project in a new PowerShell window,
reactivate the virtual environment first:

```powershell
cd chord-gen
.\venv\Scripts\Activate.ps1
```

Then run any of:

```powershell
# Quick generation, printed only
python chord_gen.py --key E --genre blues --guitar

# Play it out loud
python chord_gen.py --key G --genre country --play

# Export straight to MIDI for FL Studio
python chord_gen.py --key C# --genre alt-metal --export riff.mid --tempo 140

# Full interactive session: play, replay single chords, rearrange, export
python chord_gen.py --key A --mode minor --genre shoegaze --interactive
```

Run `python chord_gen.py --help` any time for the full flag list.

---

## 8. (Optional) Make it runnable without activating the venv every time

If retyping the activation line gets old, create a small wrapper script
`run.ps1` in the same folder:

```powershell
@'
& "$PSScriptRoot\venv\Scripts\python.exe" "$PSScriptRoot\chord_gen.py" @args
'@ | Out-File -Encoding utf8 run.ps1
```

Then just run:

```powershell
.\run.ps1 --key A --genre shoegaze --play
```

This calls the venv's Python directly without needing `Activate.ps1` at
all — handy if you ever wire this into CAS as a callable tool.

---

## 9. The GUI app (piano/guitar visualizer)

`chord_gen_gui.py` is a desktop app built on `tkinter` (ships with
Python — no extra install) that sits on top of `chord_gen.py`. It shows
your generated progression as clickable chord buttons, plays it out
loud, and visualizes the notes on a piano keyboard or guitar fretboard
as each chord plays, with the chord name displayed live.

Put `chord_gen_gui.py` in the same folder as `chord_gen.py`, then:

```powershell
python chord_gen_gui.py
```

**What you can do in it:**
- Pick key / mode / genre and hit **Generate**
- **▶ Play All** plays the whole progression, highlighting each chord's
  notes on the keyboard or fretboard as it sounds
- Click any chord button to play just that one
- Click two chord buttons in a row to swap their order
- Toggle between **Piano** and **Guitar** view any time
- **Export MIDI…** saves the current (possibly reordered) progression
  straight to a `.mid` file via a save dialog

The guitar view shows real open-position chord shapes where they exist
(C, D, Dm, E, Em, F, G, A, Am) and correctly computed barre-chord
shapes everywhere else — the same E-shape/A-shape patterns guitarists
actually use to play chords up the neck. 7th and diminished chords are
shown using their base major/minor shape, same as the CLI's guitar
hints.

---

## Troubleshooting quick reference

| Symptom | Fix |
|---|---|
| `python` not recognized | Reinstall Python, check "Add to PATH", or use `py` instead |
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| No sound on `--play` | Check Windows default output device in Sound Settings |
| `ModuleNotFoundError` for numpy/sounddevice/mido | Confirm `(venv)` shows in your prompt, then re-run the `pip install` line |
| MIDI file won't import to FL Studio | Confirm the file ends in `.mid` (the script appends it automatically if you forget) |
