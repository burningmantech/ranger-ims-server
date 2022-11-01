# -*- test-case-name: ranger-ims-server.ext.test.test_trial -*-
"""
Extensions to :mod:`twisted.trial`
"""

from collections.abc import Callable, Sequence
from functools import wraps
from typing import Any, cast

from hypothesis import HealthCheck, settings
from twisted.internet.defer import ensureDeferred
from twisted.trial.unittest import SynchronousTestCase as SuperTestCase
from twisted.trial.unittest import TestCase as SuperAsynchronousTestCase
from twisted.web import http
from twisted.web.iweb import IRequest

from ims.ext.klein import ContentType
from ims.model import EventData, IMSData


__all__ = ("TestCase", "asyncAsDeferred")


# Configure Hypothesis
settings.register_profile(
    "ci",
    deadline=None,
    suppress_health_check=[
        HealthCheck.data_too_large,
        HealthCheck.too_slow,
    ],
)
settings.load_profile("ci")


def asyncAsDeferred(f: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for async methods to return a Deferred object instead of a
    coroutine.
    """

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return ensureDeferred(f(*args, **kwargs))

    return wrapper


class TestCase(SuperTestCase):
    """
    A unit test.
    """

    def _headerValues(self, request: IRequest, name: str) -> Sequence[str]:
        return cast(
            Sequence[str],
            request.responseHeaders.getRawHeaders(name, default=[]),
        )

    def _headerValue(self, request: IRequest, name: str) -> str | None:
        values = self._headerValues(request, name)
        if len(values) == 0:
            return None
        self.assertEqual(len(values), 1)
        return values[0]

    def assertStartsWith(self, string: str, prefix: str) -> None:
        """
        Assert that the given string starts with the given prefix.
        """
        if len(prefix) < len(string):
            self.assertEqual(prefix, string[: len(prefix)])
        else:
            self.assertEqual(prefix, string)

    def assertEndsWith(self, string: str, suffix: str) -> None:
        """
        Assert that the given string ends with the given suffix.
        """
        if len(suffix) < len(string):
            self.assertEqual(suffix, string[-len(suffix) :])
        else:
            self.assertEqual(suffix, string)

    def assertResponseCode(self, request: IRequest, code: int) -> None:
        """
        Assert that the response code on a request matches the given code.
        """
        self.assertEqual(request.code, code)  # type: ignore[attr-defined]

    def assertResponseContentType(
        self, request: IRequest, contentType: str
    ) -> None:
        """
        Assert that the response content-type on a request matches the given
        value.
        """
        responseContentType = self._headerValue(request, "content-type")
        self.assertEqual(responseContentType, contentType)

    def assertTextResponse(self, request: IRequest) -> str:
        """
        Assert that the response is text and return the text.
        """
        self.assertResponseCode(request, http.OK)
        self.assertResponseContentType(request, ContentType.text.value)

        # FIXME: Check encoding, default to UTF-8

        data = request.getWrittenData()  # type: ignore[attr-defined]
        return cast(bytes, data).decode()

    def assertJSONResponse(
        self, request: IRequest, status: int = http.OK
    ) -> str:
        """
        Assert that the response is JSON and return the JSON text.
        """
        self.assertResponseCode(request, status)
        self.assertResponseContentType(request, ContentType.json.value)

        # FIXME: Check encoding, default to UTF-8

        data = request.getWrittenData()  # type: ignore[attr-defined]
        return cast(bytes, data).decode()

    def assertEventDataEqual(
        self, eventDataA: EventData, eventDataB: EventData
    ) -> None:
        """
        Assert that the given eventData objects are equal.
        """
        try:
            self.assertEqual(eventDataA.event, eventDataB.event)
        except self.failureException as e:
            self.fail(f"EventData.event: {e}")

        try:
            self.assertEqual(eventDataA.access, eventDataB.access)
        except self.failureException as e:
            self.fail(f"EventData.access: {e}")

        try:
            self.assertEqual(
                eventDataA.concentricStreets, eventDataB.concentricStreets
            )
        except self.failureException as e:
            self.fail(f"EventData.concentricStreets: {e}")

        try:
            self.assertEqual(eventDataA.incidents, eventDataB.incidents)
        except self.failureException as e:
            self.fail(f"EventData.incidents: {e}")

        try:
            self.assertEqual(
                eventDataA.incidentReports, eventDataB.incidentReports
            )
        except self.failureException as e:
            self.fail(f"EventData.incidentReports: {e}")

    def assertIMSDataEqual(self, imsDataA: IMSData, imsDataB: IMSData) -> None:
        """
        Assert that the given IMSData objects are equal.
        """
        try:
            self.assertEqual(imsDataA.incidentTypes, imsDataB.incidentTypes)
        except self.failureException as e:
            self.fail(f"IMSData.incidentTypes: {e}")

        if len(imsDataA.events) != len(imsDataB.events):
            self.fail(
                f"len(IMSData.events): "
                f"{len(imsDataA.events)} != {len(imsDataB.events)}"
            )

        for eventDataA, eventDataB in zip(
            sorted(imsDataA.events), sorted(imsDataB.events)
        ):
            try:
                self.assertEventDataEqual(eventDataA, eventDataB)
            except self.failureException as e:
                self.fail(f"IMSData.events: {e}")

        self.assertEqual(imsDataA, imsDataB)


class AsynchronousTestCase(TestCase, SuperAsynchronousTestCase):
    """
    A asynchronous unit test.
    """
