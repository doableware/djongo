import io
import os
import sys
import tempfile
from unittest import skipIf

from django.core.files.base import ContentFile
from django.http import FileResponse
from django.test import SimpleTestCase


class FileResponseTests(SimpleTestCase):
    def test_file_from_disk_response(self):
        response = FileResponse(open(__file__, 'rb'))
        self.assertEqual(response.headers['Content-Length'], str(os.path.getsize(__file__)))
        self.assertIn(response.headers['Content-Type'], ['text/x-python', 'text/plain'])
        self.assertEqual(
            response.headers['Content-Disposition'],
            'inline; filename="test_fileresponse.py"',
        )
        response.close()

    def test_file_from_buffer_response(self):
        response = FileResponse(io.BytesIO(b'binary content'))
        self.assertEqual(response.headers['Content-Length'], '14')
        self.assertEqual(response.headers['Content-Type'], 'application/octet-stream')
        self.assertFalse(response.has_header('Content-Disposition'))
        self.assertEqual(list(response), [b'binary content'])

    def test_file_from_buffer_unnamed_attachment(self):
        response = FileResponse(io.BytesIO(b'binary content'), as_attachment=True)
        self.assertEqual(response.headers['Content-Length'], '14')
        self.assertEqual(response.headers['Content-Type'], 'application/octet-stream')
        self.assertEqual(response.headers['Content-Disposition'], 'attachment')
        self.assertEqual(list(response), [b'binary content'])

    @skipIf(sys.platform == 'win32', "Named pipes are Unix-only.")
    def test_file_from_named_pipe_response(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pipe_file = os.path.join(temp_dir, 'named_pipe')
            os.mkfifo(pipe_file)
            pipe_for_read = os.open(pipe_file, os.O_RDONLY | os.O_NONBLOCK)
            with open(pipe_file, 'wb') as pipe_for_write:
                pipe_for_write.write(b'binary content')

            response = FileResponse(os.fdopen(pipe_for_read, mode='rb'))
            self.assertEqual(list(response), [b'binary content'])
            response.close()
            self.assertFalse(response.has_header('Content-Length'))

    def test_file_from_disk_as_attachment(self):
        response = FileResponse(open(__file__, 'rb'), as_attachment=True)
        self.assertEqual(response.headers['Content-Length'], str(os.path.getsize(__file__)))
        self.assertIn(response.headers['Content-Type'], ['text/x-python', 'text/plain'])
        self.assertEqual(
            response.headers['Content-Disposition'],
            'attachment; filename="test_fileresponse.py"',
        )
        response.close()

    def test_compressed_response(self):
        """
        If compressed responses are served with the uncompressed Content-Type
        and a compression Content-Encoding, browsers might automatically
        uncompress the file, which is most probably not wanted.
        """
        test_tuples = (
            ('.tar.gz', 'application/gzip'),
            ('.tar.bz2', 'application/x-bzip'),
            ('.tar.xz', 'application/x-xz'),
        )
        for extension, mimetype in test_tuples:
            with self.subTest(ext=extension):
                with tempfile.NamedTemporaryFile(suffix=extension) as tmp:
                    response = FileResponse(tmp)
                self.assertEqual(response.headers['Content-Type'], mimetype)
                self.assertFalse(response.has_header('Content-Encoding'))

    def test_unicode_attachment(self):
        response = FileResponse(
            ContentFile(b'binary content', name="祝您平安.odt"), as_attachment=True,
            content_type='application/vnd.oasis.opendocument.text',
        )
        self.assertEqual(
            response.headers['Content-Type'],
            'application/vnd.oasis.opendocument.text',
        )
        self.assertEqual(
            response.headers['Content-Disposition'],
            "attachment; filename*=utf-8''%E7%A5%9D%E6%82%A8%E5%B9%B3%E5%AE%89.odt"
        )
