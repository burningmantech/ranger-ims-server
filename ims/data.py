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
    # "Shift",
]

from functools import total_ordering
from datetime import datetime as DateTime  # , timedelta as TimeDelta

from .tz import utcNow

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
            u"{self.number}: {summary}"
            .format(self=self, summary=self.summaryFromReport())
            .encode("utf-8")
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
        if self.rangers is None:
            raise InvalidDataError("Rangers may not be None.")

        for ranger in self.rangers:
            ranger.validate()

        if self.location is not None:
            self.location.validate()

        if self.incident_types is not None:
            for incident_type in self.incident_types:
                if type(incident_type) is not unicode:
                    raise InvalidDataError(
                        "Incident type must be unicode, not {0!r}"
                        .format(incident_type)
                    )

        if (
            self.summary is not None and
            type(self.summary) is not unicode
        ):
            raise InvalidDataError(
                "Incident summary must be unicode, not {0!r}"
                .format(self.summary)
            )

        if self.report_entries is not None:
            for report_entry in self.report_entries:
                report_entry.validate()

        if (
            self.created is not None and
            type(self.created) is not DateTime
        ):
            raise InvalidDataError(
                "Incident created date must be a DateTime, not {0!r}"
                .format(self.created)
            )

        if (
            self.state is not None and
            self.state not in IncidentState.iterconstants()
        ):
            raise InvalidDataError(
                "Incident state date must be an IncidentState, not {0!r}"
                .format(self.state)
            )

        if type(self.priority) is not int:
            raise InvalidDataError(
                "Incident priority must be an int, not {0!r}"
                .format(self.priority)
            )

        if not 1 <= self.priority <= 5:
            raise InvalidDataError(
                "Incident priority must be an int from 1 to 5, not {0!r}"
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
        if created is None:
            created = utcNow()

        assert text is not None, "ReportEntry text may not be None"

        self.author       = author
        self.text         = text
        self.created      = created
        self.system_entry = bool(system_entry)


    def __str__(self):
        if self.system_entry:
            prefix = u"*"
        else:
            prefix = u""

        return (
            u"{prefix}{self.author}@{self.created}: {self.text}"
            .format(self=self, prefix=prefix)
            .encode("utf-8")
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
        if self.author is not None and type(self.author) is not unicode:
            raise InvalidDataError(
                "Report entry author must be unicode, not {0!r}"
                .format(self.author)
            )

        if type(self.text) is not unicode:
            raise InvalidDataError(
                "Report entry text must be unicode, not {0!r}"
                .format(self.text)
            )

        if type(self.created) is not DateTime:
            raise InvalidDataError(
                "Report entry created date must be a DateTime, not {0!r}"
                .format(self.created)
            )



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

        if not handle:
            raise InvalidDataError("Ranger handle required.")

        self.handle = handle
        self.name   = name
        self.status = status


    def __str__(self):
        return (
            u"{self.handle} ({self.name})"
            .format(self=self).encode("utf-8")
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
        if type(self.handle) is not unicode:
            raise InvalidDataError(
                "Ranger handle must be unicode, not {0!r}".format(self.handle)
            )

        if self.name is not None and type(self.name) is not unicode:
            raise InvalidDataError(
                "Ranger name must be unicode, not {0!r}".format(self.name)
            )

        if self.status is not None and type(self.status) is not unicode:
            raise InvalidDataError(
                "Ranger status must be unicode, not {0!r}".format(self.status)
            )



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
                    u"{self.name} ({self.address})"
                    .format(self=self).encode("utf-8")
                )
            else:
                return u"{self.name}".format(self=self).encode("utf-8")
        else:
            if self.address:
                return u"({self.address})".format(self=self).encode("utf-8")
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
        if self.name and type(self.name) is not unicode:
            raise InvalidDataError(
                "Location name must be unicode, not {0!r}"
                .format(self.name)
            )

        if self.address and type(self.address) is not unicode:
            raise InvalidDataError(
                "Location address must be unicode, not {0!r}"
                .format(self.address)
            )



# class Shift(object):
#     @classmethod
#     def from_datetime(cls, position, datetime):
#         """
#         Create a shift from a datetime.

#         @param position: a L{Values} container corresponding to the
#             position the shift is for.

#         @param datetime: a L{DateTime} during the shift.


#         """
#         return cls(
#             position=position,
#             date=datetime.date(),
#             name=position.shiftForTime(datetime.time()),
#         )


#     def __init__(self, position, date, time=None, name=None):
#         """
#         One or both of C{time} and C{name} are required.  If both are
#         provided, they must match (meaning C{time == name.value}).

#         @param position: a L{Values} container corresponding to the
#             position the shift is for.

#         @param date: the L{Date} for the shift.

#         @param time: the L{Time} for the shift.

#         @param name: the L{ValueConstant} from the C{position}
#             container corresponding to the time of the shift.
#         """
#         if time is None:
#             if name is None:
#                 raise ValueError("Both time and name may not be None.")
#             else:
#                 time = name.value

#         if name is None:
#             name = position.lookupByValue(time)
#         elif name.value != time:
#             raise ValueError(
#                 "time and name do not match: {0} != {1}"
#                 .format(time, name)
#             )

#         self.position = position
#         self.start = DateTime(
#             year=date.year,
#             month=date.month,
#             day=date.day,
#             hour=time.hour,
#         )
#         self.name = name


#     def __hash__(self):
#         return hash((self.position, self.name))


#     def __eq__(self, other):
#         return (
#             self.position == other.position and
#             self.start == other.start
#         )


#     def __lt__(self, other):
#         if not isinstance(other, Shift):
#             return NotImplemented
#         return self.start < other.start


#     def __le__(self, other):
#         if not isinstance(other, Shift):
#             return NotImplemented
#         return self.start <= other.start


#     def __gt__(self, other):
#         if not isinstance(other, Shift):
#             return NotImplemented
#         return self.start > other.start


#     def __ge__(self, other):
#         if not isinstance(other, Shift):
#             return NotImplemented
#         return self.start >= other.start


#     def __str__(self):
#         return (
#             u"{self.start:%y-%m-%d %a} {self.name.name}"
#             .format(self=self).encode("utf-8")
#         )


#     @property
#     def end(self):
#         return (self.start.time() + TimeDelta(hours=self.position.length))


#     def next_shift(self):
#         return self.__class__(
#             position=self.position,
#             date=self.start.date(),
#             time=self.end,
#         )
