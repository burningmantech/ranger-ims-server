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
    "MultiStorage",
]

from hashlib import sha1 as etag_hash

from twisted.logger import Logger
from twisted.python.filepath import UnlistableError

from .model import IncidentState, InvalidDataError
from .json import (
    incidentAsJSON, incidentFromJSON, textFromJSON, jsonFromFile,
    rfc3339AsDateTime
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
    Back-end storage (read-only).
    """

    log = Logger()


    def __init__(self, path):
        self.path = path
        self._incidentETags = {}
        self._locations = None
        self.log.info("New data store: {store}", store=self)


    def __repr__(self):
        return "{self.__class__.__name__}({self.path})".format(self=self)


    def _openIncident(self, number, mode):
        incidentFP = self.path.child(unicode(number))
        try:
            incidentFH = incidentFP.open(mode)
        except (IOError, OSError):
            raise NoSuchIncidentError(number)
        return incidentFH


    def readIncidentWithNumberRaw(self, number):
        handle = self._openIncident(number, "r")
        try:
            jsonText = handle.read()
        finally:
            handle.close()
        return jsonText


    def readIncidentWithNumber(self, number):
        handle = self._openIncident(number, "r")
        try:
            json = jsonFromFile(handle)
            incident = incidentFromJSON(json, number=number, validate=False)
        finally:
            handle.close()

        # Do pre-validation cleanup here, for compatibility with older data.
        ims2014Cleanup(incident)

        try:
            incident.validate()
        except InvalidDataError as e:
            self.log.error(
                "Unable to read incident #{number}: {error}",
                number=number, error=e
            )
            raise

        return incident


    def etagForIncidentWithNumber(self, number):
        if number in self._incidentETags:
            return self._incidentETags[number]

        data = self.readIncidentWithNumberRaw(number)
        etag = etag_hash(data).hexdigest()

        if etag:
            self._incidentETags[number] = etag
            return etag
        else:
            raise StorageError(
                "Unable to determine etag for incident {0}".format(number)
            )


    def _listIncidents(self):
        try:
            for child in self.path.children():
                name = child.basename()
                if name.startswith(u"."):
                    continue
                try:
                    number = int(name)
                except ValueError:
                    self.log.error(
                        "Invalid filename in data store: {name}",
                        name=name
                    )
                    continue

                yield number
        except UnlistableError:
            pass


    def listIncidents(self):
        """
        @return: number and etag for each incident in the store.
        @rtype: iterable of (L{int}, L{bytes})
        """
        if not hasattr(self, "_incidents"):
            incidents = {}
            for number in self._listIncidents():
                # Here we cache that the number exists, but not the incident
                # itself.
                incidents[number] = None
            self._incidents = incidents

        for number in self._incidents:
            yield (number, self.etagForIncidentWithNumber(number))


    @property
    def _maxIncidentNumber(self):
        """
        @return: the maximum incident number.
        @rtype: iterable of (L{str}, L{str})
        """
        if not hasattr(self, "_maxIncidentNumber_"):
            max = 0
            for number, etag in self.listIncidents():
                if number > max:
                    max = number
            self._maxIncidentNumber_ = max

        return self._maxIncidentNumber_


    @_maxIncidentNumber.setter
    def _maxIncidentNumber(self, value):
        assert value > self._maxIncidentNumber
        self._maxIncidentNumber_ = value


    def locations(self):
        """
        @return: all known locations.
        @rtype: iterable of L{Location}
        """
        if self._locations is None:
            def locations():
                for (number, etag) in self.listIncidents():
                    incident = self.readIncidentWithNumber(number)
                    location = incident.location

                    if location is not None:
                        yield location

            self._locations = frozenset(locations())

        return self._locations


    def searchIncidents(
        self,
        terms=(),
        showClosed=False,
        since=None,
        until=None,
    ):
        """
        Search all incidents.

        @param terms: Search terms.
            Filter out incidents that do not match every given search term.
        @type terms: iterable of L{unicode}

        @param showClosed: Whether to include closed incidents in result.
        @type showClosed: L{bool}

        @param since: Filter out incidents not edited after a given time.
        @type since: L{datetime.datetime}

        @param until: Filter out incidents not edited prior to a given time.
        @type until: L{datetime.datetime}

        @return: number and etag for each incident in the store.
        @rtype: iterable of (L{int}, L{bytes})
        """
        # log.msg("Searching for {0!r}, closed={1}".format(terms, showClosed))

        #
        # Brute force implementation for now.
        #

        def searchStringsFromIncident(incident):
            yield str(incident.number)

            #
            # Report entries contain all of the below text (via system
            # reports), so there's no need to search these as well...
            #
            # yield incident.summary
            # yield incident.location.name
            # yield incident.location.address
            # for incidentType in incident.incidentTypes:
            #     yield incidentType
            # for ranger in incident.rangers:
            #     yield ranger.handle

            for entry in incident.reportEntries:
                yield entry.text

        def inTimeBounds(when):
            if since is not None and when < since:
                return False
            if until is not None and when > until:
                return False
            return True

        for (number, etag) in self.listIncidents():
            incident = self.readIncidentWithNumber(number)

            #
            # Filter out closed incidents if appropriate
            #
            if not showClosed and incident.state == IncidentState.closed:
                continue

            #
            # Filter out incidents outside of the given time range
            #
            if since is not None or until is not None:
                for entry in incident.reportEntries:
                    if inTimeBounds(entry.created):
                        break
                else:
                    continue

            #
            # Filter out incidents that don't match the given search terms
            #

            for term in terms:
                for string in searchStringsFromIncident(incident):
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


    def _acl(self, name):
        fp = self.path.child(".{}.txt".format(name))
        try:
            return (uid.strip() for uid in fp.open())
        except (IOError, OSError):
            self.log.debug("Unable to open ACL: {fp.path}", fp=fp)
            return ()


    def readers(self):
        return self._acl(u"readers")


    def writers(self):
        return ()


    def streetsByName(self):
        if not hasattr(self, "_streetsByName"):
            fp = self.path.child(".streets.json")
            try:
                self._streetsByName = jsonFromFile(fp.open())
            except (IOError, OSError):
                self.log.warn("Unable to open streets data: {fp.path}", fp=fp)
                self._streetsByName = {}
            except ValueError as e:
                self.log.error(
                    "Unable to parse streets data: {fp.path}: {error}",
                    fp=fp, error=e,
                )
                self._streetsByName = {}

        return self._streetsByName


    def streetsByID(self):
        if not hasattr(self, "_streetsByID"):
            streetsByName = self.streetsByName()
            self._streetsByID = {v: k for k, v in streetsByName.items()}

        return self._streetsByID



class Storage(ReadOnlyStorage):
    """
    Back-end storage (read-write).
    """

    log = Logger()

    def provision(self):
        if hasattr(self, "_provisioned"):
            return

        if not self.path.exists():
            self.log.info(
                "Creating storage directory: {path}", path=self.path.path
            )
            self.path.createDirectory()
            self.path.restat()

        if not self.path.isdir():
            raise StorageError(
                "Storage location must be a directory: {0}"
                .format(self.path)
            )

        self._provisioned = True


    def _writeIncidentText(self, number, text):
        incidentFH = self._openIncident(number, "w")
        try:
            incidentFH.write(text)
        finally:
            incidentFH.close()


    def writeIncident(self, incident):
        incident.validate()

        self.provision()

        number = incident.number
        json = incidentAsJSON(incident)
        text = textFromJSON(json)

        self._writeIncidentText(number, text)

        # Clear the cached etag
        if number in self._incidentETags:
            del self._incidentETags[number]

        if hasattr(self, "_incidents"):
            self._incidents[number] = None

        self._locations = None

        if number > self._maxIncidentNumber:
            raise AssertionError(
                "Unallocated incident number: {} > {}"
                .format(number, self._maxIncidentNumber)
            )
            self._maxIncidentNumber = number


    def nextIncidentNumber(self):
        self.provision()
        self._maxIncidentNumber += 1
        return self._maxIncidentNumber


    def writers(self):
        return self._acl(u"writers")



class MultiStorage(object):
    """
    Container for multiple storages.
    """

    def __init__(self, path, readOnly=False):
        self.path = path
        self.readOnly = readOnly
        self.stores = {}


    def __getitem__(self, name):
        try:
            # Try returning cached value
            return self.stores[name]

        except KeyError:
            if not name.startswith("."):
                # Try opening the named storage
                child = self.path.child(unicode(name))
                if child.isdir:
                    if self.readOnly:
                        storeFactory = ReadOnlyStorage
                    else:
                        storeFactory = Storage
                    store = storeFactory(child)
                    self.stores[name] = store
                    return store

        raise KeyError(name)


    def __contains__(self, name):
        return name in self._events()


    def __len__(self):
        return len(self._events())


    def __iter__(self):
        return iter(self._events())


    iterkeys = __iter__


    def _events(self):
        events = []
        for child in self.path.children():
            name = child.basename()

            if name.startswith("."):
                continue
            if not child.isdir():
                continue

            events.append(name)

        return events



def ims2014Cleanup(incident):
    """
    Clean up 2014 data for compliance with current requirements.
    """
    # 2014 data contains some bugs:
    # * incidents with no created timestamp
    # * report entries with no author

    if incident.reportEntries is not None:
        if incident.created is None:
            for reportEntry in sorted(incident.reportEntries):
                incident.created = reportEntry.created

        for reportEntry in incident.reportEntries:
            if reportEntry.author is None:
                reportEntry.author = u"<unknown>"

    if incident.created is None:
        # Wow MAJOR HAXXOR SKILLZ
        if incident.number == 1158:
            incident.created = rfc3339AsDateTime("2014-09-01T01:06:06Z")

    return incident
