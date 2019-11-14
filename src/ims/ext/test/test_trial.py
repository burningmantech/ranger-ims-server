"""
Tests for :mod:`ranger-ims-server.ext.trial`
"""

from klein.test.test_resource import requestMock

from ..trial import TestCase


__all__ = ()



class ResultOfTests(TestCase):
    """
    Tests for ``*ResultOf`` methods of :class:`TestCase`.
    """

    def test_successResultOf(self) -> None:
        """
        :meth:`TestCase.successResultOf` works with coroutines.
        """
        raise NotImplementedError()

    test_successResultOf.todo = "unimplemented"  # type: ignore[attr-defined]


    def test_failureResultOf(self) -> None:
        """
        :meth:`TestCase.failureResultOf` works with coroutines.
        """
        raise NotImplementedError()

    test_failureResultOf.todo = "unimplemented"  # type: ignore[attr-defined]



class AssertionTests(TestCase):
    """
    Tests for ``assert*`` methods of :class:`TestCase`.
    """

    def test_assertResponseCode_match(self) -> None:
        """
        :meth:`TestCase.assertResponseCode` does not raise when given a request
        with the expected response code.
        """
        request = requestMock(b"/")
        request.code = 201

        self.assertResponseCode(request, 201)


    def test_assertResponseCode_mismatch(self) -> None:
        """
        :meth:`TestCase.assertResponseCode` raises :obj:`self.failureException`
        when given a request without the expected response code.
        """
        request = requestMock(b"/")
        request.code = 500

        self.assertRaises(
            self.failureException, self.assertResponseCode, request, 201
        )


    def test_assertResponseContentType_match(self) -> None:
        """
        :meth:`TestCase.assertResponseContentType` does not raise when given a
        request with the expected response ``Content-Type`` header.
        """
        request = requestMock(b"/")
        request.setHeader("content-type", "text/l33t")

        self.assertResponseContentType(request, "text/l33t")


    def test_assertResponseContentType_mismatch(self) -> None:
        """
        :meth:`TestCase.assertResponseContentType` raises
        :obj:`self.failureException` when given a request without the expected
        response ``Content-Type`` header.
        """
        request = requestMock(b"/")
        request.setHeader("content-type", "text/plain")

        self.assertRaises(
            self.failureException,
            self.assertResponseContentType, request, "text/l33t"
        )
