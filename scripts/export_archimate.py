#!/usr/bin/env python3
"""
Simple automation to export ArchiMate diagram XML files to PNG.

Behavior:
- Scans a source folder (default: ./model and ./model/diagrams) for .archimate or .xml diagram files.
- If a config file provides an `archi_command_template`, the script will run that command (formatting {input} and {output}).
- Otherwise the script creates a placeholder PNG for each diagram using Pillow, so you get automated outputs even without Archi installed.

Configure a command template in tools/archi_export/config.json, e.g.:
  "archi_command_template": "C:\\Program Files\\Archi\\Archi.exe -nosplash -application com.archimatetool.commandline -model \"{input}\" -export \"{output}\""

This script requires `Pillow` for placeholder PNG generation. See requirements.txt.
"""
import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None


def find_diagram_files(src: Path):
    files = []
    if not src.exists():
        return files
    # search for .archimate files and xml files under diagrams
    for p in src.rglob('*.archimate'):
        files.append(p)
    for p in (src / 'diagrams').rglob('*.xml') if (src / 'diagrams').exists() else []:
        files.append(p)
    return sorted(set(files))


def load_config(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def make_placeholder_png(text: str, out_path: Path, size=(1200, 900)):
    if Image is None:
        raise RuntimeError('Pillow not installed. Install via `pip install -r requirements.txt`.')
    img = Image.new('RGB', size, color=(245, 245, 245))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('arial.ttf', 20)
    except Exception:
        font = ImageFont.load_default()
    margin = 20
    lines = []
    for chunk in text.splitlines():
        lines.append(chunk)
    y = margin
    for line in lines:
        draw.text((margin, y), line, fill=(40, 40, 40), font=font)
        y += font.getsize(line)[1] + 6
    draw.text((margin, size[1] - 40), f'Generated: {datetime.utcnow().isoformat()}Z', fill=(120, 120, 120), font=font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, 'PNG')


def run_archi_command(template: str, input_file: Path, output_file: Path, dry_run=False):
    cmd = template.format(input=str(input_file), output=str(output_file))
    print('Running:', cmd)
    if dry_run:
        return 0
    try:
        completed = subprocess.run(cmd, shell=True, check=False)
        return completed.returncode
    except Exception as e:
        print('Failed to run Archi command:', e)
        return 2


def main():
    ap = argparse.ArgumentParser(description='Export ArchiMate diagram XML to PNG (automated).')
    ap.add_argument('--source', '-s', default='model', help='Source folder to search for diagrams (default: model)')
    ap.add_argument('--outdir', '-o', default='exported_diagrams', help='Output directory for PNGs')
    ap.add_argument('--config', '-c', default='tools/archi_export/config.json', help='Config JSON path')
    ap.add_argument('--dry-run', action='store_true', help='Print commands but do not execute')
    args = ap.parse_args()

    src = Path(args.source)
    outdir = Path(args.outdir)
    cfg = load_config(Path(args.config))

    files = find_diagram_files(src)
    if not files:
        print('No .archimate or diagram XML files found under', src)
        return

    template = cfg.get('archi_command_template')
    for f in files:
        rel = f.relative_to(src) if f.is_relative_to(src) else f.name
        out_name = f.stem + '.png'
        out_path = outdir / rel.parent / out_name if isinstance(rel, Path) else outdir / out_name

        out_path = out_path.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if template:
            rc = run_archi_command(template, f.resolve(), out_path, dry_run=args.dry_run)
            if rc != 0:
                print(f'Archi command returned {rc} for {f}, creating placeholder instead.')
                try:
                    make_placeholder_png(f'Placeholder for {f.name}\n(Archi command failed)', out_path)
                except Exception as e:
                    print('Failed to write placeholder PNG:', e)
        else:
            try:
                txt = f'Placeholder for {f.name}\n\nTo render a real PNG, configure `archi_command_template` in tools/archi_export/config.json.'
                make_placeholder_png(txt, out_path)
                print('Created placeholder PNG:', out_path)
            except Exception as e:
                print('Failed to create placeholder PNG for', f, '-', e)


if __name__ == '__main__':
    main()
