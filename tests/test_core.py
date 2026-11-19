import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import Evening, SlideshowDeck, discover, is_video


class CoreTests(unittest.TestCase):
    def test_exclusions_overlap_restart_and_exhaustion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sub = root / 'exclude'
            sub.mkdir()
            (root / 'a.JPG').write_bytes(b'a')
            (root / 'b.png').write_bytes(b'b')
            (sub / 'c.jpg').write_bytes(b'c')
            paths, errors = discover([str(root), str(sub)], [str(sub)])
            self.assertFalse(errors)
            self.assertEqual(len(paths), 2)
            state = Evening(root / 'state' / 'abend.json')
            for _ in range(2):
                self.assertIsNotNone(state.pick(paths, lambda _: None)[0])
            self.assertIsNone(state.pick(paths, lambda _: None)[0])
            resumed = Evening(state.path)
            self.assertEqual(len(resumed.history), 2)
            self.assertEqual(resumed.remaining(paths), [])
            resumed.reset()
            self.assertEqual(len(resumed.remaining(paths)), 2)

    def test_unreadable_does_not_consume(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Evening(Path(tmp) / 'evening.json')
            file = str(Path(tmp) / 'bad.jpg')
            path, errors = state.pick([file], lambda _: (_ for _ in ()).throw(OSError('bad')))
            self.assertIsNone(path)
            self.assertEqual(len(errors), 1)
            self.assertEqual(state.history, [])

    def test_mixed_media_once_and_video_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('photo.JPG', 'clip.MP4', 'old.AVI', 'movie.MOV'):
                (root / name).write_bytes(b'x')
            files, errors = discover([str(root)], [])
            self.assertFalse(errors)
            self.assertEqual(len(files), 4)
            self.assertEqual(sum(is_video(p) for p in files), 3)
            evening = Evening(root / 'abend.json')
            evening.set_files(files)
            drawn = [evening.pick(None, lambda _: None)[0] for _ in range(4)]
            self.assertEqual(set(drawn), set(files))
            self.assertIsNone(evening.pick(None, lambda _: None)[0])

    def test_slideshow_loops_without_changing_karaoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Evening(Path(tmp) / 'abend.json')
            files = [str(Path(tmp) / f'{n}.jpg') for n in range(5)]
            state.set_files(files)
            first, _ = state.pick(None, lambda _: None)
            deck = SlideshowDeck(files)
            first_round = [deck.next(lambda _: None)[0] for _ in files]
            self.assertEqual(set(first_round), set(files))
            next_round = [deck.next(lambda _: None)[0] for _ in files]
            self.assertEqual(set(next_round), set(files))
            self.assertNotEqual(first_round[-1], next_round[0])
            self.assertEqual(state.history, [first])
            self.assertEqual(state.remaining_count, 4)

    def test_slideshow_unavailable_files_do_not_loop_forever(self):
        deck = SlideshowDeck(['bad.mp4', 'broken.jpg'])
        path, errors = deck.next(lambda _: (_ for _ in ()).throw(OSError('missing')))
        self.assertIsNone(path)
        self.assertEqual(len(errors), 2)

    def test_rescan_adds_new_photos_without_repeating_old_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Evening(Path(tmp) / 'abend.json')
            originals = [str(Path(tmp) / f'{n}.jpg') for n in range(3)]
            state.set_files(originals)
            first, _ = state.pick(None, lambda _: None)
            self.assertEqual(state.remaining_count, 2)
            added = str(Path(tmp) / 'new.jpg')
            state.set_files(originals + [added])
            picked = [first]
            for _ in range(3):
                photo, _ = state.pick(None, lambda _: None)
                picked.append(photo)
            self.assertEqual(set(picked), set(originals + [added]))
            self.assertEqual(state.remaining_count, 0)
            resumed = Evening(state.path)
            resumed.set_files(originals + [added])
            self.assertEqual(resumed.remaining_count, 0)

    def test_save_failure_does_not_consume_photo(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Evening(Path(tmp) / 'abend.json')
            state.set_files([str(Path(tmp) / 'photo.jpg')])
            with patch.object(state, 'save', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    state.pick(None, lambda _: None)
            self.assertEqual(state.remaining_count, 1)
            self.assertEqual(state.history, [])


if __name__ == '__main__':
    unittest.main()
