from datetime import datetime
from zoneinfo import ZoneInfo

from base.data import data
from base.format import TextTable, distanceStr, latitudeStr, longitudeStr, angleRateStr

# import matplotlib.pyplot as plt


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
    time = datetime.now(tz=ZoneInfo("America/Los_Angeles"))
    # time = datetime(1977, 11, 13, 23, 24, tzinfo=ZoneInfo("America/Los_Angeles"))

    observations = [data.observe(observer, target, time) for target in targets]

    for observation in observations:
        output = TextTable()
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

    # fig = plt.figure()
    # ax = fig.add_subplot(projection="3d")


if __name__ == "__main__":
    main()
