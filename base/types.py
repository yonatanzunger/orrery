from typing import Union

from skyfield.starlib import Star
from skyfield.vectorlib import VectorFunction

# In skyfield, you can actually observe anything that impolements _observe_from_bcrs, but (dammit
# old code) there's no sane type signature for that.
Observable = Union[VectorFunction, Star]
