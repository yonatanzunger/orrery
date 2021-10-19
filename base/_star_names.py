import logging
import os
import re
import shutil
from typing import Dict, Iterator, List, Optional, Tuple

from github import Github, GithubException
from skyfield.api import Loader
from skyfield.data.stellarium import \
    StarName  # Not parse_star_names, it's broken.


class StarNames(object):
    def __init__(self, load: Loader) -> None:
        self.load = load
        self._byCulture: Dict[str, Dict[str, int]] = {}
        self._allStars: Dict[str, int] = {}
        self._byHip: Dict[int, Dict[str, str]] = {}
        self.reload()

    def find(self, name: str, culture: Optional[str] = None) -> int:
        """Return the Hipparcos catalog number of a named star."""
        if culture is not None:
            return self._byCulture[culture][name]
        return self._allStars[name]

    def allNames(self, index: int) -> Dict[str, str]:
        """Given a Hipparcos index, return the set of {culture, name} pairs for this star."""
        return self._byHip[index]

    def cultures(self) -> Tuple[str, ...]:
        return tuple(self._byCulture.keys())

    def reload(self, forceRefresh: bool = False) -> None:
        self._refresh(force=forceRefresh)
        self._byCulture = {}
        self._allStars = {}
        self._byHip = {}

        logging.info("Loading star names data")
        for file in os.scandir(self._dirname):
            if not file.is_file() or not file.name.endswith(".fab"):
                continue
            culture = file.name[:-4]
            if culture not in self._byCulture:
                self._byCulture[culture] = {}
            for star in self._parseFAB(file.path):
                self._byCulture[culture][star.name] = star.hip
                self._allStars[star.name] = star.hip
                if star.hip not in self._byHip:
                    self._byHip[star.hip] = {"hip": f"HIP{star.hip}"}
                self._byHip[star.hip][culture] = star.name

        logging.info(
            f"Loaded {len(self._allStars)} star names for {len(self._byCulture)} cultures"
        )

    _STAR_NAMES_DIR = "star_names"
    _COMPLETE_FILE = "COMPLETE"

    @property
    def _dirname(self) -> str:
        return self.load.path_to(self._STAR_NAMES_DIR)

    def _path(self, name: str) -> str:
        return self.load.path_to(f"{self._STAR_NAMES_DIR}/{name}")

    def _refresh(self, force: bool = False) -> None:
        if not force and os.path.exists(self._path(self._COMPLETE_FILE)):
            return

        logging.info("Refreshing star name data")
        shutil.rmtree(self._dirname, ignore_errors=True)
        os.makedirs(self._dirname)

        cultures: List[str] = []
        stellarium = Github().get_repo("Stellarium/stellarium")
        # The skycultures directory contains all of our cultures.
        for culture in stellarium.get_contents("skycultures"):
            if culture.type != "dir":
                continue
            try:
                starNames = stellarium.get_contents(culture.path + "/star_names.fab")
            except GithubException:
                logging.warning(f"No star names found for culture {culture.name}")
                continue

            cultures.append(culture.name)
            with open(self._path(culture.name + ".fab"), "wb") as output:
                output.write(starNames.decoded_content)

        with open(self._path(self._COMPLETE_FILE), "wb") as output:
            output.write(b"")

        logging.info(f"Finished downloading star names for cultures: {cultures}")

    def _parseFAB(self, filename: str) -> Iterator[StarName]:
        with open(filename, "rt", encoding="utf8") as data:
            for line in data:
                match = re.match('([0-9]+)\|_\("([^"]+)"\)', line.strip())
                if match:
                    yield StarName(name=match[2], hip=int(match[1]))
