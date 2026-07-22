#!/usr/bin/env python3
"""
Chord Progression Generator — GUI
===================================
A desktop app on top of chord_gen.py: pick a key/mode/genre, generate a
progression, and watch it played on a piano keyboard or guitar fretboard
while it plays out loud. Click any chord to play it individually, click
two chords in a row to swap them, and export the whole thing to MIDI.

Requires chord_gen.py in the same folder.

Run:
    python chord_gen_gui.py

Dependencies (same as the CLI):
    pip install numpy sounddevice mido
"""

import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import chord_gen as cg

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

BG = "#1e1e24"
PANEL_BG = "#2a2a33"
ACCENT = "#7dd3fc"
HIGHLIGHT = "#facc15"
TEXT = "#f4f4f5"
MUTED_TEXT = "#9ca3af"

PIANO_START_MIDI = 48   # C3
PIANO_OCTAVES = 3
WHITE_W, WHITE_H = 34, 120
BLACK_W, BLACK_H = 20, 74

WHITE_OFFSETS = {0: 0, 2: 1, 4: 2, 5: 3, 7: 4, 9: 5, 11: 6}   # semitone -> white slot
BLACK_OFFSETS = {1: 0.62, 3: 1.65, 6: 3.60, 8: 4.62, 10: 5.65}  # semitone -> x in white-widths

FRET_COUNT = 4
FRET_X_GAP = 46
FRET_Y_GAP = 46
FRETBOARD_TOP = 46
FRETBOARD_LEFT = 60


class ChordGenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chord Progression Generator")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.roman = []
        self.chords = []
        self.mode_used = "major"
        self.view = tk.StringVar(value="piano")
        self.octave = tk.IntVar(value=4)
        self.tempo = tk.IntVar(value=100)
        self.is_playing = False
        self.stop_requested = False
        self._after_id = None
        self.chord_buttons = []
        self.selected_index = None  # for click-to-swap reordering

        self._build_controls()
        self._build_chord_strip()
        self._build_now_playing()
        self._build_visualizer()

        self._generate()

    # -------------------------------------------------------------- controls
    def _build_controls(self):
        frame = tk.Frame(self.root, bg=BG, padx=12, pady=10)
        frame.grid(row=0, column=0, sticky="ew")

        tk.Label(frame, text="Key", bg=BG, fg=TEXT).grid(row=0, column=0, padx=(0, 4))
        self.key_var = tk.StringVar(value="A")
        ttk.Combobox(frame, textvariable=self.key_var, values=cg.NOTES,
                     width=4, state="readonly").grid(row=0, column=1, padx=(0, 12))

        tk.Label(frame, text="Mode", bg=BG, fg=TEXT).grid(row=0, column=2, padx=(0, 4))
        self.mode_var = tk.StringVar(value="minor")
        ttk.Combobox(frame, textvariable=self.mode_var, values=["major", "minor", "auto"],
                     width=7, state="readonly").grid(row=0, column=3, padx=(0, 12))

        tk.Label(frame, text="Genre", bg=BG, fg=TEXT).grid(row=0, column=4, padx=(0, 4))
        self.genre_var = tk.StringVar(value="shoegaze")
        ttk.Combobox(frame, textvariable=self.genre_var, values=cg.VALID_GENRES,
                     width=10, state="readonly").grid(row=0, column=5, padx=(0, 12))

        tk.Button(frame, text="Generate", command=self._generate,
                  bg=ACCENT, fg="#111", activebackground=ACCENT,
                  relief="flat", padx=10).grid(row=0, column=6, padx=(0, 6))

        tk.Button(frame, text="▶ Play All", command=self._play_all,
                  bg="#22c55e", fg="#111", activebackground="#22c55e",
                  relief="flat", padx=10).grid(row=0, column=7, padx=(0, 6))

        tk.Button(frame, text="⏹ Stop", command=self._stop,
                  bg="#ef4444", fg="#111", activebackground="#ef4444",
                  relief="flat", padx=10).grid(row=0, column=8, padx=(0, 6))

        tk.Button(frame, text="Export MIDI…", command=self._export,
                  bg=PANEL_BG, fg=TEXT, activebackground=PANEL_BG,
                  relief="flat", padx=10).grid(row=0, column=9, padx=(0, 6))

        tk.Label(frame, text="Octave", bg=BG, fg=TEXT).grid(row=1, column=0, pady=(8, 0))
        tk.Spinbox(frame, from_=2, to=6, textvariable=self.octave, width=4
                   ).grid(row=1, column=1, pady=(8, 0), sticky="w")

        tk.Label(frame, text="Tempo (BPM)", bg=BG, fg=TEXT).grid(row=1, column=2, pady=(8, 0))
        tk.Spinbox(frame, from_=40, to=220, textvariable=self.tempo, width=5
                   ).grid(row=1, column=3, pady=(8, 0), sticky="w")

        view_frame = tk.Frame(frame, bg=BG)
        view_frame.grid(row=1, column=4, columnspan=3, pady=(8, 0), sticky="w")
        tk.Radiobutton(view_frame, text="Piano", variable=self.view, value="piano",
                       command=self._redraw_visualizer, bg=BG, fg=TEXT,
                       selectcolor=PANEL_BG, activebackground=BG).pack(side="left")
        tk.Radiobutton(view_frame, text="Guitar", variable=self.view, value="guitar",
                       command=self._redraw_visualizer, bg=BG, fg=TEXT,
                       selectcolor=PANEL_BG, activebackground=BG).pack(side="left")

    # ---------------------------------------------------------- chord strip
    def _build_chord_strip(self):
        self.strip_frame = tk.Frame(self.root, bg=BG, padx=12, pady=4)
        self.strip_frame.grid(row=1, column=0, sticky="ew")
        tk.Label(self.strip_frame,
                 text="Click a chord to play it. Click two chords in a row to swap them.",
                 bg=BG, fg=MUTED_TEXT, font=("Segoe UI", 8)).pack(anchor="w")
        self.strip_inner = tk.Frame(self.strip_frame, bg=BG)
        self.strip_inner.pack(fill="x", pady=(4, 0))

    def _rebuild_chord_strip(self):
        for w in self.strip_inner.winfo_children():
            w.destroy()
        self.chord_buttons = []
        for i, (r, c) in enumerate(zip(self.roman, self.chords)):
            btn = tk.Button(
                self.strip_inner,
                text=f"{r}\n{c}",
                width=6, height=2,
                bg=PANEL_BG, fg=TEXT, activebackground=ACCENT,
                relief="flat", font=("Segoe UI", 10, "bold"),
                command=lambda idx=i: self._on_chord_click(idx),
            )
            btn.grid(row=0, column=i, padx=4)
            self.chord_buttons.append(btn)

    def _on_chord_click(self, idx):
        if self.selected_index is None:
            self.selected_index = idx
            self.chord_buttons[idx].configure(bg=ACCENT, fg="#111")
            self._play_chord_index(idx)
        else:
            if self.selected_index != idx:
                self.roman[self.selected_index], self.roman[idx] = \
                    self.roman[idx], self.roman[self.selected_index]
                self.chords[self.selected_index], self.chords[idx] = \
                    self.chords[idx], self.chords[self.selected_index]
                self._rebuild_chord_strip()
            else:
                self.chord_buttons[idx].configure(bg=PANEL_BG, fg=TEXT)
            self.selected_index = None

    # ------------------------------------------------------- now playing UI
    def _build_now_playing(self):
        frame = tk.Frame(self.root, bg=BG, padx=12, pady=6)
        frame.grid(row=2, column=0, sticky="ew")
        self.now_playing_var = tk.StringVar(value="—")
        tk.Label(frame, textvariable=self.now_playing_var, bg=BG, fg=HIGHLIGHT,
                 font=("Segoe UI", 22, "bold")).pack(side="left")
        self.genre_note_var = tk.StringVar(value="")
        tk.Label(frame, textvariable=self.genre_note_var, bg=BG, fg=MUTED_TEXT,
                 font=("Segoe UI", 9), wraplength=520, justify="left"
                 ).pack(side="left", padx=(20, 0))

    # --------------------------------------------------------- visualizer
    def _build_visualizer(self):
        frame = tk.Frame(self.root, bg=BG, padx=12, pady=10)
        frame.grid(row=3, column=0)
        self.canvas = tk.Canvas(frame, width=760, height=220, bg=PANEL_BG,
                                 highlightthickness=0)
        self.canvas.pack()

    def _redraw_visualizer(self, highlighted_midi=None, chord_frets=None):
        highlighted_midi = highlighted_midi or set()
        self.canvas.delete("all")
        if self.view.get() == "piano":
            self._draw_piano(highlighted_midi)
        else:
            self._draw_guitar(chord_frets)

    # --- piano ---
    def _draw_piano(self, highlighted_midi):
        # first pass: white keys
        for octv in range(PIANO_OCTAVES):
            base = PIANO_START_MIDI + 12 * octv
            for semitone, slot in sorted(WHITE_OFFSETS.items(), key=lambda kv: kv[1]):
                midi_note = base + semitone
                x = 20 + (octv * 7 + slot) * WHITE_W
                fill = HIGHLIGHT if midi_note in highlighted_midi else "white"
                self.canvas.create_rectangle(x, 40, x + WHITE_W, 40 + WHITE_H,
                                              fill=fill, outline="#444", width=1)
        # second pass: black keys on top
        for octv in range(PIANO_OCTAVES):
            base = PIANO_START_MIDI + 12 * octv
            for semitone, offset in BLACK_OFFSETS.items():
                midi_note = base + semitone
                x = 20 + (octv * 7) * WHITE_W + offset * WHITE_W - BLACK_W / 2
                fill = HIGHLIGHT if midi_note in highlighted_midi else "#111"
                self.canvas.create_rectangle(x, 40, x + BLACK_W, 40 + BLACK_H,
                                              fill=fill, outline="#000", width=1)

    # --- guitar ---
    def _draw_guitar(self, chord_frets):
        # 6 vertical strings, low E (left) -> high e (right)
        strings_x = [FRETBOARD_LEFT + i * FRET_X_GAP for i in range(6)]
        string_labels = ["E", "A", "D", "G", "B", "e"]

        frets = chord_frets or [None] * 6
        played_frets = [f for f in frets if f is not None and f > 0]
        if played_frets and min(played_frets) > 4:
            start_fret = min(played_frets)
            show_nut = False
        else:
            start_fret = 0
            show_nut = True

        top = FRETBOARD_TOP
        bottom = top + FRET_COUNT * FRET_Y_GAP

        # strings
        for x, label in zip(strings_x, string_labels):
            self.canvas.create_line(x, top, x, bottom, fill="#888", width=2)
            self.canvas.create_text(x, bottom + 16, text=label, fill=MUTED_TEXT,
                                     font=("Segoe UI", 9))

        # frets (horizontal)
        for i in range(FRET_COUNT + 1):
            y = top + i * FRET_Y_GAP
            width = 4 if (show_nut and i == 0) else 2
            self.canvas.create_line(strings_x[0], y, strings_x[-1], y,
                                     fill="#eee" if (show_nut and i == 0) else "#666",
                                     width=width)

        if not show_nut:
            self.canvas.create_text(FRETBOARD_LEFT - 30, top + FRET_Y_GAP / 2,
                                     text=f"{start_fret}fr", fill=TEXT,
                                     font=("Segoe UI", 10, "bold"))

        # markers per string
        for x, fret in zip(strings_x, frets):
            if fret is None:
                self.canvas.create_text(x, top - 16, text="✕", fill="#ef4444",
                                         font=("Segoe UI", 11, "bold"))
            elif fret == 0:
                self.canvas.create_oval(x - 8, top - 24, x + 8, top - 8,
                                         outline=HIGHLIGHT, width=2)
            else:
                row = fret - start_fret if not show_nut else fret
                if 0 <= row <= FRET_COUNT:
                    y = top + (row - 0.5) * FRET_Y_GAP
                    self.canvas.create_oval(x - 10, y - 10, x + 10, y + 10,
                                             fill=HIGHLIGHT, outline="#000")

    # ------------------------------------------------------------- actions
    def _generate(self):
        self._stop()
        mode = None if self.mode_var.get() == "auto" else self.mode_var.get()
        try:
            roman, chords, mode_used, note = cg.generate_progression(
                self.key_var.get(), self.genre_var.get(), mode=mode
            )
        except Exception as e:
            messagebox.showerror("Generation error", str(e))
            return
        self.roman, self.chords, self.mode_used = roman, chords, mode_used
        self.genre_note_var.set(note)
        self.now_playing_var.set("—")
        self._rebuild_chord_strip()
        self._redraw_visualizer()

    def _export(self):
        if not self.chords:
            return
        path = filedialog.asksaveasfilename(defaultextension=".mid",
                                             filetypes=[("MIDI file", "*.mid")])
        if not path:
            return
        ok = cg.export_midi(self.chords, path, tempo_bpm=self.tempo.get(),
                             octave=self.octave.get())
        if ok:
            messagebox.showinfo("Exported", f"Saved to {path}")
        else:
            messagebox.showerror("Export failed",
                                  "Make sure mido is installed: pip install mido")

    def _highlight_chord(self, idx):
        for i, btn in enumerate(self.chord_buttons):
            btn.configure(bg=(ACCENT if i == idx else PANEL_BG),
                          fg=("#111" if i == idx else TEXT))

    def _show_chord(self, idx):
        chord_name = self.chords[idx]
        self.now_playing_var.set(f"{chord_name}   ({self.roman[idx]})")
        midi_notes = set(cg.chord_to_midi_notes(chord_name, octave=self.octave.get()))
        frets = cg.chord_to_frets(chord_name)
        self._redraw_visualizer(highlighted_midi=midi_notes, chord_frets=frets)

    def _play_chord_index(self, idx):
        if not self.chords:
            return
        self._highlight_chord(idx)
        self._show_chord(idx)
        chord_name = self.chords[idx]
        notes = cg.chord_to_midi_notes(chord_name, octave=self.octave.get())
        audio = cg.synthesize_chord(notes, duration=1.0)
        threading.Thread(target=cg.play_audio, args=(audio,), daemon=True).start()

    def _play_all(self):
        if not self.chords or self.is_playing:
            return
        self.is_playing = True
        self.stop_requested = False
        self._play_sequence(0)

    def _play_sequence(self, idx):
        if self.stop_requested or idx >= len(self.chords):
            self.is_playing = False
            self._highlight_chord(-1)
            self.now_playing_var.set("—")
            self._redraw_visualizer()
            return
        self._highlight_chord(idx)
        self._show_chord(idx)
        chord_name = self.chords[idx]
        notes = cg.chord_to_midi_notes(chord_name, octave=self.octave.get())
        duration = 60.0 / max(self.tempo.get(), 1) * 2  # ~2 beats per chord
        audio = cg.synthesize_chord(notes, duration=duration)
        threading.Thread(target=cg.play_audio, args=(audio,), daemon=True).start()
        self._after_id = self.root.after(int(duration * 1000) + 60,
                                          lambda: self._play_sequence(idx + 1))

    def _stop(self):
        self.stop_requested = True
        self.is_playing = False
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass  # no audio backend available/configured; nothing to stop


def main():
    root = tk.Tk()
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    app = ChordGenApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()