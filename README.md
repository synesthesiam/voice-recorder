# Voice Recorder

Small [tkinter](https://wiki.python.org/moin/TkInter) Python program for recording voice samples.

Uses [`arecord`](https://linux.die.net/man/1/arecord) to record audio, and expects prompts to be in the same format as [CMU Arctic](http://www.festvox.org/cmu_arctic/):

```
( prompt_id1 "Text of prompt 1" )
( prompt_id2 "Text of prompt 2" )
...
```

![Screenshot](img/screenshot.png)

## Running

Run from a terminal:

```sh
$ python3 record.py <DEVICE> <PROMPTS> <WAV>
```

where `<DEVICE>` is an ALSA device from `arecord -L`, `<PROMPTS>` is a text file with prompts (CMU Arctic format), and `<WAV>` is a directory to write WAV files to.

## Using

Click the "RECORD" button and speak the text provided in the prompt. When finished, click "FINISH" (same button).

If you'd like to re-record, you may click "RECORD" again. Files are not overwritten; a timestamp is appended to the prompt id for each WAV file.

Click "Play" to hear the most recent recording. Click "Next" to move to the next prompt.

When starting up, prompts with existing WAV files will be automatically skipped.
