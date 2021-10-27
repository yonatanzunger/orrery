from typing import NamedTuple, Tuple

from skyfield.framelib import ecliptic_frame
from skyfield.positionlib import ICRF
from skyfield.units import Angle, AngleRate


class Zodiac(NamedTuple):
    name: str
    symbol: str


ZODIAC = (
    Zodiac("Ari", "\u2648"),
    Zodiac("Tau", "\u2649"),
    Zodiac("Gem", "\u264a"),
    Zodiac("Cnc", "\u264b"),
    Zodiac("Leo", "\u264c"),
    Zodiac("Vir", "\u264d"),
    Zodiac("Lib", "\u264e"),
    Zodiac("Sco", "\u264f"),
    Zodiac("Sgr", "\u2650"),
    Zodiac("Cap", "\u2651"),
    Zodiac("Aqr", "\u2652"),
    Zodiac("Psc", "\u2653"),
)


class EclipticPosition(NamedTuple):
    latitude: Angle
    latitudeRate: AngleRate
    longitude: Angle
    longitudeRate: AngleRate

    @classmethod
    def make(cls, pos: ICRF) -> "EclipticPosition":
        lat, lon, _, latR, lonR, __ = pos.frame_latlon_and_rates(ecliptic_frame)
        return EclipticPosition(lat, latR, lon, lonR)

    @property
    def classicalLongitude(self) -> Tuple[Zodiac, float]:
        angle = self.longitude.degrees
        index, remainder = divmod(angle, 30)
        return ZODIAC[int(index) % 12], remainder

    def classicalLongitudeStr(self, symbolic: bool = False) -> str:
        sign, theta = self.classicalLongitude
        angle = Angle(degrees=theta)
        return f"{angle.dstr()} {sign.symbol if symbolic else sign.name}"

    def __str__(self) -> str:
        return f"{self.classicalLongitudeStr()} lat {self.latitude.dstr()}"

    def phase(self, sun: 'EclipticPosition') -> float:
        """Return the phase (in degrees) of this body, given the ecliptic position of the Sun.
        This value will be zero when new, 90° at first quarter, 180° at full, and 270° at waning
        quarter.
        """
        return (self.longitude.degrees - sun.longitude.degrees) % 360.0
