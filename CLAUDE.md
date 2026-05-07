# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository context

This directory is a Windows-oriented red-team/CTF scanning workspace, not a conventional application repository. It contains Windows executables, batch launchers, target/input dictionaries, tool configuration, and Python scripts that parse and format scan output.

There is no git repository, package manifest, README, test suite, or build system in this directory. Treat existing `.exe`, `.db`, `.txt`, `.json`, and generated report files as challenge/tool artifacts unless the user explicitly asks to modify them.

## Runtime assumptions

- Primary workflow targets Windows `cmd.exe`; several scripts call `start cmd /c`, run `.exe` files, and use `.bat` launchers.
- Python scripts expect Python 3 plus these packages: `pandas`, `openpyxl`, and for `1.py`, `psutil`.
- `1.py` optionally imports `win32gui`/`win32con` to hide the console on Windows; absence only logs a warning.
- Tool binaries are expected in the repository root: `ts.exe`, `spray.exe`, and `ehole.exe`.
- Key input files are root-relative: `ip.txt`, `url.txt`, `port.txt`, `ports.txt`, `dirv2.txt`, `dirv3.txt`, `finger.json`, `config.yaml`.

## Common commands

Install Python dependencies:

```bash
python -m pip install pandas openpyxl psutil pywin32
```

Syntax-check all Python scripts without executing scans:

```bash
python -m py_compile 1.py 2.py ppp.py process_data.py
```

Run the top-100 Windows workflow from `cmd.exe`:

```bat
轮子top100.bat
```

Run the top-1000 Windows workflow from `cmd.exe`:

```bat
轮子top1000.bat
```

Run only the port/URL scan parser flow:

```bash
python 2.py
python ppp.py
```

Run only the spray-to-ehole pipeline after `url.txt` exists:

```bash
python 1.py
```

Convert a spray JSON-lines result to Excel and extracted URL text:

```bash
python process_data.py res.json res_processed.xlsx
```

Beautify an ehole Excel result in place:

```bash
python process_data.py ehole_result.xlsx ehole_result.xlsx
```

Run representative `ts.exe` scans manually:

```bat
ts -hf ip.txt -portf ports.txt -np -m port,url,js
ts -hf ip.txt -portf ports.txt -np -m port,url
ts -hf ip.txt -np -m port,url,js
ts -hf ip.txt -np -m port,url
```

## High-level workflow

1. `2.py` runs `ts -hf ip.txt -pa 3389 -np -m port,url`, parses `url.txt`, generates a styled `url_details_*.xlsx`, and rewrites extracted URLs back to `url.txt`.
2. `ppp.py` parses `port.txt` into a styled `port_scan_report_*.xlsx`. It supports raw open-port lines, fingerprint lines, empty-fingerprint lines, and URL result lines.
3. `1.py` orchestrates the main pipeline:
   - cleans prior transient outputs such as `url.txt.stat` and `res_processed.txt`;
   - runs `spray.exe -l url.txt -d dirv2.txt -f res.json`;
   - calls `process_data.py` to convert spray JSON-lines output to Excel and extracted URL text;
   - filters status-code-200 URLs from the processed Excel;
   - moves spray artifacts into a date folder named `MMDD`;
   - runs `ehole finger -l <filtered_urls> -o <ehole_output.xlsx> -t 10`;
   - calls `process_data.py` again to beautify the ehole Excel report.
4. Batch files compose these steps. `轮子top100.bat` runs `2.py`, `ppp.py`, clears old spray outputs, then starts `1.py`. `轮子top1000.bat` is similar but invokes `2.txt` as a Python script.

## Important files and data flow

- `ip.txt`: host input for `ts.exe`.
- `ports.txt`: custom port list for manual `ts.exe -portf` runs.
- `url.txt`: intermediate and input URL list; overwritten by `2.py`.
- `port.txt`: input parsed by `ppp.py`; normally produced by scanning tools.
- `res.json`: spray JSON-lines output consumed by `process_data.py`.
- `res_processed.xlsx` / `res_processed.txt`: processed spray outputs; often deleted and regenerated.
- `MMDD/`: generated date folders where `1.py` stores spray and ehole reports.
- `config.yaml`, `config.db`, `finger.json`: ehole/tool configuration and fingerprint database artifacts.

## Editing guidance

- Preserve Windows compatibility when changing scripts: root-relative file paths, `.bat` entrypoints, `cmd.exe` behavior, and Chinese filenames are part of the current workflow.
- Avoid replacing `.bat` workflows with POSIX-only commands unless the user asks; the operational target is Windows even if Claude runs from Linux.
- Be careful with generated scan outputs. Do not delete or overwrite result files unless the requested change requires it.
- Prefer validating parser changes with `python -m py_compile ...` and small copied/sample input files rather than launching scanners unintentionally.
