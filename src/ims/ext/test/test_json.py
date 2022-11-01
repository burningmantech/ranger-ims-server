"""
Tests for :mod:`ranger-ims-server.ext.json`
"""

from collections.abc import Callable
from datetime import date as Date
from datetime import datetime as DateTime
from datetime import timedelta as TimeDelta
from datetime import timezone as TimeZone
from io import BytesIO
from json import JSONDecodeError
from textwrap import dedent
from typing import Any, cast

from hypothesis import given
from hypothesis.strategies import composite, dates
from hypothesis.strategies import datetimes as _datetimes
from hypothesis.strategies import integers

from ..json import (
    dateAsRFC3339Text,
    dateTimeAsRFC3339Text,
    jsonTextFromObject,
    objectFromJSONBytesIO,
    objectFromJSONText,
    rfc3339TextAsDate,
    rfc3339TextAsDateTime,
)
from ..trial import TestCase


__all__ = ()


@composite
def timezones(draw: Callable[..., Any]) -> TimeZone:
    offset = cast(
        int, draw(integers(min_value=-(60 * 24) + 1, max_value=(60 * 24) - 1))
    )
    timeDelta = TimeDelta(minutes=offset)
    timeZone = TimeZone(offset=timeDelta, name=f"{offset}s")
    return timeZone


@composite
def datetimes(draw: Callable[..., Any]) -> DateTime:
    return cast(DateTime, draw(_datetimes(timezones=timezones())))


class JSONEncodingTests(TestCase):
    """
    Tests for :func:`jsonTextFromObject`
    """

    def test_encodeIterables(self) -> None:
        """
        :func:`jsonTextFromObject` encodes iterables other than :class:`list`
        and :class:`tuple`.

        This indirectly tests :class:`config_service.util.json.Encoder`.
        """
        self.assertEqual(jsonTextFromObject(n for n in (1, 2, 3)), "[1,2,3]")

    def test_encodeUnknown(self) -> None:
        """
        :func:`jsonTextFromObject` raises :exc:`TypeError` when given an
        unknown object type.

        This indirectly tests :class:`config_service.util.json.Encoder`.
        """
        self.assertRaises(TypeError, jsonTextFromObject, object())

    def test_jsonTextFromObject_ugly(self) -> None:
        """
        :func:`jsonTextFromObject` encodes JSON without pretty-ness if
        :obj:`pretty` is false.
        """
        obj = dict(x="Hello", y=["one", "two", "three"])

        self.assertEqual(
            objectFromJSONText(jsonTextFromObject(obj, pretty=False)), obj
        )

    def test_jsonTextFromObject_pretty(self) -> None:
        """
        :func:`jsonTextFromObject` encodes JSON with pretty-ness if
        :obj:`pretty` is true.
        """
        obj = dict(x="Hello", y=["one", "two", "three"])

        self.assertEqual(
            jsonTextFromObject(obj, pretty=True),
            dedent(
                """
                {
                  "x": "Hello",
                  "y": [
                    "one",
                    "two",
                    "three"
                  ]
                }
                """
            )[1:-1],
        )


class JSONDecodingTests(TestCase):
    """
    Tests for :func:`objectFromJSONText`
    """

    def test_objectFromJSONText(self) -> None:
        """
        :func:`objectFromJSONText` decodes JSON into POPOs.
        """
        self.assertEqual(
            objectFromJSONText(
                """
                {
                  "x": "Hello",
                  "y": [
                    "one",
                    "two",
                    "three"
                  ]
                }
                """
            ),
            dict(x="Hello", y=["one", "two", "three"]),
        )

    def test_objectFromJSONText_badInput(self) -> None:
        """
        :func:`objectFromJSONText` raises :exc:`JSONDecodeError` then given
        invalid JSON text.
        """
        self.assertRaises(JSONDecodeError, objectFromJSONText, "foo}")

    def test_objectFromJSONBytesIO(self) -> None:
        """
        :func:`objectFromJSONBytesIO` decodes JSON into POPOs.
        """
        self.assertEqual(
            objectFromJSONBytesIO(
                BytesIO(
                    """
                    {
                      "x": "Hello",
                      "y": [
                        "one",
                        "two",
                        "three"
                      ]
                    }
                    """.encode(
                        "ascii"
                    )
                )
            ),
            dict(x="Hello", y=["one", "two", "three"]),
        )

    def test_objectFromJSONBytesIO_badInput(self) -> None:
        """
        :func:`objectFromJSONBytesIO` raises :exc:`JSONDecodeError` then given
        invalid JSON text.
        """
        self.assertRaises(
            JSONDecodeError,
            objectFromJSONBytesIO,
            BytesIO(b"foo}"),
        )


class DateTimeTests(TestCase):
    """
    Test for encoding and decoding of date/time objects.
    """

    @staticmethod
    def dateAsRFC3339Text(date: Date) -> str:
        """
        Convert a :class:`Date` into an RFC 3339 formatted date string.

        :param date: A date to convert.

        :return: An RFC 3339 formatted date string corresponding to
        :obj:`date`.
        """
        return f"{date.year:04d}-{date.month:02d}-{date.day:02d}"

    @staticmethod
    def dateTimeAsRFC3339Text(dateTime: DateTime) -> str:
        """
        Convert a :class:`DateTime` into an RFC 3339 formatted date-time
        string.

        :param datetime: A non-naive :class:`DateTime` to convert.

        :return: An RFC 3339 formatted date-time string corresponding to
            :obj:`datetime`.
        """
        timeZone = cast(TimeZone, dateTime.tzinfo)
        assert timeZone is not None

        offset = cast(TimeDelta, timeZone.utcoffset(dateTime))
        assert offset is not None

        utcOffset = offset.total_seconds()

        if dateTime.microsecond == 0:
            microsecond = ""
        else:
            microsecond = f".{dateTime.microsecond:06d}"

        tzHour = int(utcOffset / 60 / 60)
        tzMinute = int(utcOffset / 60) % 60
        if utcOffset < 0:
            tzSign = "-"
            tzHour *= -1
            tzMinute = (60 - tzMinute) % 60
        else:
            tzSign = "+"

        return (
            f"{dateTime.year:04d}-{dateTime.month:02d}-{dateTime.day:02d}"
            "T"
            f"{dateTime.hour:02d}:{dateTime.minute:02d}:{dateTime.second:02d}"
            f"{microsecond}"
            f"{tzSign}{tzHour:02d}:{tzMinute:02d}"
        )

    @given(dates())
    def test_dateAsRFC3339Text(self, date: Date) -> None:
        """
        :func:`dateAsRFC3339Text` converts a :class:`Date` into a RFC 3339
        formatted date string.
        """
        self.assertEqual(dateAsRFC3339Text(date), self.dateAsRFC3339Text(date))

    @given(dates())
    def test_rfc3339TextAsDate(self, date: Date) -> None:
        """
        :func:`rfc3339TextAsDate` converts a RFC 3339 formatted date string
        into a :class:`Date`.
        """
        self.assertEqual(rfc3339TextAsDate(self.dateAsRFC3339Text(date)), date)

    @given(datetimes())
    def test_dateTimeAsRFC3339Text(self, dateTime: DateTime) -> None:
        """
        :func:`dateTimeAsRFC3339Text` converts a :class:`DateTime` into a RFC
        3339 formatted date string.
        """
        self.assertEqual(
            dateTimeAsRFC3339Text(dateTime),
            self.dateTimeAsRFC3339Text(dateTime),
        )

    @given(datetimes())
    def test_rfc3339TextAsDateTime(self, dateTime: DateTime) -> None:
        """
        :func:`rfc3339TextAsDateTime` converts a RFC 3339 formatted date-time
        string into a :class:`DateTime`.
        """
        self.assertEqual(
            rfc3339TextAsDateTime(self.dateTimeAsRFC3339Text(dateTime)),
            dateTime,
        )
