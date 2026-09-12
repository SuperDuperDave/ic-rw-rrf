import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'acquire_cycle15_inputs.py'
spec = importlib.util.spec_from_file_location('acquire_cycle15', MODULE)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class Response(io.BytesIO):
    status = 200

    def __init__(self, body, length=None):
        super().__init__(body)
        self.headers = {} if length is None else {'Content-Length': str(length)}


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.dest = Path(self.directory.name) / 'body'
        self.body = b'one\ntwo\n'
        self.item = {'role': 'test', 'url': 'https://example.invalid/data',
                     'expected_bytes': len(self.body), 'identity_algorithm': 'sha256',
                     'expected_digest': hashlib.sha256(self.body).hexdigest()}

    def get(self, body=None, item=None, **kwargs):
        return subject.download(item or self.item, self.dest, 100,
                                opener=lambda *_a, **_k: Response(self.body if body is None else body),
                                clock=lambda: 0, **kwargs)

    def test_sha256_success_and_no_overwrite(self):
        row = self.get()
        self.assertEqual(row['sha256'], self.item['expected_digest'])
        self.assertEqual(self.dest.read_bytes(), self.body)
        self.assertFalse(self.dest.with_name('body.partial').exists())
        with self.assertRaisesRegex(subject.AcquisitionError, 'already exists'):
            self.get()

    def test_git_blob_hash_includes_header(self):
        item = dict(self.item, identity_algorithm='git-blob-sha1',
                    expected_digest=hashlib.sha1(b'blob 8\0' + self.body).hexdigest())
        row = self.get(item=item)
        self.assertEqual(row['identity_digest'], item['expected_digest'])
        self.assertNotEqual(row['identity_digest'], hashlib.sha1(self.body).hexdigest())

    def test_mismatch_preserves_unpublished_partial(self):
        with self.assertRaisesRegex(subject.AcquisitionError, 'identity'):
            self.get(body=b'xxxxxxxx')
        self.assertFalse(self.dest.exists())
        self.assertEqual(self.dest.with_name('body.partial').read_bytes(), b'xxxxxxxx')

    def test_truncation_and_overflow_fail(self):
        for body in (self.body[:-1], self.body + b'x'):
            with self.subTest(size=len(body)):
                self.dest.with_name('body.partial').unlink(missing_ok=True)
                with self.assertRaises(subject.AcquisitionError):
                    self.get(body=body)
                self.assertFalse(self.dest.exists())

    def test_header_mismatch_before_body(self):
        response = Response(self.body, len(self.body) + 1)
        with self.assertRaisesRegex(subject.AcquisitionError, 'Advertised'):
            subject.download(self.item, self.dest, 100,
                             opener=lambda *_a, **_k: response, clock=lambda: 0)
        self.assertFalse(self.dest.with_name('body.partial').exists())

    def test_expired_deadline_prevents_request(self):
        with patch.object(subject, 'urlopen') as opener:
            with self.assertRaisesRegex(subject.AcquisitionError, 'wall'):
                subject.download(self.item, self.dest, 0, opener=opener, clock=lambda: 0)
            opener.assert_not_called()

    def test_deadline_during_body_preserves_partial(self):
        values = iter([0, 0, 101])
        with self.assertRaisesRegex(subject.AcquisitionError, 'wall'):
            subject.download(self.item, self.dest, 100,
                             opener=lambda *_a, **_k: Response(self.body), clock=lambda: next(values))
        self.assertFalse(self.dest.exists())
        self.assertEqual(self.dest.with_name('body.partial').read_bytes(), self.body)

    def test_unknown_length_archive_bounded_not_published_identity(self):
        row = self.get(item={'role': 'archive', 'url': self.item['url'], 'byte_cap': 10})
        self.assertFalse(row['published_identity_verified'])
        self.assertEqual(row['bytes'], 8)

    def test_failed_first_request_stops_sequence_and_records_failure(self):
        fake_root = Path(self.directory.name)
        output = fake_root / '_sessions/local/attempt'
        plan = {'inputs': [dict(self.item, path='a.jsonl')], 'download_wall_cap_seconds': 100}
        with patch.object(subject, 'ROOT', fake_root), patch.object(subject, 'load_plan', return_value=plan), \
             patch.object(subject, 'items_from_plan', return_value=[dict(self.item, path='a.jsonl'), dict(self.item, role='unsent', path='b.jsonl')]):
            calls = []
            def fail(*args, **kwargs):
                calls.append(1)
                raise OSError('remote URL may contain sensitive redirect params')
            with self.assertRaises(OSError):
                subject.acquire(output, opener=fail, clock=lambda: 0)
        receipt = json.loads((output / 'manifest.json').read_text())
        self.assertEqual(len(calls), 1)
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(receipt['inputs'], {})
        self.assertEqual(receipt['retries'], 0)
        self.assertNotIn('sensitive', json.dumps(receipt))


if __name__ == '__main__':
    unittest.main()
