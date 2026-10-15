import os
import threading

import pypdfium2 as pdfium

MAX_BOX_W = 3840
MAX_BOX_H = 2400
MIN_SCALE = 0.05
MAX_SCALE = 10.0


class PdfWorker(threading.Thread):
    def __init__(self, path, on_opened, on_rendered, on_error):
        super().__init__(daemon=True, name='pdf-worker')
        self._path = path
        self._on_opened = on_opened
        self._on_rendered = on_rendered
        self._on_error = on_error
        self._cv = threading.Condition()
        self._wanted = []
        self._box = (0, 0)
        self._stop_flag = False

    def request(self, indices, box):
        with self._cv:
            self._wanted = list(indices)
            self._box = box
            self._cv.notify_all()

    def stop(self):
        with self._cv:
            self._stop_flag = True
            self._wanted = []
            self._cv.notify_all()

    def run(self):
        doc = None
        try:
            if not os.path.isfile(self._path):
                self._on_error('The file could not be found. It may have been deleted.')
                return
            try:
                doc = pdfium.PdfDocument(self._path)
                count = len(doc)
            except Exception as exc:
                self._on_error(_describe_open_error(exc))
                return
            if count < 1:
                self._on_error('This PDF has no pages.')
                return
            self._on_opened(count)

            while True:
                with self._cv:
                    while not self._stop_flag and not self._wanted:
                        self._cv.wait()
                    if self._stop_flag:
                        break
                    index = self._wanted.pop(0)
                    box = self._box
                try:
                    result = self._render(doc, index, box)
                except Exception:
                    result = None
                if self._stop_flag:
                    break
                self._on_rendered(index, box, result)
                result = None
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    pass
            self._on_opened = self._on_rendered = self._on_error = None

    @staticmethod
    def _render(doc, index, box):
        box_w = max(1, min(box[0], MAX_BOX_W))
        box_h = max(1, min(box[1], MAX_BOX_H))
        page = doc[index]
        try:
            width_pt, height_pt = page.get_size()
            if width_pt <= 0 or height_pt <= 0:
                return None
            scale = min(box_w / width_pt, box_h / height_pt)
            scale = max(MIN_SCALE, min(scale, MAX_SCALE))
            bitmap = page.render(scale=scale, rev_byteorder=True)
            try:
                return bitmap.width, bitmap.height, bitmap.stride, bytes(bitmap.buffer)
            finally:
                bitmap.close()
        finally:
            page.close()


def _describe_open_error(exc):
    text = str(exc).lower()
    if 'password' in text:
        return 'This PDF is password protected.'
    if 'format' in text or 'file' in text or 'data' in text:
        return 'The file is damaged or is not a valid PDF. Try deleting it and downloading it again.'
    return f'The PDF could not be opened ({exc}).'
