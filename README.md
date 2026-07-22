# Chord Progression Generator

A genre-aware chord progression generator for guitar and piano — pick a
key, mode, and genre, and get back real diatonic chord progressions you
can hear, watch, and export.

Built for four genres with genuinely different harmonic character:
**shoegaze**, **alt-metal**, **blues**, and **country** (plus general
pop/rock).

---

## Features

- 🎸 **Genre-aware progressions** — not random chords, but curated
  roman-numeral progressions per genre (12-bar blues with dominant
  7ths, alt-metal power-chord movement, shoegaze's dreamier
  turnarounds, classic country I-IV-V)
- 🎹 **Real music theory core** — chords are derived from actual
  diatonic harmony in any key/mode, not hardcoded per key
- 🔊 **Audio playback** — hear the progression out loud via built-in
  sine-wave synthesis, no soundfont required
- 🎼 **MIDI export** — drag straight into your DAW
- 🖥️ **Desktop GUI** — piano keyboard and guitar fretboard
  visualizations that highlight notes live as each chord plays, with
  the chord name displayed
- 🎸 **Guitar voicings** — real open-position chord shapes where they
  exist, and correctly computed barre-chord shapes (E-shape/A-shape)
  everywhere else
- ⌨️ **CLI + interactive mode** — generate, play, reorder, and export
  progressions entirely from the terminal if you prefer

---

## Quick start

```bash
pip install numpy sounddevice mido
python chord_gen.py --key A --mode minor --genre shoegaze --play
```

For the full Windows/PowerShell walkthrough (virtual environment,
execution policy fixes, troubleshooting), see **[SETUP.md](SETUP.md)**.

---

## Usage

### CLI

```bash
# Generate and print a progression with guitar voicings
python chord_gen.py --key E --genre blues --guitar

# Play it out loud
python chord_gen.py --key G --genre country --play

# Export straight to MIDI
python chord_gen.py --key C# --genre alt-metal --export riff.mid --tempo 140

# Full interactive session: play, replay single chords, rearrange, export
python chord_gen.py --key A --mode minor --genre shoegaze --interactive
```

Run `python chord_gen.py --help` for the full flag list.

### GUI

```bash
python chord_gen_gui.py
```

Pick a key/mode/genre, hit **Generate**, then **▶ Play All** to hear it
while the piano keyboard or guitar fretboard highlights the notes of
each chord in real time. Click any chord to solo it, click two chords
in a row to swap their order, and export whenever you're happy with
the result.

---

## How it works

- `NOTES`, `SCALES`, and `TRIAD_QUALITIES` build correct diatonic
  chords for any root/mode — quality (major/minor/diminished) is
  derived from scale position, not looked up per key
- `GENRE_PROGRESSIONS` holds curated roman-numeral progressions per
  genre; `roman_to_chord()` renders them into real chord names
  (including 7th-chord handling for blues)
- `chord_to_frets()` computes guitar voicings: real open-position
  shapes where they exist, otherwise E-shape/A-shape barre patterns —
  the same way guitarists actually derive chords up the neck
- `synthesize_chord()` does additive sine-wave synthesis with a soft
  harmonic and attack/release envelope for clean playback
- `export_midi()` writes a standard `.mid` file via `mido`
- `chord_gen_gui.py` is a `tkinter` desktop app layered on top of all
  of the above — the music theory core has zero UI dependencies, so it
  can be reused in a different interface entirely (a Textual TUI, for
  instance) without changes

---

## Project structure

```
chord_gen.py          # Core: music theory, genre progressions, audio synthesis,
                       # MIDI export, guitar voicing/fretboard logic, CLI
chord_gen_gui.py       # Tkinter GUI: piano/guitar visualizer, playback, reordering
create_shortcut.ps1    # Creates a no-console-window desktop shortcut (Windows)
SETUP.md               # Detailed Windows/PowerShell setup walkthrough
```

---

## Requirements

- Python 3.9+
- `numpy`, `sounddevice`, `mido` (audio playback + MIDI export)
- `tkinter` (GUI only — ships with standard Python on Windows/macOS)

---

## License

Personal project — no license specified yet.
