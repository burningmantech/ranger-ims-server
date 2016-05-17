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
IMS data model
"""

__all__ = [
    "IncidentState",
    "IncidentType",
    "InvalidDataError",
    "Incident",
    "ReportEntry",
    "Ranger",
    "Location",
    "Address",
    "TextOnlyAddress",
    "RodGarettAddress",
    "concentricStreetIDByName",
    "concentricStreetNameByID",
]

from functools import total_ordering
from datetime import datetime as DateTime  # , timedelta as TimeDelta

from .tz import utcNow
from ._streets import (
    concentricStreetIDByName, concentricStreetNameByID
)

from twisted.python.constants import (
    Names, NamedConstant, Values, ValueConstant
)



#
# Constants
#

class IncidentState(Names):
    """
    Incident states.  Values are corresponding L{Incident} attribute names.
    """

    new        = NamedConstant()
    on_hold    = NamedConstant()
    dispatched = NamedConstant()
    on_scene   = NamedConstant()
    closed     = NamedConstant()


    @classmethod
    def describe(cls, value):
        """
        Describe a constant as a human-readable string.

        @param value: An L{IncidentState} constant.
        @type constant: L{NamedConstant}

        @return: A string description of C{value}.
        @rtype: L{unicode}
        """
        return {
            cls.new: u"New",
            cls.on_hold: u"On Hold",
            cls.dispatched: u"Dispatched",
            cls.on_scene: u"On Scene",
            cls.closed: u"Closed",
        }[value]


    @classmethod
    def states_prior_to(cls, state):
        for s in cls.iterconstants():
            if s is state:
                break
            yield s


    @classmethod
    def states_following(cls, state):
        states = cls.iterconstants()

        for s in states:
            if s is state:
                break

        for s in states:
            yield s



class IncidentType(Values):
    """
    Non-exhautive set of constants for incident types; only incident types
    known to (that is: used by) the software need to be here.
    """

    Admin = ValueConstant(u"Admin")
    Junk  = ValueConstant(u"Junk")



#
# Exceptions
#

class InvalidDataError(ValueError):
    """
    Invalid data
    """



#
# Data Model
#

def _validateIsInstance(name, obj, typeSpec, optional=False, recurse=False):
    if obj is None:
        if optional:
            return
        else:
            raise InvalidDataError("{} is required".format(name))

    if isinstance(obj, typeSpec):
        if recurse:
            obj.validate()
        return

    raise InvalidDataError(
        "{} must be a {}, not {!r}".format(name, typeSpec, obj)
    )


# def _validateIsContant(obj, container, optional=False):



@total_ordering
class Incident(object):
    """
    Incident.
    This object contains all relevant data pertaining to an incident.
    """

    # Note: default values for incident properties need to be None, so that
    # "partial" incidents can be created to describe an update to an incident.
    # In that case, we need to distinguish non-provided data from empty data.
    def __init__(
        self,
        number,
        priority=None,
        summary=None,
        location=None,
        rangers=None,
        incident_types=None,
        report_entries=None,
        created=None, state=None,
    ):
        """
        @param number: The incident's identifying number.
        @type number: L{int}

        @param priority: The priority for the incident.
        @type priority: L{int}

        @param summary: The incident's summary.
        @type summary: L{unicode}

        @param location: The location associated with the incident.
        @type location: L{Location}

        @param rangers: The Rangers associated with the incident.
        @type rangers: iterable of L{Ranger}

        @param incident_types: The incident types associated with the incident.
        @type incident_types: iterable of L{unicode}

        @param report_entries: The report entries associated with the incident.
        @type report_entries: iterable of L{ReportEntry}

        @param created: The created time for the incident.
        @type created: L{DateTime}

        @param state: The state of the incident.
        @type state: L{IncidentState}
        """
        if type(number) is not int:
            raise InvalidDataError(
                "Incident number must be an int, not "
                "({n.__class__.__name__}){n}"
                .format(n=number)
            )

        if number < 0:
            raise InvalidDataError(
                "Incident number must be whole, not {n}".format(n=number)
            )

        if rangers is not None:
            rangers = frozenset(rangers)

        if incident_types is not None:
            incident_types = frozenset(incident_types)

        if report_entries is not None:
            report_entries = tuple(sorted(report_entries))

        self.number         = number
        self.priority       = priority
        self.summary        = summary
        self.location       = location
        self.rangers        = rangers
        self.incident_types = incident_types
        self.report_entries = report_entries
        self.created        = created
        self.state          = state


    def __str__(self):
        return (
            "{self.number}: {summary}".format(
                self=self,
                summary=self.summaryFromReport().encode("utf-8"),
            )
        )


    def __repr__(self):
        return (
            "{self.__class__.__name__}("
            "number={self.number!r},"
            "rangers={self.rangers!r},"
            "location={self.location!r},"
            "incident_types={self.incident_types!r},"
            "summary={self.summary!r},"
            "report_entries={self.report_entries!r},"
            "created={self.created!r},"
            "state={self.state!r},"
            "priority={self.priority!r})"
            .format(self=self)
        )


    def __hash__(self):
        return hash(self.number)


    def __eq__(self, other):
        if isinstance(other, Incident):
            return (
                self.number == other.number and
                self.rangers == other.rangers and
                self.location == other.location and
                self.incident_types == other.incident_types and
                self.summary == other.summary and
                self.report_entries == other.report_entries and
                self.created == other.created and
                self.state == other.state and
                self.priority == other.priority
            )
        return NotImplemented


    def __lt__(self, other):
        if isinstance(other, Incident):
            return self.number < other.number

        return NotImplemented


    def summaryFromReport(self):
        """
        Generate a summary.  This uses the C{summary} attribute if it is not
        C{None} or empty; otherwise, it uses the first line of the first
        report entry,

        @return: The incident summary.
        @rtype: L{unicode}
        """
        if self.summary:
            return self.summary

        if self.report_entries is not None:
            for entry in self.report_entries:
                return entry.text.split("\n")[0]

        return ""


    def validate(self):
        """
        Validate this incident.

        @raise: L{InvalidDataError} if the incident does not validate.
        """
        if self.rangers is not None:
            for ranger in self.rangers:
                _validateIsInstance("Ranger", ranger, Ranger, recurse=True)

        _validateIsInstance(
            "location", self.location, Location, optional=True, recurse=True
        )

        if self.incident_types is not None:
            for incident_type in self.incident_types:
                _validateIsInstance("incident type", incident_type, unicode)

        _validateIsInstance("summary", self.summary, unicode, optional=True)

        if self.report_entries is not None:
            for report_entry in self.report_entries:
                _validateIsInstance(
                    "report entry", report_entry, ReportEntry, recurse=True
                )

        _validateIsInstance("created", self.created, DateTime, optional=False)

        if (
            self.state is not None and
            self.state not in IncidentState.iterconstants()
        ):
            raise InvalidDataError(
                "state must be a {}, not {!r}"
                .format(IncidentState, self.state)
            )

        _validateIsInstance("priority", self.priority, int)

        if not 1 <= self.priority <= 5:
            raise InvalidDataError(
                "priority must be an int from 1 to 5, not {!r}"
                .format(self.priority)
            )

        return self



@total_ordering
class ReportEntry(object):
    """
    Report entry.
    This object contains text entered into an incident.
    """

    def __init__(self, author, text, created=None, system_entry=False):
        """
        @param author: The person who created/entered the entry.
        @type author: L{unicode}

        @param text: The report entry text.
        @type text: L{unicode}

        @param created: The created time of the report entry.
        @type created: L{DateTime}

        @param system_entry: Whether the report entry was created by the
            IMS software (as opposed to by a user).
        @type system_entry: L{bool}
        """
        # FIXME: raise instead?
        if created is None:
            created = utcNow()

        self.author       = author
        self.text         = text
        self.created      = created
        self.system_entry = bool(system_entry)


    def __str__(self):
        if self.system_entry:
            prefix = "*"
        else:
            prefix = ""

        return (
            "{prefix}{self.author}@{self.created}: {self.text}".format(
                self=self, prefix=prefix
            )
        )


    def __repr__(self):
        if self.system_entry:
            star = "*"
        else:
            star = ""

        return (
            "{self.__class__.__name__}("
            "author={self.author!r}{star},"
            "text={self.text!r},"
            "created={self.created!r})"
            .format(self=self, star=star)
        )


    def __hash__(self):
        return hash((
            self.author,
            self.text,
            self.created,
            self.system_entry,
        ))


    def __eq__(self, other):
        if isinstance(other, ReportEntry):
            return (
                self.created == other.created and
                self.system_entry == other.system_entry and
                self.author == other.author and
                self.text == other.text
            )

        return NotImplemented


    def __lt__(self, other):
        if isinstance(other, ReportEntry):
            if self.created != other.created:
                return self.created < other.created

            if self.system_entry:
                return not other.system_entry

            if self.author != other.author:
                return self.author < other.author

            return self.text < other.text

        return NotImplemented


    def validate(self):
        """
        Validate this report entry.

        @raise: L{InvalidDataError} if the report entry does not validate.
        """
        _validateIsInstance("author", self.author, unicode)
        _validateIsInstance("text", self.text, unicode)
        _validateIsInstance("created", self.created, DateTime)



@total_ordering
class Ranger(object):
    """
    Ranger
    """

    def __init__(self, handle, name, status):
        """
        @param handle: The Ranger's handle.
        @type handle: L{unicode}

        @param name: The Ranger's name.
        @type name: L{unicode}

        @param status: The Ranger's status.
        @type status: L{unicode}
        """
        self.handle = handle
        self.name   = name
        self.status = status


    def __str__(self):
        return (
            u"{self.handle} ({self.name})".format(self=self).encode("utf-8")
        )


    def __repr__(self):
        return (
            "{self.__class__.__name__}("
            "handle={self.handle!r},"
            "name={self.name!r},"
            "status={self.status!r})"
            .format(self=self)
        )


    def __hash__(self):
        return hash(self.handle)


    def __eq__(self, other):
        if isinstance(other, Ranger):
            return self.handle == other.handle

        return NotImplemented


    def __lt__(self, other):
        if isinstance(other, Ranger):
            return self.handle < other.handle

        return NotImplemented


    def validate(self):
        """
        Validate this Ranger.

        @raise: L{InvalidDataError} if the Ranger does not validate.
        """
        _validateIsInstance("handle", self.handle, unicode)

        if not self.handle:
            raise InvalidDataError("Ranger handle may not be empty")

        _validateIsInstance("name", self.name, unicode, optional=True)
        _validateIsInstance("status", self.status, unicode, optional=True)



class Location(object):
    """
    Location
    """

    def __init__(self, name=None, address=None):
        """
        @param name: The location's name.
        @type name: L{unicode}

        @param address: The location's address.
        @type address: L{unicode}
        """
        self.name    = name
        self.address = address


    def __str__(self):
        if self.name:
            if self.address:
                return (
                    "{name} ({self.address})".format(
                        self=self,
                        name=self.name.encode("utf-8"),
                    )
                )
            else:
                return self.name.encode("utf-8")
        else:
            if self.address:
                return "({self.address})".format(self=self)
            else:
                return ""


    def __repr__(self):
        return (
            "{self.__class__.__name__}("
            "name={self.name!r},"
            "address={self.address!r})"
            .format(self=self)
        )


    def __hash__(self):
        return hash((
            self.name,
            self.address,
        ))


    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.name == other.name and
                self.address == other.address
            )
        elif other is None:
            return self.name is None and self.address is None

        return NotImplemented


    def __lt__(self, other):
        if isinstance(other, Location):
            if self.name != other.name:
                return self.name < other.name
            if self.address != other.address:
                return self.address < other.address

        return NotImplemented


    def validate(self):
        """
        Validate this location.

        @raise: L{InvalidDataError} if the location does not validate.
        """
        _validateIsInstance("name", self.name, unicode, optional=True)
        _validateIsInstance(
            "address", self.address, Address, optional=True, recurse=True
        )



class Address(object):
    """
    Location address
    """



@total_ordering
class TextOnlyAddress(Address):
    """
    Address described by free-form text.
    """

    def __init__(self, description=None):
        """
        @param description: The address' radial minute.
        @type description: L{unicode}
        """
        self.description = description


    def __str__(self):
        if self.description is None:
            return ""
        return self.description.encode("utf-8")


    def __repr__(self):
        return (
            "{self.__class__.__name__}(description={self.description!r})"
            .format(self=self)
        )


    def __hash__(self):
        return hash(self.description)


    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.description == other.description
        elif other is None:
            return self.description is None

        return NotImplemented


    def __lt__(self, other):
        if isinstance(other, Location):
            if self.description != other.description:
                return self.description < other.description

        return NotImplemented


    def validate(self):
        """
        Validate this location.

        @raise: L{InvalidDataError} if the location does not validate.
        """
        _validateIsInstance("description", self.description, unicode)



@total_ordering
class RodGarettAddress(Address):
    """
    Address at concentric and radial streets, as per Rod Garett's design for
    Black Rock City.
    """

    def __init__(
        self,
        concentric=None, radialHour=None, radialMinute=None,
        description=None,
    ):
        """
        @param concentric: The address' concentric street number, starting
            from C{0}.
        @type concentric: L{int}

        @param radialHour: The address' radial hour.
        @type radialHour: L{int}

        @param radialMinute: The address' radial minute.
        @type radialMinute: L{int}

        @param description: The address' radial minute.
        @type description: L{unicode}
        """
        self.concentric   = concentric
        self.radialHour   = radialHour
        self.radialMinute = radialMinute
        self.description  = description


    def __str__(self):
        if self.concentric is None:
            concentric = u""
        else:
            concentric = self.concentric

        if self.radialHour is None and self.radialMinute is None:
            radial = u""
        else:
            if self.radialHour is None:
                radialHour = u"?"
            else:
                radialHour = self.radialHour

            if self.radialMinute is None:
                radialMinute = u"?"
            else:
                radialMinute = self.radialMinute
            radial = u"{}:{}".format(radialHour, radialMinute)

        if not concentric or not radial:
            at = u""
        else:
            at = u"@"

        if self.description is None:
            description = u""
        else:
            description = u", {}".format(self.description)

        return (
            u"{concentric}{at}{radial}{description}"
            .format(
                self=self,
                concentric=concentric,
                at=at,
                radial=radial,
                description=description,
            ).encode("utf-8")
        )


    def __repr__(self):
        return (
            "{self.__class__.__name__}("
            "concentric={self.concentric!r},"
            "radialHour={self.radialHour!r},"
            "radialMinute={self.radialMinute!r},"
            "description={self.description!r})"
            .format(self=self)
        )


    def __hash__(self):
        return hash((
            self.concentric,
            self.radialHour,
            self.radialMinute,
            self.description,
        ))


    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.concentric   == other.concentric and
                self.radialHour   == other.radialHour and
                self.radialMinute == other.radialMinute and
                self.description  == other.description
            )
        elif other is None:
            return (
                self.concentric is None and
                self.radialHour is None and
                self.radialMinute is None and
                self.description
            )

        return NotImplemented


    def __lt__(self, other):
        if isinstance(other, Location):
            if self.concentric != other.concentric:
                return self.concentric < other.concentric
            if self.radialHour != other.radialHour:
                return self.radialHour < other.radialHour
            if self.radialMinute != other.radialMinute:
                return self.radialMinute < other.radialMinute
            if self.description != other.description:
                return self.description < other.description

        return NotImplemented


    def validate(self):
        """
        Validate this location.

        @raise: L{InvalidDataError} if the location does not validate.
        """
        _validateIsInstance(
            "concentric", self.concentric, int, optional=True
        )
        _validateIsInstance(
            "radialHour", self.radialHour, int, optional=True
        )
        _validateIsInstance(
            "radialMinute", self.radialMinute, int, optional=True
        )
        _validateIsInstance(
            "description", self.description, unicode, optional=True
        )

        if self.concentric is not None and self.concentric < 0:
            raise InvalidDataError(
                "Concentric street number must be non-negative, not {!r}"
                .format(self.concentric)
            )

        if self.radialHour is not None:
            if not 1 <= self.radialHour <= 12:
                raise InvalidDataError(
                    "Radial hour must be 1-12, not {!r}"
                    .format(self.radialHour)
                )

        if self.radialMinute is not None:
            if not 0 <= self.radialMinute < 60:
                raise InvalidDataError(
                    "Radial minute must be 0-59, not {!r}"
                    .format(self.radialMinute)
                )

