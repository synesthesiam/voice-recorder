#!/usr/bin/env python3
"""
Simple tkinter application for verifying voice samples with text prompts.

Shows plot of WAV data. Left click to add trim start, right click to add trim
end. Play and Verify will respect trimmings.

Change prompt in text box to have different text written with Verify.
"""
import argparse
import logging
import os
import re
import shutil
import subprocess
import threading
import time
import tkinter as tk
import tkinter.messagebox
import typing
from pathlib import Path
from tkinter import ttk

import matplotlib

matplotlib.use("TkAgg")

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.io.wavfile import read as wav_read

# Directory of this script
_DIR = Path(__file__).parent

_LOGGER = logging.getLogger("verify")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_dir", help="Directory with input WAV files and text prompts"
    )
    parser.add_argument(
        "output_dir", help="Directory to write output WAV files and text prompts to"
    )
    parser.add_argument(
        "done_dir", help="Directory to move completed WAV files and text prompts to"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    _LOGGER.debug(args)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    done_dir = Path(args.done_dir)
    done_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Load WAV files to be verified
    # -------------------------------------------------------------------------

    todo_prompts: typing.Dict[Path, str] = {}
    for wav_path in input_dir.glob("*.wav"):
        text_path = wav_path.with_suffix(".txt")
        if not text_path.is_file():
            _LOGGER.warn("Missing %s", text_path)
            continue

        rel_wav_path = wav_path.relative_to(input_dir)
        todo_prompts[rel_wav_path] = text_path.read_text().strip()

    todo_paths = list(sorted(todo_prompts.keys()))
    total_paths = len(todo_paths)
    current_path: typing.Optional[Path] = None

    # -------------------------------------------------------------------------
    # Verify Samples
    # -------------------------------------------------------------------------

    window = tk.Tk()
    window.title("Sample Verifier")

    # Text box with prompt text
    textbox = tk.Text(window, height=3, wrap=tk.WORD)
    textbox.config(font=("Courier", 20))
    textbox.pack(fill=tk.X, padx=10, pady=10)

    # Progress bar for how many prompts are done
    progress = ttk.Progressbar(
        window, orient=tk.HORIZONTAL, length=100, mode="determinate"
    )
    progress.pack(fill="x", padx=10, pady=10)

    # Label with current WAV file
    path_label = tk.Label(window)
    path_label.pack(fill=tk.X, padx=10, pady=10)

    # Plot of WAV data
    figure = Figure(figsize=(8, 3), dpi=100)
    plot = figure.add_subplot(1, 1, 1)
    figure.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=0, hspace=0)

    canvas = FigureCanvasTkAgg(figure, window)
    canvas.get_tk_widget().pack(fill=tk.BOTH, padx=10, pady=10)

    # Start of trimming
    left_cut = None

    # End of trimming
    right_cut = None

    # Sample rate (Hz) of current WAV file
    sample_rate = None

    def redraw():
        """Clears and re-draws WAV plot with trim lines."""
        nonlocal sample_rate
        plot.cla()

        if current_path:
            wav_path = input_dir / current_path
            _LOGGER.debug("Loading %s", wav_path)
            sample_rate, wav_data = wav_read(str(wav_path))
            audio = wav_data[:, 0]
            plot.plot(audio, color="blue")
            plot.set_xlim(0, len(audio))

            # Trim lines
            if left_cut is not None:
                plot.axvline(linewidth=2, x=left_cut, color="red")

            if right_cut is not None:
                plot.axvline(linewidth=2, x=right_cut, color="green")

        canvas.draw()

    def onclick(event):
        """Handles mouse clicks on plot."""
        nonlocal left_cut, right_cut

        if event.button == 1:
            # Left click
            left_cut = event.xdata
            redraw()
        elif (event.button == 2) and current_path:
            # Middle click
            wav_path = input_dir / current_path
            if wav_path and wav_path.is_file():
                from_sec = event.xdata / sample_rate
                play_command = [
                    "play",
                    "--ignore-length",
                    str(wav_path),
                    "trim",
                    str(from_sec),
                ]

                if right_cut is not None:
                    to_sec = right_cut / sample_rate
                    play_command.append(f"={to_sec}")
                threading.Thread(
                    target=lambda: subprocess.check_call(play_command)
                ).start()
        elif event.button == 3:
            # Right click
            right_cut = event.xdata
            redraw()

    canvas.mpl_connect("button_press_event", onclick)

    skip_button = None
    play_button = None
    verify_button = None

    def do_next(*_args):
        """Get the next prompt and show text."""
        nonlocal current_path, left_cut, right_cut
        left_cut = None
        right_cut = None
        current_path = None
        if todo_paths:
            current_path = todo_paths.pop()

        if current_path:
            # Update prompt and WAV plot
            wav_path = input_dir / current_path
            textbox.delete(1.0, tk.END)
            textbox.insert(1.0, todo_prompts[current_path])
            path_label["text"] = str(wav_path)
            redraw()
        else:
            tkinter.messagebox.showinfo(message="All done :)")
            path_label["text"] = ""

        # Update progress bar
        progress["value"] = 100 * ((total_paths - len(todo_paths)) / total_paths)

    def do_play(*_args):
        """Play current WAV file"""
        wav_path = input_dir / current_path
        _LOGGER.debug("Playing %s", wav_path)
        if wav_path and wav_path.is_file():
            play_command = ["play", "--ignore-length", str(wav_path)]

            if (left_cut is not None) or (right_cut is not None):
                # Play clipped WAV file
                from_sec = 0 if left_cut is None else (left_cut / sample_rate)
                play_command.extend(["trim", str(from_sec)])

                if right_cut is not None:
                    to_sec = right_cut / sample_rate
                    play_command.append(f"={to_sec}")

            _LOGGER.debug(play_command)
            threading.Thread(target=lambda: subprocess.check_call(play_command)).start()

    def do_verify(*_args):
        """Verify recording."""
        if current_path:
            input_path = input_dir / current_path
            output_path = output_dir / current_path
            sox_command = ["sox", "--ignore-length", str(input_path), str(output_path)]

            if (left_cut is not None) or (right_cut is not None):
                # Write clipped WAV file
                from_sec = 0 if left_cut is None else (left_cut / sample_rate)
                sox_command.extend(["trim", str(from_sec)])

                if right_cut is not None:
                    to_sec = right_cut / sample_rate
                    sox_command.append(f"={to_sec}")

            _LOGGER.debug(sox_command)
            subprocess.check_call(sox_command)

            # Write prompt
            prompt_path = output_dir / current_path.with_suffix(".txt")
            prompt_path.write_text(textbox.get(1.0, tk.END).strip())

            # Move completed WAV file
            done_path = done_dir / current_path
            shutil.move(input_path, done_path)

            # Move completed prompt
            input_prompt_path = input_dir / current_path.with_suffix(".txt")
            if input_prompt_path.is_file():
                done_prompt_path = done_dir / current_path.with_suffix(".txt")
                shutil.move(input_prompt_path, done_prompt_path)

            do_next()
        else:
            tkinter.messagebox.showinfo(message="No prompt")

    # -------------------------------------------------------------------------

    bottom_frame = tk.Frame(window).pack()

    skip_button = tk.Button(bottom_frame, text="Skip", command=do_next)
    skip_button.config(bg="white", activebackground="red", font=("Courier", 20))
    skip_button.pack(side="left", padx=10, pady=10)

    verify_button = tk.Button(bottom_frame, text="Verify", command=do_verify)
    verify_button.config(
        activebackground="green", activeforeground="white", font=("Courier", 20)
    )
    verify_button.pack(side="right", padx=10, pady=10)

    play_button = tk.Button(bottom_frame, text="Play", command=do_play)
    play_button.config(font=("Courier", 20))
    play_button.pack(side="right", padx=10, pady=10)

    do_next()

    window.mainloop()


# -----------------------------------------------------------------------------


if __name__ == "__main__":
    main()
