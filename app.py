"""8M Foto Karaoke — photos and videos, Windows and macOS."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageOps
from PySide6.QtCore import Qt, QUrl, QRect, Signal, QTimer
from PySide6.QtGui import QFont, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QSlider,
    QStackedWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QSizePolicy)

from core import Evening, SlideshowDeck, discover, is_video, key

STYLE = '''
QWidget { background: #111820; color: #f5f7f4; font-family: "Segoe UI", "Helvetica Neue", sans-serif; font-size: 14px; }
QPushButton { background: #24323c; border: 0; border-radius: 9px; padding: 11px 16px; font-weight: bold; }
QPushButton:hover { background: #47b8b7; color: #101820; }
QPushButton#primary { background: #47b8b7; color: #102027; font-size: 18px; padding: 17px; }
QLabel#headline { font-size: 36px; font-weight: bold; }
QLabel#sub { color: #b4c2c6; }
QLabel#section { color: #f6c958; font-weight: bold; }
QComboBox, QTreeWidget { background: #1d2931; border: 1px solid #38505b; border-radius: 6px; padding: 7px; }
QSlider::groove:horizontal { height: 6px; background: #38505b; }
QSlider::handle:horizontal { background: #47b8b7; width: 15px; margin: -5px 0; border-radius: 7px; }
'''


def state_path():
    if sys.platform == 'win32':
        base = Path(os.getenv('APPDATA') or Path.home() / 'AppData' / 'Roaming')
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path.home() / '.config'
    return base / '8M Foto Karaoke' / 'abend.json'


def button(text, callback, primary=False):
    b = QPushButton(text)
    if primary:
        b.setObjectName('primary')
    b.clicked.connect(callback)
    return b


class Sources(QDialog):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.roots = app.evening.roots[:]
        self.excluded = app.evening.excluded[:]
        self.setWindowTitle('Foto- und Videoquellen wählen · 8M')
        self.resize(760, 630)
        layout = QVBoxLayout(self)
        heading = QLabel('WO SOLLEN WIR STÖBERN?')
        heading.setObjectName('headline')
        layout.addWidget(heading)
        layout.addWidget(QLabel('Mehrere Ordner wählen. Doppelklick schließt einen Unterordner aus oder wieder ein.'))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Ausgewählte Ordner und Unterordner'])
        self.tree.itemDoubleClicked.connect(self.toggle)
        layout.addWidget(self.tree)
        row = QHBoxLayout()
        row.addWidget(button('＋ Ordner hinzufügen', self.add))
        row.addWidget(button('Quelle entfernen', self.remove))
        row.addStretch()
        row.addWidget(button('Auswahl übernehmen', self.apply, True))
        layout.addLayout(row)
        self.populate()

    def populate(self):
        self.tree.clear()
        blocked = {key(p) for p in self.excluded}

        def add_node(parent, path):
            name = path if parent is None else os.path.basename(path)
            item = QTreeWidgetItem([('☐ ' if key(path) in blocked else '☑ ') + name])
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            if parent is None:
                self.tree.addTopLevelItem(item)
                item.setExpanded(True)
            else:
                parent.addChild(item)
            if key(path) in blocked:
                return
            try:
                with os.scandir(path) as entries:
                    children = sorted((e.path for e in entries if e.is_dir(follow_symlinks=False)),
                                      key=str.casefold)
                for child in children:
                    add_node(item, child)
            except OSError:
                pass

        for root in self.roots:
            add_node(None, root)

    def add(self):
        path = QFileDialog.getExistingDirectory(self, 'Foto- und Videoordner wählen')
        if path and key(path) not in {key(p) for p in self.roots}:
            self.roots.append(path)
            self.populate()

    def remove(self):
        item = self.tree.currentItem()
        if not item:
            return
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if item.parent() is None:
            self.roots = [p for p in self.roots if key(p) != key(path)]
        elif key(path) not in {key(p) for p in self.excluded}:
            self.excluded.append(path)
        self.populate()

    def toggle(self, item, _column):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if key(path) in {key(p) for p in self.excluded}:
            self.excluded = [p for p in self.excluded if key(p) != key(path)]
        else:
            self.excluded.append(path)
        self.populate()

    def apply(self):
        self.app.evening.roots = self.roots
        self.app.evening.excluded = self.excluded
        self.app.evening.save()
        self.app.refresh()
        self.accept()


class ImageView(QLabel):
    clicked = Signal()
    selection = Signal(float, float, float, float)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet('background: black;')
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.start = None
        self.image_rect = QRect()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.start is None:
            return
        end = event.position().toPoint()
        start = self.start
        self.start = None
        if (end-start).manhattanLength() < 25:
            self.clicked.emit()
            return
        rect = self.image_rect
        if rect.width() <= 0 or rect.height() <= 0:
            return
        x1, x2 = sorted((start.x(), end.x()))
        y1, y2 = sorted((start.y(), end.y()))
        clip = lambda value: max(0., min(1., value))
        left, right = clip((x1-rect.left())/rect.width()), clip((x2-rect.left())/rect.width())
        top, bottom = clip((y1-rect.top())/rect.height()), clip((y2-rect.top())/rect.height())
        if right-left > .01 and bottom-top > .01:
            self.selection.emit(left, top, right, bottom)


class Stage(QWidget):
    def __init__(self, owner, screen):
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.owner = owner
        self.setWindowTitle('8M Foto Karaoke · Bühne')
        self.setStyleSheet(STYLE)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.screen = screen
        self.original = None
        self.zoom = None
        self.fill = False
        self.current = None
        self.is_video = False
        self.video_end_pending = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        self.image = ImageView()
        self.image.clicked.connect(owner.advance)
        self.image.selection.connect(self.select)
        self.stack.addWidget(self.image)
        self.video = QVideoWidget()
        self.video.setStyleSheet('background: black;')
        self.stack.addWidget(self.video)
        layout.addWidget(self.stack, 1)
        row = QHBoxLayout()
        row.setContentsMargins(12, 8, 12, 10)
        row.addWidget(button('← Zurück', owner.previous))
        row.addWidget(button('Nächstes →', owner.advance))
        row.addWidget(button('Überspringen', owner.skip))
        self.play_button = button('⏸ Pause', self.play_pause)
        row.addWidget(self.play_button)
        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.setRange(0, 0)
        self.seek.sliderMoved.connect(self.seek_to)
        row.addWidget(self.seek, 1)
        self.clock = QLabel('00:00 / 00:00')
        row.addWidget(self.clock)
        row.addWidget(QLabel('Ton'))
        volume = QSlider(Qt.Orientation.Horizontal)
        volume.setRange(0, 100)
        volume.setValue(75)
        volume.setFixedWidth(85)
        row.addWidget(volume)
        row.addWidget(button('Füllen', self.toggle_fill))
        row.addWidget(button('Ausschnitt zurück', self.reset_zoom))
        row.addWidget(button('✕', owner.close_stage))
        layout.addLayout(row)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(.75)
        volume.valueChanged.connect(lambda v: self.audio.setVolume(v/100))
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.errorOccurred.connect(self.video_error)
        self.player.mediaStatusChanged.connect(self.media_status)
        self.player.playbackStateChanged.connect(self.update_play)
        self.shortcuts = []
        for sequence, callback in [('Space', owner.advance), ('Right', owner.advance),
                                   ('Left', owner.previous), ('Backspace', owner.previous),
                                   ('S', owner.skip), ('C', self.toggle_fill),
                                   ('R', self.reset_zoom), ('P', self.play_pause),
                                   ('Escape', owner.close_stage)]:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        self.show()
        self.windowHandle().setScreen(screen)
        self.setGeometry(screen.geometry())
        self.showFullScreen()
        self.setFocus()
        if owner.mode == 'slideshow':
            row.itemAt(0).widget().setEnabled(False)  # no backtracking in the looping slideshow

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.render()

    def show_path(self, path):
        self.owner.photo_timer.stop()
        self.player.stop()
        self.player.setSource(QUrl())
        self.current = path
        self.is_video = is_video(path)
        self.video_end_pending = False
        self.zoom = None
        self.fill = False
        self.original = None
        if self.is_video:
            self.stack.setCurrentWidget(self.video)
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.play()
        else:
            with Image.open(path) as source:
                source.load()
                self.original = ImageOps.exif_transpose(source).convert('RGB')
            self.stack.setCurrentWidget(self.image)
            self.render()
        self.play_button.setEnabled(self.is_video)
        if self.owner.mode == 'slideshow':
            self.play_button.setEnabled(True)
            if not self.is_video:
                self.play_button.setText('⏸ Pause')
                self.owner.photo_timer.start(self.owner.interval_ms)
        self.seek.setEnabled(self.is_video)
        self.clock.setVisible(self.is_video)
        self.owner.update_summary()

    def render(self):
        if not self.original:
            return
        iw, ih = self.image.width(), self.image.height()
        if iw < 10 or ih < 10:
            return
        region = self.original.crop(self.zoom) if self.zoom else self.original
        scale = max(iw/region.width, ih/region.height) if self.fill else min(iw/region.width, ih/region.height)
        nw, nh = max(1, round(region.width*scale)), max(1, round(region.height*scale))
        # Qt crops the full-size bitmap in fill mode. Keep backing storage bounded.
        region.thumbnail((max(nw, iw), max(nh, ih)), Image.Resampling.LANCZOS)
        data = region.tobytes()
        qimage = QImage(data, region.width, region.height, region.width*3, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage.copy()).scaled(nw, nh, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                         Qt.TransformationMode.SmoothTransformation)
        self.image.setPixmap(pixmap)
        self.image.image_rect = QRect((iw-nw)//2, (ih-nh)//2, nw, nh)

    def select(self, l, t, r, b):
        base = self.zoom or (0, 0, self.original.width, self.original.height)
        bw, bh = base[2]-base[0], base[3]-base[1]
        self.zoom = (base[0]+round(l*bw), base[1]+round(t*bh),
                     base[0]+round(r*bw), base[1]+round(b*bh))
        self.fill = False
        self.render()

    def toggle_fill(self):
        if self.is_video:
            mode = (Qt.AspectRatioMode.KeepAspectRatioByExpanding if not self.fill
                    else Qt.AspectRatioMode.KeepAspectRatio)
            self.video.setAspectRatioMode(mode)
        self.fill = not self.fill
        self.render()

    def reset_zoom(self):
        self.zoom = None
        self.fill = False
        self.video.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.render()

    def play_pause(self):
        if self.owner.mode == 'slideshow':
            self.owner.slideshow_paused = not self.owner.slideshow_paused
            if not self.is_video:
                if self.owner.slideshow_paused:
                    self.owner.photo_timer.stop()
                else:
                    self.owner.photo_timer.start(self.owner.interval_ms)
                self.play_button.setText('▶ Weiter' if self.owner.slideshow_paused else '⏸ Pause')
                return
            if self.owner.slideshow_paused:
                self.player.pause()
                return
            if self.player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
                self.player.setPosition(0)
            self.player.play()
            return
        if not self.is_video:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
                self.player.setPosition(0)
            self.player.play()

    def seek_to(self, pos):
        self.player.setPosition(pos)

    def update_duration(self, duration):
        self.seek.setRange(0, max(0, duration))
        self.update_position(self.player.position())

    def update_position(self, position):
        if not self.seek.isSliderDown():
            self.seek.setValue(position)
        def stamp(ms):
            sec = max(0, ms//1000)
            return f'{sec//60:02}:{sec%60:02}'
        self.clock.setText(f'{stamp(position)} / {stamp(self.player.duration())}')

    def update_play(self, state):
        self.play_button.setText('⏸ Pause' if state == QMediaPlayer.PlaybackState.PlayingState else '▶ Weiter')

    def media_status(self, status):
        if (self.owner.mode == 'slideshow' and self.is_video and self.current
                and status == QMediaPlayer.MediaStatus.EndOfMedia and not self.video_end_pending):
            self.video_end_pending = True
            current = self.current
            QTimer.singleShot(250, lambda: self.owner.advance()
                if self.owner.stage is self and self.current == current
                and not self.owner.slideshow_paused else None)

    def video_error(self, _error, message):
        if self.is_video and self.current:
            if self.owner.mode == 'slideshow':
                self.owner.slideshow_bad.add(key(self.current))
                current = self.current
                QTimer.singleShot(250, lambda: self.owner.advance()
                    if self.owner.stage is self and self.current == current else None)
                return
            QMessageBox.warning(self, 'Video nicht abspielbar',
                f'Diese Videodatei konnte nicht abgespielt werden:\n{self.current}\n\n{message}\n\nMit „Nächstes“ fortfahren.')


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('8M Foto Karaoke')
        self.resize(980, 640)
        self.evening = Evening(state_path())
        self.files = []
        self.errors = []
        self.stage = None
        self.mode = None
        self.deck = None
        self.slideshow_bad = set()
        self.slideshow_paused = False
        self.photo_timer = QTimer(self)
        self.photo_timer.setSingleShot(True)
        self.photo_timer.timeout.connect(self.advance)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(34, 24, 34, 24)
        brand = QLabel('🟥 🟨 🟩 🟦    8M FOTO KARAOKE')
        brand.setObjectName('headline')
        layout.addWidget(brand)
        sub = QLabel('Eine Schule für viele Talente. Und sehr viele Fotos und Videos.')
        sub.setObjectName('sub')
        layout.addWidget(sub)
        stripe = QLabel('')
        stripe.setFixedHeight(4)
        stripe.setStyleSheet('background: #f6c958;')
        layout.addWidget(stripe)
        layout.addSpacing(32)
        section = QLabel('DIE BÜHNE GEHÖRT DIR')
        section.setObjectName('section')
        layout.addWidget(section)
        layout.addWidget(QLabel('Stichwort vorlesen. Zufälliges Medium aufdecken. Irgendwie überzeugend bleiben.'))
        layout.addSpacing(22)
        self.counter = QLabel('')
        self.counter.setFont(QFont('', 17, QFont.Weight.Bold))
        layout.addWidget(self.counter)
        self.details = QLabel('')
        self.details.setWordWrap(True)
        self.details.setObjectName('sub')
        layout.addWidget(self.details)
        layout.addSpacing(22)
        row = QHBoxLayout()
        row.addWidget(button('Quellen wählen', self.sources))
        row.addWidget(button('Quellen neu einlesen', self.refresh))
        row.addWidget(button('Neuen Abend beginnen', self.reset))
        row.addStretch()
        layout.addLayout(row)
        layout.addSpacing(20)
        screen_row = QHBoxLayout()
        screen_row.addWidget(QLabel('Präsentation auf:'))
        self.screens = QComboBox()
        for i, screen in enumerate(QApplication.screens()):
            s = screen.geometry()
            self.screens.addItem(f'Bildschirm {i+1} ({s.width()} × {s.height()})', screen)
        self.screens.setCurrentIndex(min(1, self.screens.count()-1))
        screen_row.addWidget(self.screens)
        screen_row.addStretch()
        layout.addLayout(screen_row)
        start_row = QHBoxLayout()
        start_row.addWidget(button('▶  KARAOKE STARTEN', self.open_stage, True))
        start_row.addWidget(button('♫  DIASHOW STARTEN', self.open_slideshow, True))
        start_row.addStretch()
        layout.addLayout(start_row)
        duration_row = QHBoxLayout()
        duration_row.addWidget(QLabel('Fotos in der Diashow wechseln nach:'))
        self.interval = QComboBox()
        for seconds in (5, 8, 12, 20, 30):
            self.interval.addItem(f'{seconds} Sekunden', seconds * 1000)
        self.interval.setCurrentIndex(2)
        duration_row.addWidget(self.interval)
        duration_row.addStretch()
        layout.addLayout(duration_row)
        layout.addStretch()
        footer = QLabel('KLICK / LEERTASTE / →  nächstes Medium     ←  zurück (Karaoke)     S  überspringen     P  Pause     C  füllen     R  Ausschnitt zurück     ESC  Bühne schließen')
        footer.setObjectName('sub')
        footer.setWordWrap(True)
        layout.addWidget(footer)
        self.refresh()

    def sources(self):
        Sources(self).exec()

    def refresh(self):
        self.files, self.errors = discover(self.evening.roots, self.evening.excluded)
        self.evening.set_files(self.files)
        self.update_summary()

    def update_summary(self):
        photos = sum(not is_video(p) for p in self.files)
        videos = len(self.files)-photos
        self.counter.setText(f'{photos} Fotos  ·  {videos} Videos  ·  {self.evening.remaining_count} noch ungesehen')
        info = f'{len(self.evening.roots)} Quellordner · {len(self.evening.excluded)} ausgeschlossene Unterordner · {len(self.evening.history)} gezogen'
        if self.errors:
            info += '\n⚠ ' + '; '.join(self.errors[:2])
        self.details.setText(info)

    def open_stage(self):
        self.refresh()
        if not self.files:
            QMessageBox.information(self, 'Noch keine Medien', 'Bitte zuerst Foto- und Videoquellen wählen.')
            return
        if self.stage:
            self.close_stage()
        self.mode = 'karaoke'
        self.stage = Stage(self, self.screens.currentData())
        if self.evening.history:
            path = self.evening.history[-1]
            if os.path.isfile(path):
                try:
                    self.stage.show_path(path)
                except (OSError, ValueError):
                    pass

    @property
    def interval_ms(self):
        return self.interval.currentData()

    def open_slideshow(self):
        self.refresh()
        if not self.files:
            QMessageBox.information(self, 'Noch keine Medien', 'Bitte zuerst Foto- und Videoquellen wählen.')
            return
        if self.stage:
            self.close_stage()
        self.mode = 'slideshow'
        self.deck = SlideshowDeck(self.files)
        self.slideshow_bad = set()
        self.slideshow_paused = False
        self.stage = Stage(self, self.screens.currentData())
        self.slideshow_next()

    def slideshow_next(self):
        if not self.stage or self.mode != 'slideshow':
            return
        self.photo_timer.stop()
        def valid(path):
            if key(path) in self.slideshow_bad:
                raise OSError('Dieses Video konnte nicht dekodiert werden')
            self.validate(path)
        for _ in range(len(self.files)):
            path, _invalid = self.deck.next(valid)
            if not path:
                break
            try:
                self.stage.show_path(path)
                return
            except (OSError, ValueError):
                self.slideshow_bad.add(key(path))
        QMessageBox.warning(self.stage, 'Keine Medien abspielbar',
                            'Die ausgewählten Dateien sind nicht mehr erreichbar oder lesbar. Bitte Quellen prüfen.')
        self.close_stage()

    def validate(self, path):
        if is_video(path):
            with open(path, 'rb') as video:
                if not video.read(1):
                    raise OSError('Leere Datei')
        else:
            with Image.open(path) as image:
                image.load()

    def new_random(self):
        path, invalid = self.evening.pick(self.files, self.validate)
        if path:
            try:
                self.stage.show_path(path)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self.stage, 'Medium nicht lesbar', f'{path}\n{exc}')
                self.new_random()
            return
        self.update_summary()
        if invalid or self.errors:
            QMessageBox.warning(self.stage, 'Medien nicht erreichbar',
                'Keine weiteren lesbaren Medien erreichbar. Bitte Quellen prüfen und neu einlesen.\n' +
                '\n'.join((invalid or self.errors)[:3]))
            self.sources()
        elif QMessageBox.question(self.stage, 'Alle Medien gezeigt',
                'Alle ausgewählten Medien wurden gezeigt. Mit denselben Quellen neu beginnen?\n'
                '„Nein“ öffnet die Quellenauswahl.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.evening.reset()
            self.refresh()
            self.new_random()
        else:
            self.sources()

    def advance(self):
        if not self.stage:
            return
        if self.mode == 'slideshow':
            self.slideshow_paused = False
            self.slideshow_next()
            return
        while self.evening.cursor < len(self.evening.history)-1:
            self.evening.cursor += 1
            try:
                self.stage.show_path(self.evening.history[self.evening.cursor])
                return
            except (OSError, ValueError):
                pass
        self.new_random()

    def skip(self):
        if self.stage:
            if self.mode == 'slideshow':
                self.advance()
                return
            self.new_random()

    def previous(self):
        if not self.stage or self.mode == 'slideshow':
            return
        while self.evening.cursor > 0:
            self.evening.cursor -= 1
            try:
                self.stage.show_path(self.evening.history[self.evening.cursor])
                return
            except (OSError, ValueError):
                pass

    def reset(self):
        if QMessageBox.question(self, 'Neuen Abend beginnen',
                'Den bisherigen Ziehungsstand löschen und alle Medien erneut freigeben?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.evening.reset()
            self.refresh()
            if self.stage:
                self.stage.player.stop()
                self.stage.original = None
                self.stage.image.clear()

    def close_stage(self):
        if self.stage:
            self.photo_timer.stop()
            self.stage.player.stop()
            self.stage.close()
            self.stage = None
            self.mode = None
            self.deck = None

    def closeEvent(self, event):
        self.close_stage()
        super().closeEvent(event)


if __name__ == '__main__':
    application = QApplication(sys.argv)
    application.setStyleSheet(STYLE)
    window = App()
    window.show()
    sys.exit(application.exec())
