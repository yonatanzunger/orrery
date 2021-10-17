import math
from typing import Callable, Optional

from pandas.core.frame import DataFrame
from skyfield.constants import RAD2DEG
from skyfield.functions import angle_between, length_of
from skyfield.magnitudelib import _FUNCTIONS, planetary_magnitude
from skyfield.positionlib import Astrometric
from skyfield.vectorlib import VectorFunction

# A MagnitudeFunction is something that goes from an astrometric distance (i.e. a distance from an
# observer) to an apparent magnitude.
MagnitudeFunction = Callable[[Astrometric], float]


# Log10 of the number of AU in a parsec.
LOG_AU_TO_PC = -math.log10(206265)


# TODO: Figure out how to support the Moon!


def magnitudeFunction(
    position: Optional[VectorFunction] = None,
    dataFrame: Optional[DataFrame] = None,
    absoluteMagnitude: Optional[float] = None,
) -> Optional[MagnitudeFunction]:
    """Try to figure out a magnitude function, given the data available."""
    if absoluteMagnitude is not None:
        return _makeFnAbsolute(absoluteMagnitude)

    # The planetary_magnitude function is best for the targets it supports.
    if position and (position.target in _FUNCTIONS):
        return planetary_magnitude

    if dataFrame is not None:
        # Does this have data in the (H, G) magnitude system?
        if "magnitude_H" in dataFrame.index and "magnitude_G" in dataFrame.index:
            return _makeFnHG(dataFrame["magnitude_H"], dataFrame["magnitude_G"])

        # What about (G, K)? (Note the different capitalization; blame the Minor Planets Center.
        if "magnitude_g" in dataFrame.index and "magnitude_k" in dataFrame.index:
            return _makeFnGK(dataFrame["magnitude_g"], dataFrame["magnitude_k"])

        if "magnitude" in dataFrame.index:
            return _makeFnAbsolute(dataFrame["magnitude"])

    return None


def _makeFnAbsolute(absolute: float) -> MagnitudeFunction:
    """Return a magnitude function for an object whose absolute magnitude is given as a single
    number. This tends to work well for things like stars.
    """

    def fromAbsoluteMagnitude(pos: Astrometric) -> float:
        logAu = math.log10(pos.distance().au)
        logPc = logAu + LOG_AU_TO_PC
        return absolute - 5 * (logPc - 1)

    return fromAbsoluteMagnitude


def _makeFnHG(magnitudeH: float, magnitudeG: float) -> MagnitudeFunction:
    """Return a magnitude function for an object whose magnitude is given using the (H, G) system
    generally used for minor planets. See
    https://www.clearskyinstitute.com/xephem/help/xephem.html#mozTocId564354
    """

    def fromHGMagnitude(position: Astrometric) -> float:
        # Same ridiculous hack to get radius and phase angle and so on as planetary_magnitude
        sunToObserver = position.center_barycentric.position.au
        observerToPlanet = position.position.au
        sunToPlanet = sunToObserver + observerToPlanet

        r = length_of(sunToPlanet)
        delta = length_of(observerToPlanet)
        alpha = angle_between(-sunToPlanet, -observerToPlanet)

        halfTan = math.tan(0.5 * alpha)
        phi1 = math.exp(-3.33 * math.pow(halfTan, 0.63))
        phi2 = math.exp(-1.87 * math.pow(halfTan, 1.22))
        angleFactor = -2.5 * math.log((1 - magnitudeG) * phi1 + magnitudeG * phi2)

        distanceFactor = 5 * (math.log(r) + math.log(delta))

        return magnitudeH + distanceFactor + angleFactor

    return fromHGMagnitude


def _makeFnGK(magnitudeG: float, magnitudeK: float) -> MagnitudeFunction:
    """Return a magnitude function for an object whose magnitude is given using the (G, K) system
    generally used for comets. See
    https://www.clearskyinstitute.com/xephem/help/xephem.html#mozTocId564354
    """

    def fromGKMagnitude(position: Astrometric) -> float:
        sunToObserver = position.center_barycentric.position.au
        observerToComet = position.position.au
        sunToComet = sunToObserver + observerToComet

        r = length_of(sunToComet)
        delta = length_of(observerToComet)

        return magnitudeG + 5 * math.log10(delta) + 2.5 * magnitudeK * math.log10(r)
