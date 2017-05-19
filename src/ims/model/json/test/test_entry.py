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

from datetime import datetime as DateTime

from hypothesis import given
from hypothesis.extra.datetime import datetimes
from hypothesis.strategies import booleans, text


from .._json import jsonDeserialize, jsonSerialize
from ..._entry import ReportEntry
from ....ext.trial import TestCase


__all__ = ()



class ReportEntrySerializationTests(TestCase):
    """
    Tests for serialization of :class:`ReportEntry`
    """

    @given(datetimes(), text(min_size=1), booleans(), text(min_size=1))
    def test_serialize(
        self, created: DateTime, author: str, automatic: bool, text: str
    ) -> None:
        """
        :func:`jsonSerialize` serializes the given report entry.
        """
        self.assertEqual(
            jsonSerialize(
                ReportEntry(
                    created=created,
                    author=author,
                    automatic=automatic,
                    text=text,
                )
            ),
            dict(
                created=jsonSerialize(created),
                author=jsonSerialize(author),
                system_entry=jsonSerialize(automatic),
                text=jsonSerialize(text),
            )
        )



class ReportEntryDeserializationTests(TestCase):
    """
    Tests for deserialization of :class:`ReportEntry`
    """

    @given(datetimes(), text(min_size=1), booleans(), text(min_size=1))
    def test_deserialize(
        self, created: DateTime, author: str, automatic: bool, text: str
    ) -> None:
        """
        :func:`jsonDeserialize` returns a report entry with the correct data.
        """
        self.assertEqual(
            jsonDeserialize(
                dict(
                    created=jsonSerialize(created),
                    author=jsonSerialize(author),
                    system_entry=jsonSerialize(automatic),
                    text=jsonSerialize(text),
                ),
                ReportEntry
            ),
            ReportEntry(
                created=created,
                author=author,
                automatic=automatic,
                text=text,
            )
        )
