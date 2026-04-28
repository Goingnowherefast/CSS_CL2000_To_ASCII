# CL2000 → Vector ASC Converter

A lightweight Python desktop application that converts **CSS CL2000 CAN logger TXT files** into **Vector ASC format** compatible with CANalyzer and CANoe.

---

## What It Does

CL2000 data loggers export CAN bus captures as semicolon-delimited `.TXT` files. This tool converts those files into the `.asc` format used by Vector tools (CANalyzer, CANoe), allowing you to replay, analyze, and filter captures in a professional CAN analysis environment.

- Converts single files or merges multiple split logs into one continuous `.asc`
- Preserves relative timestamps with millisecond precision
- Handles standard (11-bit) and extended (29-bit) CAN IDs
- Reads logger metadata (bitrate, session time) from the file header

---

## Requirements

- **Python 3.7+** — [Download here](https://www.python.org/downloads/)
- No third-party libraries required — uses Python standard library only (`tkinter`, `re`, `os`, `threading`)

---

## How to Run

1. Download `cl2000_to_asc.py`
2. Open a terminal or command prompt in the same folder
3. Run:

```
python cl2000_to_asc.py
```

The GUI will launch.

---

## Usage

1. **Add Files** — Select one or more CL2000 `.TXT` log files. If your session was split across multiple files, add them all and use **Move Up / Move Down** to ensure they are in chronological order.
2. **Remove Selected** — Remove a file from the list if added by mistake.
3. **Output File** — Type a path or click **Browse** to choose where to save the `.asc` file. The app will auto-suggest a path next to your first input file.
4. **Convert** — Click the Convert button. Progress is shown in the progress bar and log console.

---

## Input Format (CL2000 TXT)

```
# Logger type: CL2000
# Bit-rate: 500000
# Time: 20260422T140315
Timestamp;Type;ID;Data
22T140315133;0;201;10a87d00271000ff
22T140315134;0;4f1;810174ffff005959
...
```

- Timestamp format: `DDTHHMMSSmmm`
- ID and Data fields are hexadecimal
- Semicolon-delimited

---

## Output Format (Vector ASC)

```
date 20260422T140315
base hex  timestamps absolute
no internal events logged
Begin Triggerblock
   0.0000 1  201          Rx   d 8 10 a8 7d 00 27 10 00 ff
   0.0010 1  4F1          Rx   d 8 81 01 74 ff ff 00 59 59
...
End TriggerBlock
```

Compatible with **Vector CANalyzer**, **CANoe**, and any tool that accepts the standard `.asc` log format.

---

## Notes

- All frames are logged on **Channel 1**
- Timestamps are relative to the first message in the first file
- Extended CAN IDs (>0x7FF) are automatically suffixed with `x` per ASC spec
- The LF → CRLF warning from Git on Windows is harmless and can be ignored
