#!/usr/bin/env python3
"""
Chord Progression Generator
============================
Generates chord progressions in any key/mode, tailored by genre
(shoegaze, alt-metal, blues, country, pop/rock), with guitar voicing
suggestions, audio playback, MIDI export, and an interactive session
for replaying individual chords and rearranging the progression.

Usage examples:
    python chord_gen.py --key A --mode minor --genre shoegaze
    python chord_gen.py --key E --genre blues --guitar
    python chord_gen.py --key G --genre country --count 3
    python chord_gen.py --key A --genre shoegaze --play
    python chord_gen.py --key A --genre shoegaze --export prog.mid
    python chord_gen.py --key A --genre shoegaze --interactive

Dependencies for audio/MIDI (install once):
    pip install numpy sounddevice mido

Architecture note: the music-theory core (NOTES, scale building,
diatonic chord construction, GENRE_PROGRESSIONS) is fully decoupled
from I/O, and so is the audio/MIDI layer below it. If you want to
drop this into a Textual TUI later (same pattern as CAS Journal),
import generate_progression(), suggest_voicing(), play_progression(),
and export_midi(), and build a view layer on top.
"""

import argparse
import random
import sys

# ---------------------------------------------------------------------------
# Music theory core
# ---------------------------------------------------------------------------

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

ENHARMONIC_FLATS = {
    "C#": "Db", "D#": "Eb", "F#": "Gb", "G#": "Ab", "A#": "Bb",
}

# Scale intervals (semitones from root)
SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],  # natural minor
}

# Diatonic triad qualities by scale degree (1-indexed), for each mode
TRIAD_QUALITIES = {
    "major": ["maj", "min", "min", "maj", "maj", "min", "dim"],
    "minor": ["min", "dim", "maj", "min", "min", "maj", "maj"],
}

# Roman numeral templates per scale degree (matches TRIAD_QUALITIES index)
ROMAN_MAJOR = ["I", "ii", "iii", "IV", "V", "vi", "vii°"]
ROMAN_MINOR = ["i", "ii°", "III", "iv", "v", "VI", "VII"]

CHORD_SUFFIX = {
    "maj": "",
    "min": "m",
    "dim": "dim",
    "dom7": "7",
    "maj7": "maj7",
    "min7": "m7",
}


def build_scale(root: str, mode: str):
    """Return list of 7 note names for the diatonic scale of root+mode."""
    root_idx = NOTES.index(root)
    intervals = SCALES[mode]
    return [NOTES[(root_idx + i) % 12] for i in intervals]


def roman_numerals_for_mode(mode: str):
    return ROMAN_MAJOR if mode == "major" else ROMAN_MINOR


def roman_to_chord(roman: str, root: str, mode: str, seventh: bool = False):
    """
    Convert a single roman numeral (e.g. 'vi', 'IV', 'V7') into an actual
    chord name in the given key. Handles an explicit trailing '7' for
    dominant/seventh chords (common in blues).
    """
    force_seventh = roman.endswith("7")
    base_roman = roman[:-1] if force_seventh else roman

    scale = build_scale(root, mode)
    numerals = roman_numerals_for_mode(mode)

    # Normalize for lookup (strip ° for matching, but keep quality info)
    try:
        degree_idx = [r.replace("°", "") for r in numerals].index(
            base_roman.replace("°", "")
        )
    except ValueError:
        raise ValueError(f"Unrecognized roman numeral: {roman}")

    quality = TRIAD_QUALITIES[mode][degree_idx]
    note = scale[degree_idx]

    if force_seventh or seventh:
        if quality == "maj":
            quality_key = "dom7" if force_seventh else "maj7"
        elif quality == "min":
            quality_key = "min7"
        else:
            quality_key = "dim"  # dim7 edge case, rare in these progressions
    else:
        quality_key = quality

    suffix = CHORD_SUFFIX.get(quality_key, "")
    return f"{note}{suffix}"


def progression_to_chords(progression, root: str, mode: str):
    return [roman_to_chord(r, root, mode) for r in progression]


# ---------------------------------------------------------------------------
# Genre progression pools (roman numeral progressions)
# ---------------------------------------------------------------------------
# Each entry: (progression list, preferred mode). Genre pools mix common
# real-world progressions from that style. Where a genre strongly implies
# a mode (e.g. blues -> major w/ dominant 7ths), that's noted.

GENRE_PROGRESSIONS = {
    "shoegaze": {
        "default_mode": "major",
        "progressions": [
            (["I", "V", "vi", "IV"], "major"),
            (["vi", "IV", "I", "V"], "major"),
            (["I", "iii", "IV", "vi"], "major"),
            (["IV", "I", "V", "vi"], "major"),
            (["i", "VI", "III", "VII"], "minor"),
            (["i", "iv", "VII", "III"], "minor"),
        ],
        "note": "Shoegaze often layers sus2/sus4 and add9 voicings over "
                "these — try adding the 2nd or 4th on top of open chords "
                "for that wash-of-sound texture.",
    },
    "alt-metal": {
        "default_mode": "minor",
        "progressions": [
            (["i", "VI", "VII"], "minor"),
            (["i", "iv", "v"], "minor"),
            (["i", "VII", "VI", "VII"], "minor"),
            (["i", "III", "VII", "VI"], "minor"),
            (["i", "iv", "VI", "V"], "minor"),
        ],
        "note": "Alt-metal usually plays these as power chords (root + "
                "5th, no 3rd), often palm-muted, frequently in drop tuning. "
                "Chromatic passing chords between i and VII are common too.",
    },
    "blues": {
        "default_mode": "major",
        "progressions": [
            (["I7", "I7", "I7", "I7",
              "IV7", "IV7", "I7", "I7",
              "V7", "IV7", "I7", "V7"], "major"),  # 12-bar blues
            (["I7", "IV7", "I7", "V7"], "major"),
            (["i7", "iv7", "i7", "v7"], "minor"),  # minor blues variant
        ],
        "note": "All chords are dominant/minor 7ths, not plain triads — "
                "that's what gives blues its characteristic tension. Try "
                "adding a quick IV7 in bar 2 ('quick change') for variety.",
    },
    "country": {
        "default_mode": "major",
        "progressions": [
            (["I", "IV", "V", "I"], "major"),
            (["I", "vi", "IV", "V"], "major"),
            (["I", "IV", "I", "V"], "major"),
            (["I", "V", "IV", "I"], "major"),
            (["vi", "IV", "I", "V"], "major"),
        ],
        "note": "Classic country leans on I-IV-V heavily. Try adding "
                "hammer-ons/pull-offs around the I and IV chords, or a "
                "walking bassline connecting chord roots.",
    },
    "pop-rock": {
        "default_mode": "major",
        "progressions": [
            (["I", "V", "vi", "IV"], "major"),
            (["vi", "IV", "I", "V"], "major"),
            (["I", "IV", "vi", "V"], "major"),
            (["ii", "V", "I", "vi"], "major"),
        ],
        "note": "The 'four chord song' progressions — extremely common "
                "across decades of pop and rock.",
    },
}

VALID_GENRES = list(GENRE_PROGRESSIONS.keys())

# ---------------------------------------------------------------------------
# Guitar voicing helper (open-position shapes, common keys only)
# ---------------------------------------------------------------------------

OPEN_CHORD_SHAPES = {
    "C": "x32010", "Cm": "x31013 (or barre 3rd fret)",
    "C#": "barre 4th fret (A-shape)", "C#m": "barre 4th fret (Am-shape)",
    "D": "xx0232", "Dm": "xx0231",
    "D#": "barre 6th fret (A-shape)", "D#m": "barre 6th fret (Am-shape)",
    "E": "022100", "Em": "022000",
    "F": "133211 (barre 1st fret, E-shape)", "Fm": "133111 (barre 1st fret, Em-shape)",
    "F#": "244322 (barre 2nd fret)", "F#m": "244222 (barre 2nd fret)",
    "G": "320003", "Gm": "355333 (barre 3rd fret)",
    "G#": "barre 4th fret (E-shape)", "G#m": "barre 4th fret (Em-shape)",
    "A": "x02220", "Am": "x02210",
    "A#": "x13331 (barre 1st fret, A-shape)", "A#m": "x13321 (barre 1st fret, Am-shape)",
    "B": "x24442 (barre 2nd fret, A-shape)", "Bm": "x24432 (barre 2nd fret, Am-shape)",
}


def suggest_voicing(chord_name: str):
    """
    Look up a simple guitar voicing for a chord. Strips 7ths/dim down to
    their base major/minor shape and notes the extension separately, since
    open-position 7th shapes vary a lot by key.
    """
    base = chord_name
    extension = ""
    for ext in ["maj7", "dom7", "m7", "7", "dim"]:
        if chord_name.endswith(ext) and chord_name != ext:
            base = chord_name[: -len(ext)]
            extension = ext
            break

    shape = OPEN_CHORD_SHAPES.get(base)
    if not shape:
        return f"(no simple open shape for {base} — try a barre chord)"
    if extension:
        return f"{shape}  [base shape; add a {extension} extension by ear or tab lookup]"
    return shape


# Known true open-position shapes (string order low E -> high e).
# None = muted string, 0 = open string, N = fretted at fret N.
# Only chords with a genuine "cowboy chord" open shape are listed here;
# everything else falls back to a computed barre shape below.
OPEN_POSITION_FRETS = {
    ("C", "maj"): [None, 3, 2, 0, 1, 0],
    ("D", "maj"): [None, None, 0, 2, 3, 2],
    ("D", "min"): [None, None, 0, 2, 3, 1],
    ("E", "maj"): [0, 2, 2, 1, 0, 0],
    ("E", "min"): [0, 2, 2, 0, 0, 0],
    ("G", "maj"): [3, 2, 0, 0, 0, 3],
    ("A", "maj"): [None, 0, 2, 2, 2, 0],
    ("A", "min"): [None, 0, 2, 2, 1, 0],
}


def chord_to_frets(chord_name: str):
    """
    Return a 6-element list (low E -> high e string order) of fret
    positions for a playable guitar voicing of the chord: None = muted,
    0 = open, N = fretted at fret N.

    Uses real open-position ("cowboy chord") shapes where one exists.
    Otherwise computes a barre chord using the E-shape or A-shape
    movable pattern (whichever sits in a lower/more natural position),
    the same way guitarists derive barre chords in practice.

    7th/dim chords are approximated using their base major/minor shape,
    matching the caveat already given in suggest_voicing().
    """
    root, quality = parse_chord(chord_name)
    shape_quality = "maj" if quality in ("maj", "dom7", "maj7") else "min"

    key = (root, shape_quality)
    if key in OPEN_POSITION_FRETS:
        return list(OPEN_POSITION_FRETS[key])

    root_idx = NOTES.index(root)
    b_e = (root_idx - NOTES.index("E")) % 12  # E-shape barre fret
    b_a = (root_idx - NOTES.index("A")) % 12  # A-shape barre fret

    if shape_quality == "maj":
        e_shape = [b_e, b_e + 2, b_e + 2, b_e + 1, b_e, b_e]
        a_shape = [None, b_a, b_a + 2, b_a + 2, b_a + 2, b_a]
    else:
        e_shape = [b_e, b_e + 2, b_e + 2, b_e, b_e, b_e]
        a_shape = [None, b_a, b_a + 2, b_a + 2, b_a + 1, b_a]

    return a_shape if b_a < b_e else e_shape


# Standard tuning open-string MIDI notes, low E -> high e
GUITAR_OPEN_STRING_MIDI = [40, 45, 50, 55, 59, 64]


def frets_to_midi_notes(frets):
    """Convert a chord_to_frets()-style list into actual MIDI note numbers."""
    notes = []
    for open_midi, fret in zip(GUITAR_OPEN_STRING_MIDI, frets):
        if fret is not None:
            notes.append(open_midi + fret)
    return notes


# ---------------------------------------------------------------------------
# Chord name -> notes/MIDI (shared by audio synthesis and MIDI export)
# ---------------------------------------------------------------------------

# Semitone intervals from the chord root, by quality
CHORD_INTERVALS = {
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "dim": [0, 3, 6],
    "dom7": [0, 4, 7, 10],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
}

# Reverse of CHORD_SUFFIX: chord-name suffix -> quality key
SUFFIX_TO_QUALITY = {
    "": "maj",
    "m": "min",
    "dim": "dim",
    "7": "dom7",
    "maj7": "maj7",
    "m7": "min7",
}


def parse_chord(chord_name: str):
    """Split a chord name like 'C#m7' into (root, quality)."""
    if len(chord_name) > 1 and chord_name[1] == "#":
        root, suffix = chord_name[:2], chord_name[2:]
    else:
        root, suffix = chord_name[:1], chord_name[1:]

    if root not in NOTES:
        raise ValueError(f"Unrecognized chord root in '{chord_name}'")
    if suffix not in SUFFIX_TO_QUALITY:
        raise ValueError(f"Unrecognized chord suffix in '{chord_name}'")

    return root, SUFFIX_TO_QUALITY[suffix]


def chord_to_midi_notes(chord_name: str, octave: int = 4):
    """
    Convert a chord name into a list of MIDI note numbers, using the
    standard convention where C4 == MIDI note 60.
    """
    root, quality = parse_chord(chord_name)
    root_idx = NOTES.index(root)
    root_midi = 12 * (octave + 1) + root_idx
    return [root_midi + i for i in CHORD_INTERVALS[quality]]


def midi_to_freq(midi_note: int) -> float:
    """Convert MIDI note number to frequency in Hz (A4 = 440Hz = MIDI 69)."""
    return 440.0 * (2 ** ((midi_note - 69) / 12))


# ---------------------------------------------------------------------------
# Audio synthesis + playback
# ---------------------------------------------------------------------------

SAMPLE_RATE = 44100


def synthesize_chord(midi_notes, duration: float = 1.2, sample_rate: int = SAMPLE_RATE):
    """
    Additive sine-wave synthesis of a chord: sums a sine wave per note plus
    a soft second harmonic for a slightly fuller tone, with a short
    attack/release envelope to avoid clicks.
    """
    import numpy as np

    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio = np.zeros_like(t)
    for note in midi_notes:
        freq = midi_to_freq(note)
        audio += np.sin(2 * np.pi * freq * t)
        audio += 0.25 * np.sin(2 * np.pi * (freq * 2) * t)  # soft octave harmonic
    audio /= len(midi_notes)

    attack = int(0.01 * sample_rate)
    release = int(0.2 * sample_rate)
    envelope = np.ones_like(audio)
    if attack > 0:
        envelope[:attack] = np.linspace(0, 1, attack)
    if release > 0 and release < len(envelope):
        envelope[-release:] *= np.linspace(1, 0, release)
    audio *= envelope

    # keep headroom so summed chords don't clip
    audio *= 0.6
    return audio.astype("float32")


def play_audio(audio, sample_rate: int = SAMPLE_RATE):
    """Play a numpy audio buffer through the default output device."""
    try:
        import sounddevice as sd
    except Exception as e:
        print(f"Audio playback unavailable ({e}). Try: pip install numpy sounddevice")
        return False
    try:
        sd.play(audio, sample_rate)
        sd.wait()
        return True
    except Exception as e:
        print(f"Couldn't play audio ({e}). Check your system's audio output device.")
        return False


def play_chord(chord_name: str, octave: int = 4, duration: float = 1.2):
    notes = chord_to_midi_notes(chord_name, octave)
    audio = synthesize_chord(notes, duration)
    play_audio(audio)


def play_progression(chords, octave: int = 4, duration: float = 1.0, gap: float = 0.05):
    """Play a list of chord names in sequence, with a tiny gap between each."""
    try:
        import numpy as np
        import sounddevice as sd
    except Exception as e:
        print(f"Audio playback unavailable ({e}). Try: pip install numpy sounddevice")
        return
    for chord_name in chords:
        notes = chord_to_midi_notes(chord_name, octave)
        audio = synthesize_chord(notes, duration)
        if not play_audio(audio):
            return
        if gap > 0:
            import time
            time.sleep(gap)


# ---------------------------------------------------------------------------
# MIDI export
# ---------------------------------------------------------------------------

def export_midi(chords, filename: str, tempo_bpm: int = 100,
                 beats_per_chord: int = 4, octave: int = 4):
    """
    Write the given chord progression to a standard MIDI file, one chord
    per `beats_per_chord` beats, at the given tempo.
    """
    try:
        import mido
        from mido import MidiFile, MidiTrack, Message, MetaMessage
    except ImportError:
        print("MIDI export needs: pip install mido")
        return False

    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo_bpm)))

    duration_ticks = mid.ticks_per_beat * beats_per_chord

    for chord_name in chords:
        notes = chord_to_midi_notes(chord_name, octave)
        for note in notes:
            track.append(Message("note_on", note=note, velocity=70, time=0))
        for i, note in enumerate(notes):
            track.append(Message("note_off", note=note, velocity=70,
                                  time=duration_ticks if i == 0 else 0))

    mid.save(filename)
    return True


# ---------------------------------------------------------------------------
# Generation logic
# ---------------------------------------------------------------------------

def generate_progression(root: str, genre: str, mode: str = None, seed=None):
    """
    Pick a random progression template for the genre, render it into real
    chords for the given root/mode. Returns (roman_list, chord_list, mode_used, note).
    """
    if genre not in GENRE_PROGRESSIONS:
        raise ValueError(f"Unknown genre: {genre}. Choose from {VALID_GENRES}")

    rng = random.Random(seed)
    pool = GENRE_PROGRESSIONS[genre]["progressions"]

    if mode:
        candidates = [p for p in pool if p[1] == mode]
        if not candidates:
            candidates = pool  # fall back if genre has no progressions in that mode
    else:
        candidates = pool

    roman_progression, prog_mode = rng.choice(candidates)
    chords = progression_to_chords(roman_progression, root, prog_mode)
    note = GENRE_PROGRESSIONS[genre]["note"]
    return roman_progression, chords, prog_mode, note


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def normalize_key(key: str) -> str:
    key = key.strip().capitalize()
    # accept flats and convert to sharps for internal lookup
    flat_to_sharp = {v: k for k, v in ENHARMONIC_FLATS.items()}
    if key in flat_to_sharp:
        return flat_to_sharp[key]
    if key not in NOTES:
        raise ValueError(f"'{key}' isn't a recognized note. Use A-G, optionally with # or b.")
    return key


def display_key(note: str) -> str:
    """Show flats for keys that are more commonly written that way."""
    return note  # kept simple/sharp-based for consistency; flip if you prefer flats


def print_progression(root, genre, roman, chords, mode_used, note, show_guitar):
    print(f"\nKey: {display_key(root)} {mode_used}   Genre: {genre}")
    print(f"Roman:  {' - '.join(roman)}")
    print(f"Chords: {' - '.join(chords)}")
    if show_guitar:
        print("Guitar shapes:")
        for r, c in zip(roman, chords):
            print(f"  {r:>5}  {c:<6} {suggest_voicing(c)}")
    print(f"Note: {note}")


def print_help():
    print("""
Commands:
  p, play            play the full progression in order
  p N, play N        play just chord number N (e.g. 'p 2')
  r ORDER             rearrange chords, e.g. 'r 3,1,2,4' (1-indexed, comma separated)
  s, show             show the current progression
  g, generate         generate a new progression (same key/genre)
  e FILE, export FILE export current progression to a .mid file
  o N, octave N       set playback/export octave (default 4)
  t N, tempo N        set export tempo in BPM (default 100)
  h, help             show this help
  q, quit             exit
""")


def interactive_session(root, genre, mode, seed=None):
    roman, chords, mode_used, note = generate_progression(root, genre, mode=mode, seed=seed)
    octave = 4
    tempo = 100

    print_progression(root, genre, roman, chords, mode_used, note, show_guitar=True)
    print_help()

    while True:
        try:
            raw = input("chord-gen> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("q", "quit", "exit"):
            break

        elif cmd in ("h", "help"):
            print_help()

        elif cmd in ("s", "show"):
            for i, (r, c) in enumerate(zip(roman, chords), start=1):
                print(f"  {i}. {r:>5}  {c:<6} {suggest_voicing(c)}")

        elif cmd in ("p", "play"):
            if arg:
                try:
                    idx = int(arg) - 1
                    if not 0 <= idx < len(chords):
                        print(f"Chord number must be 1-{len(chords)}.")
                        continue
                    print(f"Playing {chords[idx]}...")
                    play_chord(chords[idx], octave=octave)
                except ValueError:
                    print("Usage: play [chord number]")
            else:
                print("Playing progression: " + " - ".join(chords))
                play_progression(chords, octave=octave)

        elif cmd in ("r", "reorder"):
            try:
                new_order = [int(x.strip()) - 1 for x in arg.split(",")]
                if sorted(new_order) != list(range(len(chords))):
                    print(f"Give each of 1-{len(chords)} exactly once, e.g. 'r 3,1,2,4'")
                    continue
                roman = [roman[i] for i in new_order]
                chords = [chords[i] for i in new_order]
                print("Reordered. New progression:")
                for i, (r, c) in enumerate(zip(roman, chords), start=1):
                    print(f"  {i}. {r:>5}  {c}")
            except ValueError:
                print("Usage: reorder 3,1,2,4  (comma separated, 1-indexed)")

        elif cmd in ("g", "generate"):
            roman, chords, mode_used, note = generate_progression(root, genre, mode=mode)
            print_progression(root, genre, roman, chords, mode_used, note, show_guitar=True)

        elif cmd in ("o", "octave"):
            try:
                octave = int(arg)
                print(f"Octave set to {octave}.")
            except ValueError:
                print("Usage: octave 4")

        elif cmd in ("t", "tempo"):
            try:
                tempo = int(arg)
                print(f"Tempo set to {tempo} BPM.")
            except ValueError:
                print("Usage: tempo 100")

        elif cmd in ("e", "export"):
            if not arg:
                print("Usage: export filename.mid")
                continue
            filename = arg if arg.endswith(".mid") else arg + ".mid"
            if export_midi(chords, filename, tempo_bpm=tempo, octave=octave):
                print(f"Exported to {filename}")

        else:
            print("Unknown command. Type 'h' for help.")


def run_cli():
    parser = argparse.ArgumentParser(description="Generate genre-flavored chord progressions.")
    parser.add_argument("--key", help="Root note, e.g. A, C#, Eb (default: random)")
    parser.add_argument("--mode", choices=["major", "minor"], help="Force major or minor")
    parser.add_argument("--genre", choices=VALID_GENRES, help="Genre style (default: random)")
    parser.add_argument("--count", type=int, default=1, help="How many progressions to generate")
    parser.add_argument("--guitar", action="store_true", help="Show guitar voicing suggestions")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--play", action="store_true", help="Play the progression out loud")
    parser.add_argument("--export", metavar="FILE", help="Export progression to a .mid file")
    parser.add_argument("--tempo", type=int, default=100, help="Tempo in BPM for --export (default 100)")
    parser.add_argument("--octave", type=int, default=4, help="Octave for playback/export (default 4)")
    parser.add_argument("--interactive", action="store_true",
                         help="Enter interactive mode: play/replay chords, rearrange, export")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    root = normalize_key(args.key) if args.key else rng.choice(NOTES)
    genre = args.genre if args.genre else rng.choice(VALID_GENRES)

    if args.interactive:
        interactive_session(root, genre, args.mode, seed=args.seed)
        return

    for i in range(args.count):
        roman, chords, mode_used, note = generate_progression(
            root, genre, mode=args.mode, seed=(args.seed + i if args.seed is not None else None)
        )
        print_progression(root, genre, roman, chords, mode_used, note, args.guitar)

        if args.play:
            print("Playing...")
            play_progression(chords, octave=args.octave)

        if args.export:
            filename = args.export if args.export.endswith(".mid") else args.export + ".mid"
            # if generating multiple, avoid overwriting the same file each loop
            if args.count > 1:
                base, _, ext = filename.rpartition(".")
                filename = f"{base}_{i+1}.{ext}"
            if export_midi(chords, filename, tempo_bpm=args.tempo, octave=args.octave):
                print(f"Exported to {filename}")


if __name__ == "__main__":
    run_cli()