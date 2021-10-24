from enum import Enum
from typing import Dict, NamedTuple, Optional, Tuple, Union

from pandas.core.frame import DataFrame
from skyfield.planetarylib import Frame, PlanetTopos
from skyfield.positionlib import Astrometric, Barycentric
from skyfield.starlib import Star
from skyfield.timelib import Time
from skyfield.toposlib import GeographicPosition, Geoid
from skyfield.units import Angle, Distance
from skyfield.vectorlib import VectorFunction

from base.geoid import geoDistance
from base.magnitude import MagnitudeFunction, magnitudeFunction

# In skyfield, you can actually observe anything that impolements _observe_from_bcrs, but (dammit
# old code) there's no sane type signature for that.
Observable = Union[VectorFunction, Star]

# A local position on some body in space. Why are these classes separate, exactly?
LocalPosition = Union[GeographicPosition, PlanetTopos]


class ObjectType(Enum):
    PLANET = 0
    STAR = 1
    MINOR_PLANET = 2
    COMET = 3
    MOON = 4


class CelestialObject(NamedTuple):
    type: ObjectType

    name: str

    # The astronomical symbol, if it exists.
    symbol: Optional[str]

    # A dict from culture to other names.
    otherNames: Dict[str, str]

    # A function from time to absolute (ICRF) position.
    position: Observable

    # A function from an observed position to visual magnitude
    magnitudeFunction: Optional[MagnitudeFunction]

    # A coordinate reference frame for the surface of the object, if known.
    surface: Optional[Union[Frame, Geoid]]

    def magnitude(self, position: Astrometric) -> Optional[float]:
        return (
            self.magnitudeFunction(position)
            if self.magnitudeFunction is not None
            else None
        )


def makeObject(
    type: ObjectType,
    name: str,
    position: Observable,
    dataFrame: Optional[DataFrame] = None,
    absoluteMagnitude: Optional[float] = None,
    names: Optional[Dict[str, str]] = None,
    symbol: Optional[str] = None,
    surface: Optional[Union[Frame, Geoid]] = None,
) -> CelestialObject:
    return CelestialObject(
        type=type,
        name=name,
        symbol=symbol,
        otherNames=names or {},
        position=position,
        magnitudeFunction=magnitudeFunction(
            position=position, dataFrame=dataFrame, absoluteMagnitude=absoluteMagnitude
        ),
        surface=surface,
    )


class Observation(NamedTuple):
    # The thing being observed
    target: CelestialObject

    # The position of the object relative to the observation point.
    position: Astrometric

    # The visual magnitude of the object, if known.
    magnitude: Optional[float]

    # The subpoint of this object on the Earth at the moment of observation
    subpoint: GeographicPosition

    @property
    def altaz(self) -> Tuple[Angle, Angle, Distance]:
        return self.position.apparent().altaz()

    @property
    def altitude(self) -> Angle:
        return self.altaz[0]

    @property
    def azimuth(self) -> Angle:
        return self.altaz[1]

    @property
    def distance(self) -> Distance:
        return self.altaz[2]

    @property
    def observer(self) -> Barycentric:
        return self.position.center_barycentric

    @property
    def observationTime(self) -> Time:
        assert self.position.t is not None
        return self.position.t

    @property
    def surfaceObserver(self) -> GeographicPosition:
        """The surface location of observation"""
        assert isinstance(self.observer.target, GeographicPosition)
        return self.observer.target

    @property
    def distanceToSubpoint(self) -> Distance:
        return geoDistance(self.surfaceObserver, self.subpoint)

    # TODO: Apparent diameter
