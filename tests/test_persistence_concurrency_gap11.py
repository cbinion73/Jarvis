"""
GAP-11: Concurrency tests for jarvis/persistence.py.

Tests verify:
- concurrent append_jsonl writers produce no duplicate or missing lines
- concurrent atomic_write_json writers converge to valid JSON (last writer wins)
- concurrent atomic_write_jsonl writers converge to valid JSONL
- read during concurrent writes returns valid JSON (never a corrupt partial read)
- no data loss when N threads all append to the same file
- recovery: if a .tmp file is left behind (simulated crash), next write succeeds
- lock file is created alongside the target file
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

from jarvis.persistence import append_jsonl, atomic_write_json, atomic_write_jsonl


class TestAppendJsonlConcurrency(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)

    def test_concurrent_appenders_no_data_loss(self):
        """N threads each appending M records — all N*M records present, all valid JSON."""
        path = self.root / "concurrent.jsonl"
        N_THREADS = 8
        M_RECORDS = 50
        errors = []

        def worker(thread_id):
            for i in range(M_RECORDS):
                try:
                    append_jsonl(path, {"thread": thread_id, "seq": i})
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(N_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertFalse(errors, f"Errors during concurrent append: {errors}")
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        self.assertEqual(len(lines), N_THREADS * M_RECORDS)
        for line in lines:
            parsed = json.loads(line)
            self.assertIn("thread", parsed)
            self.assertIn("seq", parsed)

    def test_all_values_present(self):
        """Every (thread, seq) pair is written exactly once."""
        path = self.root / "all_values.jsonl"
        N = 5
        M = 20
        errors = []

        def worker(tid):
            for i in range(M):
                try:
                    append_jsonl(path, {"t": tid, "s": i})
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertFalse(errors)
        records = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        pairs = {(r["t"], r["s"]) for r in records}
        expected = {(t, s) for t in range(N) for s in range(M)}
        self.assertEqual(pairs, expected)

    def test_no_corrupt_partial_lines(self):
        """Each line must be a complete, parseable JSON object."""
        path = self.root / "no_corrupt.jsonl"
        errors = []

        def worker(tid):
            for i in range(30):
                try:
                    append_jsonl(path, {"tid": tid, "i": i, "padding": "x" * 100})
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertFalse(errors)
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            json.loads(line)  # raises on corruption


class TestAtomicWriteJsonConcurrency(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)

    def test_concurrent_writers_always_valid_json(self):
        """After N concurrent writes, the file must contain valid JSON."""
        path = self.root / "state.json"
        N = 10
        errors = []

        def worker(tid):
            for i in range(20):
                try:
                    atomic_write_json(path, {"writer": tid, "seq": i, "data": list(range(20))})
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertFalse(errors)
        content = path.read_text().strip()
        parsed = json.loads(content)
        self.assertIn("writer", parsed)
        self.assertIn("seq", parsed)

    def test_no_tmp_file_left_after_concurrent_writes(self):
        """No .tmp scratch files should remain after writes complete."""
        path = self.root / "no_tmp.json"
        errors = []

        def worker(tid):
            for i in range(10):
                try:
                    atomic_write_json(path, {"tid": tid, "i": i})
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertFalse(errors)
        tmp_files = list(self.root.glob("no_tmp.json.*.tmp"))
        self.assertEqual(tmp_files, [], f"Stale tmp files remain: {tmp_files}")

    def test_read_during_writes_never_corrupt(self):
        """A reader thread polling during concurrent writes must always get valid JSON."""
        path = self.root / "read_during_write.json"
        atomic_write_json(path, {"init": True})
        read_errors = []
        stop = threading.Event()

        def reader():
            while not stop.is_set():
                try:
                    content = path.read_text().strip()
                    if content:
                        json.loads(content)
                except json.JSONDecodeError as exc:
                    read_errors.append(exc)

        def writer(tid):
            for i in range(30):
                atomic_write_json(path, {"tid": tid, "i": i, "blob": list(range(50))})

        reader_thread = threading.Thread(target=reader)
        writer_threads = [threading.Thread(target=writer, args=(t,)) for t in range(4)]

        reader_thread.start()
        for t in writer_threads:
            t.start()
        for t in writer_threads:
            t.join()
        stop.set()
        reader_thread.join()

        self.assertFalse(read_errors, f"Corrupt reads during concurrent writes: {read_errors}")


class TestAtomicWriteJsonlConcurrency(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)

    def test_concurrent_writes_produce_valid_jsonl(self):
        """After concurrent full-overwrite writes, file must be valid JSONL."""
        path = self.root / "log.jsonl"
        errors = []

        def worker(tid):
            for i in range(15):
                try:
                    atomic_write_jsonl(path, [{"tid": tid, "i": j} for j in range(i + 1)])
                except Exception as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertFalse(errors)
        content = path.read_text()
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            json.loads(line)


class TestRecoveryFromStrayTmp(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)

    def test_write_succeeds_when_stray_tmp_exists(self):
        """A leftover .tmp file from a simulated crash must not block subsequent writes."""
        path = self.root / "data.json"
        stray = self.root / "data.json.stray.tmp"
        stray.write_text('{"incomplete": true')  # not valid JSON, simulates crash

        atomic_write_json(path, {"recovered": True})
        content = path.read_text().strip()
        parsed = json.loads(content)
        self.assertTrue(parsed["recovered"])

    def test_lock_file_created(self):
        """append_jsonl must create a .jsonl.lock file alongside the data file."""
        path = self.root / "events.jsonl"
        append_jsonl(path, {"event": "test"})
        lock = self.root / "events.jsonl.lock"
        self.assertTrue(lock.exists(), "Lock file should exist after write")

    def test_append_idempotent_on_empty_payload(self):
        """append_jsonl with empty dict writes one valid line."""
        path = self.root / "empty.jsonl"
        append_jsonl(path, {})
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0]), {})


if __name__ == "__main__":
    unittest.main()
