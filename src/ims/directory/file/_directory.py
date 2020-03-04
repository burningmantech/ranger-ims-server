##
# See the file COPYRIGHT for copyright information.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##

"""
Incident Management System directory service integration.
"""

from time import time
from pathlib import Path
from typing import Any, ClassVar, Iterable, Mapping, Optional, Sequence

from attr import Factory, attrs

from twisted.logger import Logger

from yaml import safe_load as parseYAML

from ims.model import Position, Ranger, RangerStatus

from .._directory import DirectoryError, IMSDirectory, IMSUser, RangerDirectory


__all__ = ()


def statusFromID(strValue: str) -> RangerStatus:
    return {
        "active": RangerStatus.active,
        "inactive": RangerStatus.inactive,
        "vintage": RangerStatus.vintage,
    }.get(strValue, RangerStatus.other)


def rangersFromMappings(
    sequence: Iterable[Mapping[str, Any]]
) -> Iterable[Ranger]:
    if type(sequence) is not list:
        raise DirectoryError(f"Rangers must be sequence: {sequence!r}")

    for mapping in sequence:
        try:
            yield rangerFromMapping(mapping)
        except DirectoryError:
            raise
        except Exception as e:
            raise DirectoryError(f"Unable to parse Ranger records: {e}")


def rangerFromMapping(mapping: Mapping[str, Any]) -> Ranger:
    if type(mapping) is not dict:
        raise DirectoryError(f"Ranger must be mapping: {mapping!r}")

    handle = mapping.get("handle", None)
    if handle is None:
        raise DirectoryError(f"Ranger must have handle: {mapping!r}")
    elif type(handle) is not str:
        raise DirectoryError(f"Ranger handle must be text: {handle!r}")

    name = mapping.get("name", "")
    if type(name) is not str:
        raise DirectoryError(f"Ranger name must be text: {name!r}")

    _status = mapping.get("status", "")
    if type(_status) is not str:
        raise DirectoryError(f"Ranger status must be text: {_status!r}")
    status = statusFromID(_status)

    _email = mapping.get("email", [])
    email: Sequence[str]
    if type(_email) is str:
        email = (_email,)
    elif type(_email) is list:
        for e in _email:
            if type(e) is not str:
                raise DirectoryError(f"Ranger email must be text: {e!r}")
        email = tuple(_email)
    else:
        raise DirectoryError(
            f"Ranger email must be text or sequence of text: {_email!r}"
        )

    enabled = mapping.get("enabled", None)
    if type(enabled) is not bool:
        raise DirectoryError(f"Ranger enabled must be boolean: {enabled!r}")

    password = mapping.get("password", None)
    if password is not None and type(password) is not str:
        raise DirectoryError(f"Ranger password must be text: {password!r}")

    return Ranger(
        handle=handle,
        name=name,
        status=status,
        email=email,
        enabled=enabled,
        directoryID=None,
        password=mapping.get("password", None),
    )


def positionsFromMappings(
    sequence: Iterable[Mapping[str, Any]]
) -> Iterable[Position]:
    if type(sequence) is not list:
        raise DirectoryError(f"Positions must be sequence: {sequence!r}")

    for mapping in sequence:
        try:
            yield positionFromMapping(mapping)
        except DirectoryError:
            raise
        except Exception as e:
            raise DirectoryError(f"Unable to parse position records: {e}")


def positionFromMapping(mapping: Mapping[str, Any]) -> Position:
    if type(mapping) is not dict:
        raise DirectoryError(f"Position must be mapping: {mapping!r}")

    name: Optional[str] = mapping.get("name", None)
    if name is None:
        raise DirectoryError(f"Position must have name: {mapping!r}")
    elif type(name) is not str:
        raise DirectoryError(f"Position name must be text: {name!r}")

    members: Sequence[str] = mapping.get("members", [])
    if type(members) is not list:
        raise DirectoryError(
            f"Position members must be sequence of text: {members!r}"
        )
    for m in members:
        if type(m) is not str:
            raise DirectoryError(f"Position members must be text: {m!r}")

    return Position(name=name, members=frozenset(members))


@attrs(frozen=True, auto_attribs=True, kw_only=True)
class FileDirectory(IMSDirectory):
    """
    IMS directory loaded from a file.
    """

    _log: ClassVar[Logger] = Logger()

    @attrs(frozen=False, auto_attribs=True, kw_only=True, eq=False)
    class _State(object):
        """
        Internal mutable state for :class:`RangerDirectory`.
        """

        directory: RangerDirectory = Factory(
            lambda: RangerDirectory(rangers=(), positions=())
        )
        lastLoadTime = 0.0

    path: Path
    checkInterval = 1.0  # Don't restat the file more often than this (seconds)

    _state: _State = Factory(_State)

    def _reload(self) -> None:
        now = time()
        elapsed = now - self._state.lastLoadTime

        if (
            elapsed >= self.checkInterval
            and self.path.stat().st_mtime > self._state.lastLoadTime
        ):
            self._log.info("Reloading directory file...")
            with self.path.open() as fh:
                yaml = parseYAML(fh)

                schemaVersion = yaml.get("schema")
                if schemaVersion is None:
                    raise DirectoryError("No schema version in YAML file")
                if schemaVersion != 0:
                    raise DirectoryError("Unknown schema version in YAML file")

                rangers = tuple(rangersFromMappings(yaml.get("rangers", ())))
                positions = tuple(
                    positionsFromMappings(yaml.get("positions", ()))
                )

                self._state.directory = RangerDirectory(
                    rangers=rangers, positions=positions
                )

    async def personnel(self) -> Iterable[Ranger]:
        self._reload()
        return await self._state.directory.personnel()

    async def lookupUser(self, searchTerm: str) -> Optional[IMSUser]:
        self._reload()
        return await self._state.directory.lookupUser(searchTerm)
