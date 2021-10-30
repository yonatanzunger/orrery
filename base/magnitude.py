import math
from typing import Callable, Dict, List, NamedTuple, Optional

from pandas.core.frame import DataFrame
from skyfield.constants import DEG2RAD, RAD2DEG
from skyfield.functions import angle_between, length_of
from skyfield.positionlib import Astrometric
from skyfield.units import Angle
from skyfield.vectorlib import VectorFunction


# A MagnitudeFunction is something that goes from an astrometric distance (i.e. a distance from an
# observer) to an apparent magnitude.
MagnitudeFunction = Callable[[Astrometric], Optional[float]]

# Log10 of the number of AU in a parsec.
LOG_AU_TO_PC = math.log10(math.pi / 648000)


class IlluminatedBody(object):
    def magnitude(self, position: Astrometric) -> Optional[float]:
        """Return the apparent magnitude of the object."""
        return None

    @classmethod
    def make(
        cls,
        position: Optional[VectorFunction] = None,
        dataFrame: Optional[DataFrame] = None,
    ) -> Optional["IlluminatedBody"]:
        """Construct an IlluminatedBody for this object, if we have a good model for it."""
        if position and position.target in STANDARD_BODIES:
            return STANDARD_BODIES[position.target]

        if dataFrame is not None:
            # Does this have data in the (H, G) magnitude system?
            if "magnitude_H" in dataFrame.index and "magnitude_G" in dataFrame.index:
                return HGReflectingBody(
                    dataFrame["magnitude_H"], dataFrame["magnitude_G"]
                )

            # What about (G, K)? (Note the different capitalization; blame the Minor Planets
            # Center.
            if "magnitude_g" in dataFrame.index and "magnitude_k" in dataFrame.index:
                return SolarActivatedBody(
                    dataFrame["magnitude_g"], dataFrame["magnitude_k"]
                )

            # For stars, we have a simple constant apparent magnitude.
            if "magnitude" in dataFrame.index:
                return DistantLuminousBody(dataFrame["magnitude"])

        return None


# Below follow a bunch of actual IlluminatedBody implementations, including generic ones for things
# like stars and minor planets, and specialized ones for the major planets (for which we have fancy
# models)


class DistantLuminousBody(IlluminatedBody):
    """A good subclass for things whose magnitude is effectively constant, like distant stars."""

    def __init__(self, apparentMagnitude: float) -> None:
        self._m = apparentMagnitude

    def magnitude(self, position: Astrometric) -> Optional[float]:
        return self._m


class ProximateLuminousBody(IlluminatedBody):
    """A good subclass for luminous bodies where distance variation matters, like the Sun."""

    def __init__(self, absoluteMagnitude: float) -> None:
        self._m = absoluteMagnitude

    def magnitude(self, position: Astrometric) -> Optional[float]:
        return self._m + 5 * (math.log10(position.distance().au) + LOG_AU_TO_PC - 1)


class ReflectionParameters(NamedTuple):
    """Parameters for a reflecting object in the Solar System."""

    # The underlying position of the object
    position: Astrometric

    # r is the distance between the Sun and the object, in AU.
    r: float
    # δ is the distance between the observer and the object, in AU.
    delta: float
    # α is the phase angle of the object, in degrees.
    alpha: float

    @classmethod
    def make(cls, position: Astrometric) -> "ReflectionParameters":
        # This is a ridiculous hack borrowed from skylib's planetary magnitudes library. Shamelessly
        # treat the Sun as being at the Solar System barycenter.
        sunToObserver = position.center_barycentric.position.au
        observerToPlanet = position.position.au
        sunToPlanet = sunToObserver + observerToPlanet

        return ReflectionParameters(
            position=position,
            r=length_of(sunToPlanet),
            delta=length_of(observerToPlanet),
            alpha=angle_between(-sunToPlanet, -observerToPlanet) * RAD2DEG,
        )

    @property
    def distanceFactor(self) -> float:
        """Return the "distance factor" in the equation for the magnitude of the reflector, the part
        that depends on how far the observer is from the object.
        """
        return 5 * math.log10(self.r * self.delta)


class ReflectingBody(IlluminatedBody):
    """A model good for bodies whose illumination comes from reflection off the Sun. Subclasses need
    to implement L, which should be a sum of the H and q factors in the underlying equation

        m = H + [distance factor] + [phase angle factor]

    See https://en.wikipedia.org/wiki/Absolute_magnitude#Solar_System_bodies_(H)
    """

    def q(self, params: ReflectionParameters) -> Optional[float]:
        raise NotImplementedError()

    def magnitude(self, position: Astrometric) -> Optional[float]:
        params = ReflectionParameters.make(position)
        q = self.q(params)
        return q + params.distanceFactor if q is not None else None

    def phaseAngle(self, position: Astrometric) -> Angle:
        """Return the phase angle of the object."""
        return Angle(degrees=ReflectionParameters.make(position).alpha)


def _polynomial(x: float, coefficients: List[float]) -> float:
    """Evaluate Σa_n x^n. Useful since most q's are polynomials!"""
    acc = 0.0
    xx = 1.0
    for coefficient in coefficients:
        acc += coefficient * xx
        xx *= x
    return acc


# Models for planetary magnitude. See https://arxiv.org/pdf/1808.01973.pdf. (And yes, in all of
# these polynomials, α is indeed in degrees!)


class Mercury(ReflectingBody):
    def q(self, params: ReflectionParameters) -> Optional[float]:
        return _polynomial(
            params.alpha,
            [
                -0.613,
                6.3280e-02,
                -1.6336e-03,
                +3.3644e-05,
                -3.4265e-07,
                +1.6893e-09,
                -3.0334e-12,
            ],
        )


class Venus(ReflectingBody):
    def q(self, params: ReflectionParameters) -> Optional[float]:
        if params.alpha < 163.7:
            return _polynomial(
                params.alpha, [-4.384, -1.044e-3, 3.687e-4, -2.814e-6, 8.938e-9]
            )
        else:
            return _polynomial(params.alpha, [240.44228 - 4.384, -2.81914, 8.39034e-3])


class Earth(ReflectingBody):
    def q(self, params: ReflectionParameters) -> Optional[float]:
        return _polynomial(params.alpha, [-3.99, -1.06e-3, 2.054e-4])


class Mars(ReflectingBody):
    def q(self, params: ReflectionParameters) -> Optional[float]:
        if params.alpha <= 50:
            return _polynomial(params.alpha, [-1.601, 2.267e-2, -1.302e-4])
        elif params.alpha <= 120:
            return _polynomial(params.alpha, [-1.601 + 1.234, -2.573e-2, 3.445e-4])
        else:
            return None


class Jupiter(ReflectingBody):
    def q(self, params: ReflectionParameters) -> Optional[float]:
        if params.alpha < 12:
            return _polynomial(params.alpha, [-9.395, -3.7e-4, 6.16e-4])
        else:
            poly = _polynomial(
                params.alpha / 180, [1, -1.507, -0.363, -0.062, 2.809, -1.876]
            )
            return -9.395 - 0.033 - 2.5 * math.log10(poly)


class Saturn(ReflectingBody):
    def q(self, params: ReflectionParameters) -> Optional[float]:
        alpha_factor: float
        beta = 0  # XXX TODO
        if params.alpha < 6.5:
            beta_factor = math.sin(beta) * (
                1.825 - 0.378 * math.exp(-2.25 * params.alpha)
            )
            return -8.914 + 2.6e-2 * params.alpha + beta_factor
        elif params.alpha < 150:
            return _polynomial(
                params.alpha, [-8.914 + 0.026, 2.446e-4, 2.672e-2, -1.505e-6, 4.767e-9]
            )
        else:
            # We don't have any good model for Saturn's brightness at these angles
            return None


class Uranus(ReflectingBody):
    def q(self, params: ReflectionParameters) -> Optional[float]:
        # TODO Compute phi'
        phiprime = 0.0
        if params.alpha < 3.1:
            return -8.4e-4 * phiprime + _polynomial(
                params.alpha, [-7.110, 6.587e-3, 1.045e-4]
            )
        return None


class Neptune(ReflectingBody):
    def q(self, params: ReflectionParameters) -> Optional[float]:
        if (
            params.alpha < 133
            and params.position.t is not None
            and params.position.t.utc_datetime().year >= 2000
        ):
            return _polynomial(params.alpha, [-7.00, 7.944e-3, 9.617e-5])
        return None


class HGReflectingBody(ReflectingBody):
    """An approximate model for reflecting bodies using two parameters; this is what we use for
    minor planets.
    """

    def __init__(self, h: float, g: float) -> None:
        super().__init__()
        self.h = h
        self.g = g

    def q(self, params: ReflectionParameters) -> Optional[float]:
        halfTan = math.tan(0.5 * params.alpha * DEG2RAD)
        phi1 = math.exp(-3.33 * math.pow(halfTan, 0.63))
        phi2 = math.exp(-1.87 * math.pow(halfTan, 1.22))
        angleFactor = -2.5 * math.log((1 - self.g) * phi1 + self.g * phi2)

        return self.h + angleFactor


class SolarActivatedBody(IlluminatedBody):
    def __init__(self, g: float, k: float) -> None:
        """A good model for objects like comets, whose illumination is powered by their solar
        proximity. Different values of K are used for nuclear and total magnitude.
        """
        super().__init__()
        self.g = g
        self.k = k

    def magnitude(self, position: Astrometric) -> Optional[float]:
        params = ReflectionParameters.make(position)

        return (
            self.g + 5 * math.log10(params.delta) + 2.5 * self.k * math.log10(params.r)
        )


STANDARD_BODIES: Dict[int, IlluminatedBody] = {
    1: Mercury(),
    199: Mercury(),
    2: Venus(),
    299: Venus(),
    3: Earth(),
    399: Earth(),
    4: Mars(),
    5: Jupiter(),
    6: Saturn(),
    7: Uranus(),
    8: Neptune(),
    # Pluto doesn't have a good detailed model, so we just use its H/G model and recent data for
    # that.
    9: HGReflectingBody(-0.45, 0.15),
    # The Sun is a mass of incandescent gas, an amazing nuclear furnace where Hydrogen is burned
    # into Helium at a temperature of millions of degrees and an absolute magnitude of +4.83.
    10: ProximateLuminousBody(4.83),
}
