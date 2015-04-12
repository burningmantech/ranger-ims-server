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
Data store
"""

__all__ = [
    "StorageError",
    "NoSuchIncidentError",
    "ReadOnlyStorage",
    "Storage",
]

from hashlib import sha1 as etag_hash

from twisted.python import log
from twisted.python.filepath import UnlistableError
from .data import IncidentState
from .json import (
    incident_as_json, incident_from_json, json_as_text, json_from_file
)



class StorageError(RuntimeError):
    """
    Storage error.
    """



class NoSuchIncidentError(StorageError):
    """
    No such incident.
    """



class ReadOnlyStorage(object):
    """
    Back-end storage
    """

    def __init__(self, path):
        self.path = path
        self._incident_etags = {}
        self._locations = None
        log.msg("New data store: {0}".format(self))


    def __repr__(self):
        return "{self.__class__.__name__}({self.path})".format(self=self)


    def _open_incident(self, number, mode):
        incident_fp = self.path.child(unicode(number))
        try:
            incident_fh = incident_fp.open(mode)
        except (IOError, OSError):
            raise NoSuchIncidentError(number)
        return incident_fh


    def read_incident_with_number_raw(self, number):
        handle = self._open_incident(number, "r")
        try:
            jsonText = handle.read()
        finally:
            handle.close()
        return jsonText


    def read_incident_with_number(self, number):
        handle = self._open_incident(number, "r")
        try:
            json = json_from_file(handle)
            incident = incident_from_json(json, number=number, validate=False)
        finally:
            handle.close()

        # Do pre-validation cleanup here, for compatibility with older data.
        ims2014Cleanup(incident)

        incident.validate()

        return incident


    def etag_for_incident_with_number(self, number):
        if number in self._incident_etags:
            return self._incident_etags[number]

        data = self.read_incident_with_number_raw(number)
        etag = etag_hash(data).hexdigest()

        if etag:
            self._incident_etags[number] = etag
            return etag
        else:
            raise StorageError(
                "Unable to determine etag for incident {0}".format(number)
            )


    def _list_incidents(self):
        try:
            for child in self.path.children():
                name = child.basename()
                if name.startswith("."):
                    continue
                try:
                    number = int(name)
                except ValueError:
                    log.err(
                        "Invalid filename in data store: {0}"
                        .format(name)
                    )
                    continue

                yield number
        except UnlistableError:
            pass


    def list_incidents(self):
        """
        @return: number and etag for each incident in the store.
        @rtype: iterable of (L{int}, L{bytes})
        """
        if not hasattr(self, "_incidents"):
            incidents = {}
            for number in self._list_incidents():
                # Here we cache that the number exists, but not the incident
                # itself.
                incidents[number] = None
            self._incidents = incidents

        for number in self._incidents:
            yield (number, self.etag_for_incident_with_number(number))


    @property
    def _max_incident_number(self):
        """
        @return: the maximum incident number.
        @rtype: iterable of (L{str}, L{str})
        """
        if not hasattr(self, "_max_incident_number_"):
            max = 0
            for number, etag in self.list_incidents():
                if number > max:
                    max = number
            self._max_incident_number_ = max

        return self._max_incident_number_


    @_max_incident_number.setter
    def _max_incident_number(self, value):
        assert value > self._max_incident_number
        self._max_incident_number_ = value


    def locations(self):
        """
        @return: all known locations.
        @rtype: iterable of L{Location}
        """
        if self._locations is None:
            def locations():
                for (number, etag) in self.list_incidents():
                    incident = self.read_incident_with_number(number)
                    location = incident.location

                    if location is not None:
                        yield location

            self._locations = frozenset(locations())

        return self._locations


    def search_incidents(
        self,
        terms=(),
        show_closed=False,
        since=None,
        until=None,
    ):
        """
        Search all incidents.

        @param terms: Search terms.
            Filter out incidents that do not match every given search term.
        @type terms: iterable of L{unicode}

        @param show_closed: Whether to include closed incidents in result.
        @type show_closed: L{bool}

        @param since: Filter out incidents not edited after a given time.
        @type since: L{datetime.datetime}

        @param until: Filter out incidents not edited prior to a given time.
        @type until: L{datetime.datetime}

        @return: number and etag for each incident in the store.
        @rtype: iterable of (L{int}, L{bytes})
        """
        # log.msg("Searching for {0!r}, closed={1}".format(terms, show_closed))

        #
        # Brute force implementation for now.
        #

        def search_strings_from_incident(incident):
            yield str(incident.number)

            #
            # Report entries contain all of the below text (via system
            # reports), so there's no need to search these as well...
            #
            # yield incident.summary
            # yield incident.location.name
            # yield incident.location.address
            # for incident_type in incident.incident_types:
            #     yield incident_type
            # for ranger in incident.rangers:
            #     yield ranger.handle

            for entry in incident.report_entries:
                yield entry.text

        def in_time_bounds(when):
            if since is not None and when < since:
                return False
            if until is not None and when > until:
                return False
            return True

        for (number, etag) in self.list_incidents():
            incident = self.read_incident_with_number(number)

            #
            # Filter out closed incidents if appropriate
            #
            if not show_closed and incident.state == IncidentState.closed:
                continue

            #
            # Filter out incidents outside of the given time range
            #
            if since is not None or until is not None:
                for entry in incident.report_entries:
                    if in_time_bounds(entry.created):
                        break
                else:
                    continue

            #
            # Filter out incidents that don't match the given search terms
            #

            for term in terms:
                for string in search_strings_from_incident(incident):
                    if string is None:
                        continue
                    if term.lower() in string.lower():
                        # Matched; break out of inner for loop
                        break
                else:
                    # Term didn't match any string; break out of outer for loop
                    break
            else:
                # Matched; yield a value
                yield (number, etag)



class Storage(ReadOnlyStorage):
    def provision(self):
        if hasattr(self, "_provisioned"):
            return

        if not self.path.exists():
            log.msg(
                "Creating storage directory: {0}"
                .format(self.path)
            )
            self.path.createDirectory()
            self.path.restat()

        if not self.path.isdir():
            raise StorageError(
                "Storage location must be a directory: {0}"
                .format(self.path)
            )

        self._provisioned = True


    def _write_incident_text(self, number, text):
        incident_fh = self._open_incident(number, "w")
        try:
            incident_fh.write(text)
        finally:
            incident_fh.close()


    def write_incident(self, incident):
        incident.validate()

        self.provision()

        number = incident.number
        json = incident_as_json(incident)
        text = json_as_text(json)

        self._write_incident_text(number, text)

        # Clear the cached etag
        if number in self._incident_etags:
            del self._incident_etags[number]

        if hasattr(self, "_incidents"):
            self._incidents[number] = None

        self._locations = None

        if number > self._max_incident_number:
            raise AssertionError(
                "Unallocated incident number: {} > {}"
                .format(number, self._max_incident_number)
            )
            self._max_incident_number = number


    def next_incident_number(self):
        self.provision()
        self._max_incident_number += 1
        return self._max_incident_number



def ims2014Cleanup(incident):
    """
    Clean up 2014 data for compliance with current requirements.
    """
    report_entries = list(incident.report_entries)
    for report_entry in report_entries:
        if report_entry.author is None:
            report_entry.author = u"<unknown>"

    return incident
