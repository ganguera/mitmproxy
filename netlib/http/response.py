from __future__ import absolute_import, print_function, division

import warnings

from . import cookies
from .headers import Headers
from .message import Message, _native, _always_bytes, MessageData
from .. import utils
from ..odict import ODict


class ResponseData(MessageData):
    def __init__(self, http_version, status_code, reason=None, headers=None, content=None,
                 timestamp_start=None, timestamp_end=None):
        if not isinstance(headers, Headers):
            headers = Headers(headers)

        self.http_version = http_version
        self.status_code = status_code
        self.reason = reason
        self.headers = headers
        self.content = content
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end


class Response(Message):
    """
    An HTTP response.
    """
    def __init__(self, *args, **kwargs):
        data = ResponseData(*args, **kwargs)
        super(Response, self).__init__(data)

    def __repr__(self):
        if self.content:
            details = "{}, {}".format(
                self.headers.get("content-type", "unknown content type"),
                utils.pretty_size(len(self.content))
            )
        else:
            details = "no content"
        return "Response({status_code} {reason}, {details})".format(
            status_code=self.status_code,
            reason=self.reason,
            details=details
        )

    @property
    def status_code(self):
        """
        HTTP Status Code, e.g. ``200``.
        """
        return self.data.status_code

    @status_code.setter
    def status_code(self, status_code):
        self.data.status_code = status_code

    @property
    def reason(self):
        """
        HTTP Reason Phrase, e.g. "Not Found".
        This is always :py:obj:`None` for HTTP2 requests, because HTTP2 responses do not contain a reason phrase.
        """
        return _native(self.data.reason)

    @reason.setter
    def reason(self, reason):
        self.data.reason = _always_bytes(reason)

    @property
    def cookies(self):
        """
        Get the contents of all Set-Cookie headers.

        A possibly empty :py:class:`ODict`, where keys are cookie name strings,
        and values are [value, attr] lists. Value is a string, and attr is
        an ODictCaseless containing cookie attributes. Within attrs, unary
        attributes (e.g. HTTPOnly) are indicated by a Null value.
        """
        ret = []
        for header in self.headers.get_all("set-cookie"):
            v = cookies.parse_set_cookie_header(header)
            if v:
                name, value, attrs = v
                ret.append([name, [value, attrs]])
        return ODict(ret)

    @cookies.setter
    def cookies(self, odict):
        values = []
        for i in odict.lst:
            header = cookies.format_set_cookie_header(i[0], i[1][0], i[1][1])
            values.append(header)
        self.headers.set_all("set-cookie", values)

    # Legacy

    def get_cookies(self):  # pragma: nocover
        warnings.warn(".get_cookies is deprecated, use .cookies instead.", DeprecationWarning)
        return self.cookies

    def set_cookies(self, odict):  # pragma: nocover
        warnings.warn(".set_cookies is deprecated, use .cookies instead.", DeprecationWarning)
        self.cookies = odict

    @property
    def msg(self):  # pragma: nocover
        warnings.warn(".msg is deprecated, use .reason instead.", DeprecationWarning)
        return self.reason

    @msg.setter
    def msg(self, reason):  # pragma: nocover
        warnings.warn(".msg is deprecated, use .reason instead.", DeprecationWarning)
        self.reason = reason
