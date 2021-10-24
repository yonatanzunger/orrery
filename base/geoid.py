from typing import Optional

import numpy
from skyfield.api import wgs84
from skyfield.toposlib import GeographicPosition, Geoid
from skyfield.units import Distance


def geoDistance(
    a: GeographicPosition,
    b: GeographicPosition,
    geoid: Optional[Geoid] = None,
) -> Distance:
    """Compute the surface distance between two geographic positions.

    TODO: Add this to the Geoid class instead.
    """
    geoid = geoid or wgs84

    # We use Lambert's formula. See
    # https://en.wikipedia.org/wiki/Geographical_distance#Lambert's_formula_for_long_lines
    omf = 1.0 - (1.0 / geoid.inverse_flattening)

    # Compute reduced latitudes
    beta1 = numpy.arctan(omf * numpy.tan(a.latitude.radians))
    beta2 = numpy.arctan(omf * numpy.tan(b.latitude.radians))

    # The (spherical) central angle between the two points
    sigma = numpy.arccos(
        numpy.sin(beta1) * numpy.sin(beta2) +
        numpy.cos(beta1) * numpy.cos(beta2) * numpy.cos(b.longitude.radians - a.longitude.radians)
    )

    # And now Lambert's equation.
    sinSigma = numpy.sin(sigma)

    P = (beta2 + beta1) / 2
    Q = (beta2 - beta1) / 2

    xBase = numpy.sin(P) * numpy.cos(Q) / numpy.cos(sigma / 2)
    yBase = numpy.cos(P) * numpy.sin(Q) / numpy.sin(sigma / 2)

    X = (sigma - sinSigma) * xBase * xBase
    Y = (sigma + sinSigma) * yBase * yBase

    arc = sigma - (X + Y) / (2 * geoid.inverse_flattening)

    return Distance.from_au(geoid.radius.au * arc)
