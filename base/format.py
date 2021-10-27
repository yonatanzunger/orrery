import io
import math
from typing import List

from skyfield.units import Angle, AngleRate, Distance


def _markedStr(theta: Angle, plusChar: str, minusChar: str) -> str:
    if theta.radians > 0:
        return f"{theta.dstr()}{plusChar}"
    alpha = Angle(radians=-theta.radians)
    return f"{alpha.dstr()}{minusChar}"


def latitudeStr(latitude: Angle) -> str:
    return _markedStr(latitude, "N", "S")


def longitudeStr(longitude: Angle) -> str:
    return _markedStr(longitude, "E", "W")


def latLonStr(latitude: Angle, longitude: Angle) -> str:
    return f"{latitudeStr(latitude)} {longitudeStr(longitude)}"


AU_PC = math.pi / 648000


def distanceStr(d: Distance) -> str:
    if d.km < 5:
        return f"{int(d.m)}m"
    elif d.km < 10000000:
        return f"{int(d.km)}km"
    elif d.au < 100:
        return f"{d.au:0.2f}au"
    elif d.au < 100000:
        return f"{int(d.au)}au"
    else:
        pc = d.au * AU_PC
        if pc < 100:
            return f"{pc:0.2f}pc"
        else:
            return f"{int(pc)}pc"


def angleRateStr(r: AngleRate) -> str:
    # TODO make this into AngleRate.__str__.
    rate = r.degrees.per_day
    if rate > 0:
        sign = "+"
    else:
        sign = "-"
        rate = -rate
    degrees = int(rate)
    rate = 60 * (rate - degrees)
    minutes = int(rate)
    rate = 60 * (rate - minutes)
    seconds = int(rate)
    mas = int(1000 * (rate - seconds))

    return f"{sign}{degrees}°{minutes:02d}'{seconds:02d}.{mas:03d}\"/day"


class TextTable(object):
    def __init__(
        self, minWidth: int = 0, exceptFirstColumns: int = 0, minSpace: int = 2
    ) -> None:
        """A TextTable is a 2D table of cells that can print out as a nice grid.

        Args:
            minWidth: The minimum width for any column
            exceptFirstColumns: If > 0, minWidth won't apply to the first N columns. (Useful for
                titles and the like)
            minSpace: The minimum spacing between columns
        """
        self.lines: List[List[str]] = []
        self.maxima: List[int] = []
        self.minWidth = minWidth
        self.exceptFirstColumns = exceptFirstColumns
        self.minSpace = minSpace

    def append(self, line: List[str]) -> None:
        self.lines.append(line)
        for i, entry in enumerate(line):
            minWidth = self.minWidth if i >= self.exceptFirstColumns else 0
            length = max(len(entry), minWidth)
            if i >= len(self.maxima):
                self.maxima.append(length)
            elif length > self.maxima[i]:
                self.maxima[i] = length

    def format(self, leader: str = "") -> str:
        result = io.StringIO()
        for line in self.lines:
            result.write(leader)
            for entry, width in zip(line, self.maxima):
                result.write(entry.ljust(width + self.minSpace))
            result.write("\n")
        return result.getvalue()
