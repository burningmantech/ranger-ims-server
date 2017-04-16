"""
Tests for :mod:`ranger-ims-server.model._entry`
"""

from datetime import datetime as DateTime, timezone as TimeZone

from twisted.python.compat import cmp

from .._entry import ReportEntry
from .._ranger import Ranger, RangerStatus
from ...ext.trial import TestCase


__all__ = ()



class ReportEntryTests(TestCase):
    """
    Tests for :class:`ReportEntry`
    """

    hubcap = Ranger(
        handle="Hubcap",
        name="Ranger Hubcap",
        status=RangerStatus.active,
        email=(),
        onSite=False,
        dmsID=0,
        password="password",
    )

    bucket = Ranger(
        handle="Bucket",
        name="Ranger Bucket",
        status=RangerStatus.active,
        email=(),
        onSite=False,
        dmsID=0,
        password="password",
    )

    author = hubcap
    automatic = False
    created = DateTime(2000, 1, 2, tzinfo=TimeZone.utc)
    text = "Hello"


    def test_ordering_created(self) -> None:
        """
        Report entry ordering sorts by created.
        """
        b = ReportEntry(
            created=self.created,
            author=self.author,
            automatic=self.automatic,
            text=self.text,
        )

        a = ReportEntry(
            created=DateTime(2000, 1, 1, tzinfo=TimeZone.utc),
            author=self.author,
            automatic=self.automatic,
            text=self.text,
        )

        self.assertLess(a, b)


    def test_ordering_author(self) -> None:
        """
        Report entry ordering with same created sorts by author.
        """
        b = ReportEntry(
            created=self.created,
            author=self.hubcap,
            automatic=self.automatic,
            text=self.text,
        )

        a = ReportEntry(
            created=self.created,
            author=self.bucket,
            automatic=self.automatic,
            text=self.text,
        )

        self.assertLess(a, b)


    def test_ordering_automatic(self) -> None:
        """
        Report entry ordering with same created and author sorts by automatic,
        where :obj:`True` comes before :obj:`False`.
        """
        b = ReportEntry(
            created=self.created,
            author=self.hubcap,
            automatic=False,
            text=self.text,
        )

        a = ReportEntry(
            created=self.created,
            author=self.hubcap,
            automatic=True,
            text=self.text,
        )

        self.assertLess(a, b)

