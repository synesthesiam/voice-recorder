#!/usr/bin/env python3
"""
Simple tkinter application for recording voice samples with text prompts.

Reads prompts from a text file in the CMU Arctic format.
Records 48Khz, 16-bit, stereo WAV files using "arecord".
Writes WAV files to a directory with a timestamp appended to the prompt id.
"""
import argparse
import os
import re
import signal
import subprocess
import threading
import time
import tkinter as tk
import typing
from pathlib import Path
from tkinter import ttk

# Directory of this script
_DIR = Path(__file__).parent

# Regex for prompt lines
_ARCTIC_LINE = re.compile(r'^\s*\(\s*([^ ]+)\s+"([^"]+)"\s*\)\s*$')


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("device", help="Name of ALSA recording device")
    parser.add_argument("prompts", help="File with prompts (CMU Arctic format)")
    parser.add_argument("wav", help="Directory to store WAV files")
    args = parser.parse_args()

    wav_dir = Path(args.wav)
    wav_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Read Prompts
    # -------------------------------------------------------------------------

    prompts: typing.Dict[str, str] = {}
    with open(args.prompts, "r") as prompts_file:
        for line in prompts_file:
            line = line.strip()
            if line:
                # ( prompt_id "Text for prompt" )
                match = _ARCTIC_LINE.match(line)
                if match:
                    prompt_id = match.group(1)
                    prompt_text = match.group(2)
                    prompts[prompt_id] = prompt_text

    assert prompts, "No prompts!"

    # Remaining prompt ids
    prompts_left: typing.List[str] = list(prompts.keys())

    # Total number of prompts
    total_prompts: int = len(prompts_left)

    # Current prompt id or None
    current_prompt_id: typing.Optional[str] = None

    # Last recorded WAV path or None
    last_wav_path: typing.Optional[Path] = None

    # -------------------------------------------------------------------------
    # Record Samples
    # -------------------------------------------------------------------------

    window = tk.Tk()
    window.title("Voice Recorder")

    # Text box with prompt text
    textbox = tk.Text(window, height=10, wrap=tk.WORD)
    textbox.config(font=("Courier", 20))
    textbox.pack(fill=tk.BOTH, padx=10, pady=10)

    # Progress bar for how many prompts are done
    progress = ttk.Progressbar(
        window, orient=tk.HORIZONTAL, length=100, mode="determinate"
    )
    progress.pack(fill="x", padx=10, pady=10)

    record_button = None
    play_button = None
    next_button = None

    def do_next(*_args):
        """Get the next prompt and show text."""
        nonlocal current_prompt_id
        current_prompt_id = None
        last_wav_path = None
        next_button.config(bg="#F0F0F0")
        if prompts_left:
            wav_names = [wav_path.name for wav_path in wav_dir.glob("*.wav")]
            current_prompt_id = prompts_left.pop()
            wav_prefix = f"{current_prompt_id}_"
            while has_wav(wav_names, wav_prefix):
                current_prompt_id = None
                if prompts_left:
                    current_prompt_id = prompts_left.pop()
                    wav_prefix = f"{current_prompt_id}_"
                else:
                    break

        if current_prompt_id:
            textbox.delete(1.0, tk.END)
            textbox.insert(1.0, prompts[current_prompt_id])
            next_button["state"] = tk.DISABLED
        else:
            tk.messagebox.showinfo(message="All done :)")

        progress["value"] = 100 * ((total_prompts - len(prompts_left)) / total_prompts)

    def do_play(*_args):
        """Play last recorded WAV file"""
        print(last_wav_path)
        if last_wav_path and last_wav_path.is_file():
            threading.Thread(
                target=lambda: subprocess.check_call(
                    ["aplay", "-q", str(last_wav_path)]
                )
            ).start()

    recording = False
    record_proc = None

    def do_record(*_args):
        """Toggle recording."""
        nonlocal recording, record_proc, last_wav_path

        if recording:
            # Stop recording
            recording = False
            window.config(background="#F0F0F0")
            record_button.config(activebackground="red")
            record_button["text"] = "RECORD"
            play_button["state"] = tk.NORMAL
            next_button["state"] = tk.NORMAL
            next_button.config(bg="yellow")

            if record_proc:
                os.kill(record_proc.pid, signal.SIGTERM)
                record_proc.terminate()
                record_proc.wait()
                record_proc = None

                if current_prompt_id and last_wav_path:
                    # Write prompt text to file
                    text_path = last_wav_path.with_suffix(".txt")
                    text_path.write_text(prompts[current_prompt_id])
        else:
            # Start recording
            if current_prompt_id:
                recording = True
                window.config(background="red")
                record_button.config(activebackground="yellow")
                record_button["text"] = "FINISH"
                play_button["state"] = tk.DISABLED
                next_button.config(bg="#F0F0F0")

                last_wav_path = (
                    wav_dir / f"{current_prompt_id}_{time.time()}"
                ).with_suffix(".wav")
                record_proc = subprocess.Popen(
                    [
                        "arecord",
                        "-q",
                        "-D",
                        args.device,
                        "-r",
                        "48000",
                        "-c",
                        "2",
                        "-f",
                        "S16_LE",
                        str(last_wav_path),
                    ]
                )
            else:
                tk.messagebox.showinfo(message="No prompt")

    # -------------------------------------------------------------------------

    bottom_frame = tk.Frame(window).pack()

    record_button = tk.Button(bottom_frame, text="RECORD", command=do_record)
    record_button.config(bg="white", activebackground="red", font=("Courier", 20))
    record_button.pack(side="left", padx=10, pady=10)

    next_button = tk.Button(bottom_frame, text="Next", command=do_next)
    next_button.config(font=("Courier", 20))
    next_button.pack(side="right", padx=10, pady=10)

    play_button = tk.Button(bottom_frame, text="Play", command=do_play)
    play_button.config(font=("Courier", 20))
    play_button.pack(side="right", padx=10, pady=10)

    do_next()

    window.mainloop()


# -----------------------------------------------------------------------------


def has_wav(wav_names, wav_prefix):
    """True if WAV file with prefix already exists."""
    for wav_name in wav_names:
        if wav_name.startswith(wav_prefix):
            return True

    return False


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
