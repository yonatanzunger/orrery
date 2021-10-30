import bisect
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from skyfield.constants import DEG2RAD

from base.classical import ZODIAC
from base.data import data
from base.format import (TextTable, angleRateStr, distanceStr, latitudeStr,
                         longitudeStr, phaseAngleStr)
from base.object import CelestialObject


def _nearest(
    moments: List[datetime], values: List[Optional[float]], when: datetime
) -> Optional[float]:
    """Given parallel arrays (moments, values), find the nearest non-null value to 'when'.

    Moments must be sorted.
    """
    assert len(moments) == len(values)
    find = bisect.bisect_left(moments, when)
    # Now search left from there.
    for pos in reversed(range(find)):
        if values[pos] is not None:
            return values[pos]
    return None


def main() -> None:
    targets = [
        data.sun,
        data.moon,
        data.mercury,
        data.venus,
        data.mars,
        data.jupiter,
        data.saturn,
        data.uranus,
        data.neptune,
        data.pluto,
        # data.ceres,
        # data.chiron,
        # data.eris,
        # data.makemake,
        # data.haumea,
        # data.sedna,
        # data.comet("1P/Halley"),
        # data.sirius,
        # data.arcturus,
    ]

    observer = data.observer(37.8694, -122.271)
    # time = datetime.now(tz=ZoneInfo("America/Los_Angeles"))
    time = datetime(1977, 11, 13, 23, 24, tzinfo=ZoneInfo("America/Los_Angeles"))

    observations = [data.observe(observer, target, time) for target in targets]

    for observation in observations:
        output = TextTable()
        if observation.phaseAngle is not None:
            output.append(["Phase:", phaseAngleStr(observation.phaseAngle)])
        ra, dec, _ = observation.position.radec()
        output.append(["Equatorial:", f"RA {ra}", f"Dec {dec}"])
        output.append(
            [
                "Horizontal:",
                f"Alt {observation.altitude}",
                f"Az {observation.azimuth}",
                f"Dist {distanceStr(observation.distance)}",
            ]
        )
        output.append(
            [
                "Ecliptic:",
                observation.classicalPosition.classicalLongitudeStr(),
                angleRateStr(observation.classicalPosition.latitudeRate),
                f"Lat {observation.classicalPosition.latitude.dstr()}",
            ]
        )
        sp = observation.subpoint
        output.append(
            [
                "Subpoint:",
                latitudeStr(sp.latitude),
                longitudeStr(sp.longitude),
                f"{distanceStr(observation.distanceToSubpoint)} from observer",
            ]
        )

        if observation.magnitude is not None:
            magStr = f" ({observation.magnitude:+0.2f})"
        else:
            magStr = ""

        print(f"{observation.target.longName}{magStr}")
        print(output.format("  "))

    # Let's make some plots!
    # X-values
    moments = [time + timedelta(days=n - 200) for n in range(400)]
    xLabelSpacer = timedelta(days=2)
    defaultLabelX = moments[-1]

    def _addPlot(
        axes: Axes,
        target: CelestialObject,
        values: List[Optional[float]],
        swap: bool = False,
        labelX: Optional[datetime] = None,
        **kwargs,
    ) -> Line2D:
        """Add a plot to the given set of axes."""
        labelX = (labelX or defaultLabelX) + xLabelSpacer
        labelY = _nearest(moments, values, labelX)
        if labelY is None:
            return
        lines = (
            axes.plot(values, moments, **kwargs)
            if swap
            else axes.plot(moments, values, **kwargs)
        )
        assert len(lines) == 1
        line = lines[0]
        coords = (labelY, labelX) if swap else (labelX, labelY)
        axes.text(*coords, target.shortLabel, color=line.get_color())
        return line

    # We'll do the computation in one pass, so that we don't have to call observe() more times than
    # needed.
    brightnesses: Dict[str, List[Optional[float]]] = {
        target.name: [] for target in targets
    }
    eclipticLongs: Dict[str, List[Optional[float]]] = {
        target.name: [] for target in targets
    }
    for moment in moments:
        for target in targets:
            obs = data.observe(observer, target, moment)
            brightnesses[target.name].append(obs.magnitude)
            eclipticLongs[target.name].append(obs.classicalPosition.longitude.degrees)

    brPlot = plt.subplot(211)
    brPlot.set_title("Apparent Magnitudes")
    brPlot.axvline(x=time, ls="--", color="darkgrey")

    longPlot = plt.subplot(212, projection="polar")
    longPlot.set_title("Ecliptic Longitude")
    thetas = list(theta * DEG2RAD for theta in range(0, 361, 10))
    longPlot.plot(thetas, [time] * len(thetas), color="darkgrey", ls="--")
    longPlot.set_xticks([30 * n * DEG2RAD for n in range(12)])
    longPlot.set_xticklabels([z.symbol for z in ZODIAC])
    longPlot.tick_params(axis="y", labeltop=False, labelbottom=False)
    longPlot.grid(True, axis="x")

    for target in targets:
        # The Sun and Moon are such outliers in brightness and longitudinal velocity that we drop
        # them from the plot.
        if target.name in brightnesses and target.name != "The Sun":
            _addPlot(brPlot, target, brightnesses[target.name])
        if target.name in eclipticLongs:
            line = (
                _addPlot(
                    longPlot,
                    target,
                    [long * DEG2RAD for long in eclipticLongs[target.name]],
                    swap=True,
                    labelX=time,
                )
                if target.name != "The Moon"
                else None
            )
            longPlot.plot(
                data.observe(
                    observer, target, time
                ).classicalPosition.longitude.radians,
                time,
                "o",
                color=line.get_color() if line else "black",
            )

    plt.show()


if __name__ == "__main__":
    main()
