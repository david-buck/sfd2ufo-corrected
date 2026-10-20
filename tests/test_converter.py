import tempfile
import unittest
from pathlib import Path

from fontTools.pens.recordingPen import RecordingPen
from sfdLib.parser import SFDParser
from ufoLib2 import Font
from converter import convert, ExactCubicPen

HEADER = '''SplineFontDB: 3.0
FontName: Synthetic-Regular
FullName: Synthetic Regular
FamilyName: Synthetic
Weight: Regular
Ascent: 800
Descent: 200
LayerCount: 2
Layer: 0 1 "Back" 1
Layer: 1 1 "Fore" 0
'''
GLYPH = '''StartChar: zero
Encoding: 48 48 0
Width: 600
VWidth: 1000
Flags: W
LayerCount: 2
Fore
SplineSet
0 0 m 0,0,1
0 100 0 100 50 100 c 128,-1,2
100 100 100 100 100 0 c 0,2,3
0 0 l 1,0,-1
EndSplineSet
EndChar
'''

def recording(glyph):
    pen = RecordingPen()
    glyph.draw(pen)
    return pen.value

class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'Synthetic.sfd'
        self.source.write_text(HEADER + 'BeginChars: 256 1\n' + GLYPH + 'EndChars\nEndSplineFont\n')

    def test_sfd_implied_endpoint_geometry(self):
        font = Font.open(convert(self.source, self.root / 'Synthetic.ufo'), validate=True)
        self.assertEqual(font.info.unitsPerEm, 1000)
        self.assertEqual(font['zero'].width, 600)
        self.assertEqual(font['zero'].unicodes, [48])
        commands = recording(font['zero'])
        self.assertEqual([kind for kind, _ in commands], ['moveTo', 'curveTo', 'curveTo', 'closePath'])
        self.assertEqual(commands[1][1][-1], (50, 100))
        segments = [((0, 0), (0, 100), (50, 100)), ((50, 100), (100, 100), (100, 0))]
        for index, (start, control, end) in enumerate(segments):
            a, b, result = commands[index + 1][1]
            for step in range(101):
                t = step / 100
                u = 1 - t
                for axis in range(2):
                    expected = u*u*start[axis] + 2*u*t*control[axis] + t*t*end[axis]
                    actual = u**3*start[axis] + 3*u*u*t*a[axis] + 3*u*t*t*b[axis] + t**3*result[axis]
                    self.assertAlmostEqual(actual, expected, places=10)
            for axis in range(2):
                self.assertAlmostEqual(-start[axis] + 3*a[axis] - 3*b[axis] + result[axis], 0)
        upstream = Font()
        SFDParser(self.source, upstream).parse()
        self.assertNotEqual(recording(upstream['zero'])[1][1][-1], (50, 100))

    def test_sfdir_input(self):
        directory = self.root / 'Synthetic.sfdir'
        directory.mkdir()
        (directory / 'font.props').write_text(HEADER + 'EndSplineFont\n')
        (directory / 'zero.glyph').write_text(GLYPH)
        font = Font.open(convert(directory, self.root / 'Directory.ufo'), validate=True)
        self.assertEqual(font['zero'].width, 600)
        self.assertEqual(recording(font['zero'])[1][1][-1], (50, 100))

    def test_existing_output_is_not_overwritten(self):
        output = self.root / 'Existing.ufo'
        output.mkdir()
        sentinel = output / 'keep.txt'
        sentinel.write_text('user work')
        with self.assertRaises(FileExistsError):
            convert(self.source, output)
        self.assertEqual(sentinel.read_text(), 'user work')

    def test_cubic_and_open_path_are_preserved(self):
        target = RecordingPen()
        pen = ExactCubicPen(target)
        pen.moveTo((10, 20))
        pen.curveTo((20, 50), (80, 60), (90, 20))
        pen.endPath()
        self.assertEqual(target.value, [('moveTo', ((10, 20),)), ('curveTo', ((20, 50), (80, 60), (90, 20))), ('endPath', ())])

if __name__ == '__main__':
    unittest.main()
