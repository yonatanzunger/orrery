from enum import Enum
from typing import Dict, NamedTuple, Optional, Union

from pandas.core.frame import DataFrame
from skyfield.starlib import Star
from skyfield.vectorlib import VectorFunction

from base.magnitude import MagnitudeFunction, magnitudeFunction

# In skyfield, you can actually observe anything that impolements _observe_from_bcrs, but (dammit
# old code) there's no sane type signature for that.
Observable = Union[VectorFunction, Star]


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
    magnitude: Optional[MagnitudeFunction]


def makeObject(
    type: ObjectType,
    name: str,
    position: Observable,
    dataFrame: Optional[DataFrame] = None,
    absoluteMagnitude: Optional[float] = None,
    names: Optional[Dict[str, str]] = None,
    symbol: Optional[str] = None,
) -> CelestialObject:
    return CelestialObject(
        type=type,
        name=name,
        symbol=symbol,
        otherNames=names or {},
        position=position,
        magnitude=magnitudeFunction(
            position=position, dataFrame=dataFrame, absoluteMagnitude=absoluteMagnitude
        ),
    )
