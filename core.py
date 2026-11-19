"""Selection and crash-safe evening state; no GUI dependencies."""
from __future__ import annotations

import json
import os
import secrets
import tempfile
from pathlib import Path

PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.jfif', '.png', '.bmp', '.dib', '.gif',
                    '.tif', '.tiff', '.webp', '.ico', '.pcx', '.tga', '.ppm', '.pgm', '.pbm'}
VIDEO_EXTENSIONS = {'.mp4', '.m4v', '.mov', '.avi', '.mkv', '.wmv', '.mpg',
                    '.mpeg', '.3gp', '.webm', '.mts', '.m2ts', '.flv', '.vob'}
EXTENSIONS = PHOTO_EXTENSIONS | VIDEO_EXTENSIONS


def is_video(path: str) -> bool:
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


def key(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def discover(roots: list[str], excluded: list[str]) -> tuple[list[str], list[str]]:
    """Enumerate selected trees, avoiding junction loops and overlapping roots."""
    blocked = {key(p) for p in excluded}
    found: dict[str, str] = {}
    errors: list[str] = []

    def onerror(error):
        errors.append(str(error))

    for root in roots:
        if not os.path.isdir(root):
            errors.append(f'Quelle nicht erreichbar: {root}')
            continue
        for base, dirs, files in os.walk(root, topdown=True, followlinks=False, onerror=onerror):
            dirs[:] = [d for d in dirs if key(os.path.join(base, d)) not in blocked
                      and not os.path.islink(os.path.join(base, d))]
            if key(base) in blocked:
                dirs[:] = []
                continue
            for name in files:
                path = os.path.join(base, name)
                if Path(name).suffix.lower() in EXTENSIONS and os.path.isfile(path):
                    found.setdefault(key(path), path)
    return list(found.values()), errors


class Evening:
    def __init__(self, path: Path):
        self.path = path
        self.roots: list[str] = []
        self.excluded: list[str] = []
        self.history: list[str] = []
        self.cursor = -1
        self._pool: list[str] = []
        self._files: list[str] = []
        if path.exists():
            data = json.loads(path.read_text(encoding='utf-8'))
            self.roots = data.get('roots', [])
            self.excluded = data.get('excluded', [])
            self.history = data.get('history', [])
            self.cursor = len(self.history) - 1  # resume at the last drawn photo

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = dict(roots=self.roots, excluded=self.excluded, history=self.history)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix='.8m-', suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as output:
                json.dump(data, output, ensure_ascii=False)
                output.flush()
                os.fsync(output.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def set_files(self, files: list[str]):
        """Rebuild once after a source scan, never after each photo."""
        self._files = files
        drawn = {key(p) for p in self.history}
        self._pool = [p for p in files if key(p) not in drawn]

    def remaining(self, files: list[str] | None = None) -> list[str]:
        if files is not None and files is not self._files:
            self.set_files(files)
        return self._pool[:]

    @property
    def remaining_count(self) -> int:
        return len(self._pool)

    def pick(self, files: list[str] | None, loadable) -> tuple[str | None, list[str]]:
        """Validate file before consuming; persist each draw before showing it."""
        if files is not None and files is not self._files:
            self.set_files(files)
        invalid = []
        while self._pool:
            index = secrets.randbelow(len(self._pool))
            path = self._pool[index]
            self._pool[index] = self._pool[-1]
            self._pool.pop()
            try:
                loadable(path)
            except (OSError, ValueError) as error:
                invalid.append(f'{path}: {error}')
                continue
            self.history.append(path)
            self.cursor = len(self.history) - 1
            try:
                self.save()
            except OSError:
                self.history.pop()
                self.cursor = len(self.history) - 1
                self._pool.append(path)
                raise
            return path, invalid
        return None, invalid

    def reset(self):
        old_history, old_cursor = self.history, self.cursor
        self.history = []
        self.cursor = -1
        try:
            self.save()
        except OSError:
            self.history, self.cursor = old_history, old_cursor
            raise
        self.set_files(self._files)


class SlideshowDeck:
    """A separate, shuffled loop; never changes the Karaoke evening history."""

    def __init__(self, files: list[str]):
        self.files = files[:]
        self.pool: list[str] = []
        self.last: str | None = None

    def next(self, loadable) -> tuple[str | None, list[str]]:
        invalid = []
        attempts = len(self.files)
        while attempts:
            if not self.pool:
                self.pool = self.files[:]
                secrets.SystemRandom().shuffle(self.pool)
                if len(self.pool) > 1 and key(self.pool[-1]) == key(self.last or ''):
                    self.pool[0], self.pool[-1] = self.pool[-1], self.pool[0]
            path = self.pool.pop()
            attempts -= 1
            try:
                loadable(path)
            except (OSError, ValueError) as error:
                invalid.append(f'{path}: {error}')
                continue
            self.last = path
            return path, invalid
        return None, invalid
