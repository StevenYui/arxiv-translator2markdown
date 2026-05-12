#!/usr/bin/env python3
"""
Render/copy figures referenced by LaTeX sources for Markdown output.

Usage:
  python render_figures.py <work_dir> <main_tex> <asset_dir>

Figures are emitted as fig01.png, fig02.png, ... in the order their active
\\includegraphics commands appear after expanding \\input/\\include files.
PDF figures are rendered with pdftoppm using PNG, 300 DPI, and CropBox.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass


INPUT_RE = re.compile(r"\\(?:input|include|subfile)\{([^}]+)\}")
GRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
COMMENT_RE = re.compile(r"(?<!\\)%.*$")
SUPPORTED_COPY_EXTS = {".png", ".jpg", ".jpeg"}
VECTOR_EXTS = {".pdf", ".eps", ".svg"}


@dataclass(frozen=True)
class FigureRef:
    tex_file: str
    source: str


def strip_comment(line: str) -> str:
    return COMMENT_RE.sub("", line)


def resolve_tex_path(base_dir: str, raw: str) -> str | None:
    raw = raw.strip()
    if not raw:
        return None
    candidates = [raw]
    if not raw.lower().endswith(".tex"):
        candidates.append(raw + ".tex")
    for cand in candidates:
        path = os.path.normpath(os.path.join(base_dir, cand))
        if os.path.isfile(path):
            return path
    return None


def resolve_graphic_path(base_dir: str, work_dir: str, raw: str) -> str | None:
    raw = raw.strip()
    candidates = [raw]
    root, ext = os.path.splitext(raw)
    if not ext:
        candidates.extend(raw + suffix for suffix in (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg"))
    search_dirs = [base_dir, work_dir]
    for root_dir in search_dirs:
        for cand in candidates:
            path = os.path.normpath(os.path.join(root_dir, cand))
            if os.path.isfile(path):
                return path
    return None


def collect_figures(tex_path: str, work_dir: str, seen: set[str] | None = None) -> list[FigureRef]:
    tex_path = os.path.abspath(tex_path)
    if seen is None:
        seen = set()
    if tex_path in seen:
        return []
    seen.add(tex_path)

    base_dir = os.path.dirname(tex_path)
    refs: list[FigureRef] = []
    try:
        lines = open(tex_path, "r", encoding="utf-8", errors="replace").readlines()
    except OSError:
        return refs

    for line in lines:
        clean = strip_comment(line)
        for match in GRAPHICS_RE.finditer(clean):
            graphic = resolve_graphic_path(base_dir, work_dir, match.group(1))
            if graphic:
                refs.append(FigureRef(tex_file=tex_path, source=graphic))
        for match in INPUT_RE.finditer(clean):
            child = resolve_tex_path(base_dir, match.group(1))
            if child:
                refs.extend(collect_figures(child, work_dir, seen))
    return refs


def copy_raster(src: str, dest_no_ext: str) -> str:
    ext = os.path.splitext(src)[1].lower()
    dest_ext = ".jpg" if ext == ".jpeg" else ext
    dest = dest_no_ext + dest_ext
    shutil.copy2(src, dest)
    return dest


def render_pdf(src: str, dest_no_ext: str) -> str:
    cmd = ["pdftoppm", "-png", "-r", "300", "-cropbox", "-singlefile", src, dest_no_ext]
    subprocess.run(cmd, check=True)
    return dest_no_ext + ".png"


def render_figures(work_dir: str, main_tex: str, asset_dir: str) -> int:
    work_dir = os.path.abspath(work_dir)
    main_path = main_tex if os.path.isabs(main_tex) else os.path.join(work_dir, main_tex)
    main_path = os.path.abspath(main_path)
    if not main_path.startswith(work_dir + os.sep) and main_path != work_dir:
        raise SystemExit(f"main_tex must be inside work_dir: {main_path}")

    refs = collect_figures(main_path, work_dir)
    os.makedirs(asset_dir, exist_ok=True)
    print(f"FIGURE_COUNT={len(refs)}")

    emitted = 0
    for ref in refs:
        emitted += 1
        dest_no_ext = os.path.abspath(os.path.join(asset_dir, f"fig{emitted:02d}"))
        ext = os.path.splitext(ref.source)[1].lower()
        rel_src = os.path.relpath(ref.source, work_dir)
        try:
            if ext in SUPPORTED_COPY_EXTS:
                out = copy_raster(ref.source, dest_no_ext)
            elif ext == ".pdf":
                out = render_pdf(ref.source, dest_no_ext)
            elif ext in VECTOR_EXTS:
                print(f"WARNING=unsupported vector format for automatic render:{rel_src}", file=sys.stderr)
                continue
            else:
                print(f"WARNING=unsupported image format:{rel_src}", file=sys.stderr)
                continue
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"WARNING=failed to render:{rel_src}:{exc}", file=sys.stderr)
            continue
        print(f"FIGURE={emitted}:{os.path.basename(out)}:{rel_src}")

    return emitted


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("work_dir")
    parser.add_argument("main_tex")
    parser.add_argument("asset_dir")
    args = parser.parse_args(argv)
    render_figures(args.work_dir, args.main_tex, args.asset_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
