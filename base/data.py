import gzip
import logging
import os
import os.path
from datetime import datetime
from functools import cached_property
from typing import Optional, Tuple, Union

from pandas.core.frame import DataFrame
from skyfield.api import Loader, N, W, wgs84
from skyfield.constants import GM_SUN_Pitjeva_2005_km3_s2 as GM_SUN
from skyfield.data import hipparcos, mpc
from skyfield.jpllib import SpiceKernel
from skyfield.starlib import Star
from skyfield.timelib import Time, Timescale
from skyfield.toposlib import GeographicPosition
from skyfield.vectorlib import VectorFunction

from base._star_names import StarNames
from base.object import CelestialObject, ObjectType, Observation, makeObject

logging.getLogger().setLevel(logging.INFO)


class Data(object):
    """This class is the central holder for astronomical data; it acts as a wrapper around all of
    the datasets we get from JPL, the Minor Planets Center, etc., and exposes them via nice,
    Skyfield-friendly APIs.
    """

    def __init__(self, dirname: str = "data", ephemerides: str = "de441") -> None:
        self.load = Loader(dirname)
        self._ephName = ephemerides
        if not self._ephName.endswith(".bsp"):
            self._ephName += ".bsp"

    # CelestialObjects representing the most common things we might want to use.

    @cached_property
    def sun(self) -> CelestialObject:
        return makeObject(
            ObjectType.STAR,
            "The Sun",
            self._ephemerides["sun"],
            symbol="\u2609",
        )

    @cached_property
    def moon(self) -> CelestialObject:
        return makeObject(
            ObjectType.MOON, "The Moon", self._ephemerides["moon"], symbol="\u263D"
        )

    @cached_property
    def mercury(self) -> CelestialObject:
        return makeObject(
            ObjectType.PLANET, "Mercury", self._ephemerides["mercury"], symbol="\u263f"
        )

    @cached_property
    def venus(self) -> CelestialObject:
        return makeObject(
            ObjectType.PLANET, "Venus", self._ephemerides["venus"], symbol="\u2640"
        )

    @cached_property
    def earth(self) -> CelestialObject:
        return makeObject(
            ObjectType.PLANET, "Earth", self._ephemerides["earth"], symbol="\u2641"
        )

    @cached_property
    def mars(self) -> CelestialObject:
        return makeObject(
            ObjectType.PLANET,
            "Mars",
            self._ephemerides["mars barycenter"],
            symbol="\u2642",
        )

    @cached_property
    def jupiter(self) -> CelestialObject:
        return makeObject(
            ObjectType.PLANET,
            "Jupiter",
            self._ephemerides["jupiter barycenter"],
            symbol="\u2643",
        )

    @cached_property
    def saturn(self) -> CelestialObject:
        return makeObject(
            ObjectType.PLANET,
            "Saturn",
            self._ephemerides["saturn barycenter"],
            symbol="\u2644",
        )

    @cached_property
    def uranus(self) -> CelestialObject:
        return makeObject(
            ObjectType.PLANET,
            "Uranus",
            self._ephemerides["uranus barycenter"],
            symbol="\u2645",
        )

    @cached_property
    def neptune(self) -> CelestialObject:
        return makeObject(
            ObjectType.PLANET,
            "Neptune",
            self._ephemerides["neptune barycenter"],
            symbol="\u2646",
        )

    # Our favorite dwarf planets

    @cached_property
    def pluto(self) -> CelestialObject:
        # Still in the JPL planet ephemerides!
        return makeObject(
            ObjectType.MINOR_PLANET,
            "Pluto",
            self._ephemerides["pluto barycenter"],
            symbol="\u2647",
        )

    @cached_property
    def ceres(self) -> CelestialObject:
        return self.minorPlanet("(1) Ceres", symbol="\u26b3")

    @cached_property
    def chiron(self) -> CelestialObject:
        return self.minorPlanet("(2060) Chiron", symbol="\u26b7")

    @cached_property
    def eris(self) -> CelestialObject:
        return self.minorPlanet("(136199) Eris", symbol="\u2bf0")

    @cached_property
    def makemake(self) -> CelestialObject:
        # Not yet in Unicode!
        return self.minorPlanet("(136472) Makemake")

    @cached_property
    def haumea(self) -> CelestialObject:
        # Not yet in Unicode!
        return self.minorPlanet("(136108) Haumea")

    @cached_property
    def sedna(self) -> CelestialObject:
        return self.minorPlanet("(90377) Sedna", symbol="\u2bf2")

    # Orcus, Quaoar,Pallas, Juno, Vesta, Astraea, Hebe, Iris, Flora, Metis, Hygiea, Parthenope,
    # Victoria, Egeria, Irene, Eunomia, Psyche, Thetis, Melpomene, Fortuna, Proserpina, Bellona,
    # Amphitrite, Leukothea, Fides?

    # How about some stars?
    @cached_property
    def sirius(self) -> CelestialObject:
        return self.star("Sirius", "western")

    @cached_property
    def arcturus(self) -> CelestialObject:
        return self.star("Arcturus", "western")

    # Observation points

    # Helpers for getting positions
    def observer(
        self,
        lat: float,
        lon: float,
        elevationMeters: Optional[float] = None,
    ) -> VectorFunction:
        """Return a VectorFunction representing a terrestrial observer."""
        return self.earth.position + wgs84.latlon(
            lat, lon, elevation_m=elevationMeters or 0
        )

    @cached_property
    def berkeley(self) -> VectorFunction:
        return self.observer(37.8645 * N, 122.3015 * W, 52.1)

    def observe(
        self,
        observer: VectorFunction,
        target: CelestialObject,
        when: Optional[datetime] = None,
    ) -> Observation:
        """Give the astrometric (relative) position of target relative to observer at time.

        If the time is not given, assume "now."
        """
        time = self.timescale.from_datetime(when) if when else self.timescale.now()
        position = observer.at(time).observe(target.position)
        return Observation(
            target=target,
            position=position,
            magnitude=target.magnitude(position),
            subpoint=self.subpoint(target, time),
        )

    # More general accessors to load up other celestial bodies in our databases.

    def comet(self, designation: str) -> CelestialObject:
        """Look up a comet by its designation, e.g. 1P/Halley"""
        # NB: mpc.comet_orbit returns an orbit centered on the Sun, so we need to offset it!
        row = self._comets.loc[designation]
        return makeObject(
            type=ObjectType.COMET,
            name=designation[designation.find("/") + 1 :],
            position=self.sun.position + mpc.comet_orbit(row, self.timescale, GM_SUN),
            dataFrame=row,
        )

    def minorPlanet(
        self, designation: str, symbol: Optional[str] = None
    ) -> CelestialObject:
        """Look up a minor planet by its designation, e.g. (2060) Chiron"""
        data = self._minorPlanets.loc[designation]
        shortName = designation[designation.find(") ") + 2 :]
        return makeObject(
            type=ObjectType.MINOR_PLANET,
            name=shortName,
            position=self.sun.position + mpc.mpcorb_orbit(data, self.timescale, GM_SUN),
            dataFrame=data,
            symbol=symbol,
        )

    def star(
        self, ref: Union[str, int], culture: Optional[str] = None
    ) -> CelestialObject:
        """Fetch a star by its name or Hipparcos catalogue number.

        Args:
            ref: Either the string common name, or the int catalogue number, e.g. 87937 for
                Barnard's Star.
            culture: If given, use as a hint to understand the common name.
        """
        number = ref if isinstance(ref, int) else self.starNumber(ref)
        data = self._stars.loc[number]
        names = self._starNames.allNames(number)
        primaryName = (
            ref
            if isinstance(ref, str)
            else names["western"]
            if "western" in names
            else names["hip"]
        )
        star = Star.from_dataframe(data)
        return makeObject(
            type=ObjectType.STAR,
            name=primaryName,
            position=star,
            dataFrame=data,
            names=names,
        )

    def cultures(self) -> Tuple[str, ...]:
        return self._starNames.cultures()

    def starNumber(self, name: str, culture: Optional[str] = None) -> int:
        return self._starNames.find(name, culture=culture)

    @property
    def timescale(self) -> Timescale:
        return self.load.timescale()

    def subpoint(self, target: CelestialObject, time: Time) -> GeographicPosition:
        return wgs84.subpoint(self.earth.position.at(time).observe(target.position))

    #########################################################################################
    # Much more internal accessors

    @cached_property
    def _comets(self) -> DataFrame:
        with self.load.open(mpc.COMET_URL) as f:
            return (
                mpc.load_comets_dataframe(f)
                .sort_values("reference")
                .groupby("designation", as_index=False)
                .last()
                .set_index("designation", drop=False)
            )

    @cached_property
    def _ephemerides(self) -> SpiceKernel:
        return self.load(self._ephName)

    @cached_property
    def _minorPlanets(self) -> DataFrame:
        with self.load.open(self._minorPlanetsPath()) as f:
            logging.info("Loading minor planets dataset")
            mp = mpc.load_mpcorb_dataframe(f)
            # Drop items without orbits
            badOrbits = mp.semimajor_axis_au.isnull()
            mp = mp[~badOrbits].set_index("designation", drop=False)
            return mp

    @cached_property
    def _stars(self) -> DataFrame:
        logging.info("Loading Hipparcos data")
        with self.load.open(hipparcos.URL) as f:
            df = hipparcos.load_dataframe(f)
            # Filter out the ones with no reliable position
            df = df[df["ra_degrees"].notnull()]
            return df

    @cached_property
    def _starNames(self) -> StarNames:
        return StarNames(self.load)

    # Logic for downloading data

    _MPC_ORB = "minor_planets.dat"
    _MPC_URL = "https://www.minorplanetcenter.net/iau/MPCORB/MPCORB.DAT.gz"

    def _minorPlanetsPath(self, ensure: bool = True, refresh: bool = False) -> str:
        """Return a path to the file containing minor planets data.

        If ensure is True, ensures that the file exists.
        If refresh is True, force a re-download.
        """
        filename = self.load.path_to(self._MPC_ORB)
        if not ensure or (not refresh and os.path.exists(filename)):
            return self._MPC_ORB

        # Do we need to refetch the compressed data?
        compressed = self._MPC_ORB + ".gz"
        if not os.path.exists(compressed):
            logging.info(f"Downloading minor planet data from {self._MPC_URL}")
            compressed = self.load.download(
                self._MPC_URL, filename=self._MPC_ORB + ".gz"
            )

        # Regenerate the "clean" data. Why do they stick an unformatted header in this file?
        # I really don't know.
        logging.info("Cleaning and parsing minor planets data")
        with gzip.open(compressed, mode="rt", encoding="ascii") as input, open(
            filename, "w"
        ) as output:
            sawHeader = False
            count = 0
            for line in input:
                if not line:
                    continue
                if not sawHeader:
                    sawHeader = line.startswith("-----")
                else:
                    count += 1
                    output.write(line)

        logging.info(f"Loaded {count} minor planets")

        # Now nuke the compressed file.
        os.remove(compressed)

        return self._MPC_ORB


# Static global instance
data = Data()
