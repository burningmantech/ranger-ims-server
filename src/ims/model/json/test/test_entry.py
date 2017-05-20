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
Tests for :mod:`ranger-ims-server.model.json._entry`
"""

from typing import Any, Callable, Dict, Tuple

from hypothesis import given
from hypothesis.extra.datetime import datetimes
from hypothesis.strategies import booleans, composite, text


from .._json import jsonDeserialize, jsonSerialize
from ..._entry import ReportEntry
from ....ext.trial import TestCase


__all__ = ()


EntryAndJSON = Tuple[ReportEntry, Dict[str, Any]]


@composite
def entryAndJSON(draw: Callable) -> EntryAndJSON:
    created   = draw(datetimes())
    author    = draw(text(min_size=1))
    automatic = draw(booleans())
    entryText = draw(text(min_size=1))

    entry = ReportEntry(
        created=created, author=author, automatic=automatic, text=entryText
    )

    json = dict(
        created=jsonSerialize(created),
        author=jsonSerialize(author),
        system_entry=jsonSerialize(automatic),
        text=jsonSerialize(entryText),
    )

    return (entry, json)



class ReportEntrySerializationTests(TestCase):
    """
    Tests for serialization of :class:`ReportEntry`
    """

    @given(entryAndJSON())
    def test_serialize(self, entryAndJSON: EntryAndJSON) -> None:
        """
        :func:`jsonSerialize` serializes the given report entry.
        """
        entry, json = entryAndJSON

        self.assertEqual(jsonSerialize(entry), json)



class ReportEntryDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`ReportEntry`
    """

    @given(entryAndJSON())
    def test_deserialize(self, entryAndJSON: EntryAndJSON) -> None:
        """
        :func:`jsonDeserialize` returns a report entry with the correct data.
        """
        entry, json = entryAndJSON

        self.assertEqual(jsonDeserialize(json, ReportEntry), entry)
