from enum import Enum
from typing import Dict, NamedTuple, Optional, Tuple, Union

from pandas.core.frame import DataFrame
from skyfield.planetarylib import Frame
from skyfield.positionlib import Astrometric, Barycentric
from skyfield.timelib import Time
from skyfield.toposlib import GeographicPosition, Geoid
from skyfield.units import Angle, Distance

from base.classical import EclipticPosition
from base.geoid import geoDistance
from base.magnitude import IlluminatedBody, ReflectingBody
from base.types import Observable


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

    # If we know something about its illumination, it's here.
    illumination: Optional[IlluminatedBody]

    # A coordinate reference frame for the surface of the object, if known.
    surface: Optional[Union[Frame, Geoid]]

    def magnitude(self, position: Astrometric) -> Optional[float]:
        return (
            self.illumination.magnitude(position)
            if self.illumination is not None
            else None
        )

    # TODO: Figure out a nice way to capture magnitude ranges. There are "special" events that
    # occasionally take a body way out of its characteristic range, so we really want to see its (1,
    # 99)th percentile ranges and baseline against those, and then mark "exceptional" magnitudes
    # outside that range. But of course the periodicity of that is tied to the mutual periodicity of
    # the observer and the observed, and the three reflection parameters are far from independent.
    # The best solution is probably to consider the two periods P1 and P2 of observer and observed,
    # and the ratio r=max(P1, P2)/min(P1, P2). Pick N so that the decimal part of N*r <= some fixed
    # value, which means we're covering a decent approximation of all the possible relative
    # positions of the two bodies. Sample over N periods (i.e. N max(P1, P2)) with a resolution of
    # maybe 1/100 min(P1, P2)?

    @property
    def shortLabel(self) -> str:
        return self.symbol or self.name

    @property
    def longName(self) -> str:
        if self.symbol:
            return f"{self.name} ({self.symbol})"
        return self.name


def makeObject(
    type: ObjectType,
    name: str,
    position: Observable,
    dataFrame: Optional[DataFrame] = None,
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
        illumination=IlluminatedBody.make(position=position, dataFrame=dataFrame),
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

    @property
    def classicalPosition(self) -> EclipticPosition:
        return EclipticPosition.make(self.position.apparent())

    @property
    def phaseAngle(self) -> Optional[Angle]:
        if isinstance(self.target.illumination, ReflectingBody):
            return self.target.illumination.phaseAngle(self.position)
        return None

    # TODO: Apparent diameter
