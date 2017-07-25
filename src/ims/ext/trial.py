# -*- test-case-name: ranger-ims-server.ext.test.test_trial -*-
"""
Extensions to :mod:`twisted.trial`
"""

from typing import Any, Optional, Sequence

from twisted.internet.defer import Deferred, ensureDeferred
from twisted.python.failure import Failure
from twisted.trial.unittest import SynchronousTestCase
from twisted.web import http
from twisted.web.iweb import IRequest

from .klein import ContentType


__all__ = (
    "TestCase",
)



class TestCase(SynchronousTestCase):
    """
    A unit test. The atom of the unit testing universe.

    This class extends :class:`SynchronousTestCase`, not
    :class:`twisted.trial.unittest.TestCase`, because tests that are themselves
    asynchronous cause some known problems, and one should be able to unit test
    code synchronously.
    """

    def successResultOf(self, deferred: Deferred) -> Any:
        """
        Override :meth:`SynchronousTestCase.successResultOf` to enable handling
        of coroutines as well as :class:`Deferred` s.
        """
        deferred = ensureDeferred(deferred)
        return SynchronousTestCase.successResultOf(self, deferred)


    def failureResultOf(
        self, deferred: Deferred, *expectedExceptionTypes: BaseException
    ) -> Failure:
        """
        Override :meth:`SynchronousTestCase.failureResultOf` to enable handling
        of coroutines as well as :class:`Deferred` s.
        """
        deferred = ensureDeferred(deferred)
        return SynchronousTestCase.failureResultOf(
            self, deferred, *expectedExceptionTypes
        )


    def _headerValues(self, request: IRequest, name: str) -> Sequence[str]:
        return request.responseHeaders.getRawHeaders(name, default=[])


    def _headerValue(self, request: IRequest, name: str) -> Optional[str]:
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
            self.assertEqual(prefix, string[:len(prefix)])
        else:
            self.assertEqual(prefix, string)


    def assertEndsWith(self, string: str, suffix: str) -> None:
        """
        Assert that the given string ends with the given suffix.
        """
        if len(suffix) < len(string):
            self.assertEqual(suffix, string[-len(suffix):])
        else:
            self.assertEqual(suffix, string)


    def assertResponseCode(self, request: IRequest, code: int) -> None:
        """
        Assert that the response code on a request matches the given code.
        """
        self.assertEqual(request.code, code)


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

        return request.getWrittenData().decode()


    def assertJSONResponse(
        self, request: IRequest, status: int = http.OK
    ) -> str:
        """
        Assert that the response is JSON and return the JSON text.
        """
        self.assertResponseCode(request, status)
        self.assertResponseContentType(request, ContentType.json.value)

        # FIXME: Check encoding, default to UTF-8

        return request.getWrittenData().decode()
