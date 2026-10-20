"""Convert SFD/SFDIR to cubic UFO3, preserving implied quadratic endpoints."""
from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.pens.basePen import BasePen
from sfdLib.parser import SFDParser
from ufoLib2 import Font


class ExactCubicPen(BasePen):
    """Elevate each quadratic exactly, without fitting or merging segments."""

    def __init__(self, target):
        super().__init__(None)
        self.target = target

    def _moveTo(self, point):
        self.target.moveTo(point)

    def _lineTo(self, point):
        self.target.lineTo(point)

    def _curveToOne(self, control1, control2, end):
        self.target.curveTo(control1, control2, end)

    def _qCurveToOne(self, control, end):
        start = self._getCurrentPoint()
        control1 = tuple(start[i] + 2 * (control[i] - start[i]) / 3 for i in range(2))
        control2 = tuple(end[i] + 2 * (control[i] - end[i]) / 3 for i in range(2))
        self.target.curveTo(control1, control2, end)

    def _closePath(self):
        self.target.closePath()

    def _endPath(self):
        self.target.endPath()


class SourceFaithfulParser(SFDParser):
    """Replace sfdLib 2.0's contour reader; retain its other font parsing."""

    def _drawContours(self, name, layerIdx, contours):
        quadratic = self._layerType[layerIdx]
        glyph = self._layers[layerIdx][name]
        pen = ExactCubicPen(glyph.getPen())
        for contour in contours:
            records = [record for record in contour if isinstance(record, (tuple, list))]
            force_open = False
            for points, kind, flags in records:
                flag = int(flags.split(',')[0].split('x')[0])
                force_open |= bool(flag & 0x400)
                if kind == 'm':
                    pen.moveTo(points[0])
                elif kind == 'l':
                    pen.lineTo(points[0])
                elif quadratic:
                    if points[0] != points[1]:
                        raise ValueError(f'{name}: inconsistent SFD quadratic controls')
                    # 0x80 marks an implied ON-curve endpoint. It must not become
                    # an extra OFF-curve control, as it does in sfdLib 2.0.0.post0.
                    pen.qCurveTo(points[0], points[-1])
                else:
                    pen.curveTo(*points)
            pen.endPath() if force_open else pen.closePath()


def convert(source: str | Path, destination: str | Path) -> Path:
    source, destination = Path(source), Path(destination)
    if not source.exists():
        raise FileNotFoundError(source)
    if destination.exists():
        raise FileExistsError(f'Output already exists: {destination}')
    if destination.suffix.lower() != '.ufo':
        raise ValueError('Output must have a .ufo extension')
    font = Font()
    SourceFaithfulParser(source, font, ufo_kerning=True).parse()
    font.save(destination, overwrite=False, validate=True)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='FontForge .sfd file or .sfdir directory')
    parser.add_argument('destination', type=Path, help='New .ufo package; existing outputs are refused')
    args = parser.parse_args()
    try:
        output = convert(args.source, args.destination)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{parser.prog}: {error}\n')
    print(output)


if __name__ == '__main__':
    main()
