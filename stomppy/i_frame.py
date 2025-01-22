from abc import ABC
from typing import List
from stomppy.rtypes import Uint8Array

from stomppy.stomp_headers import StompHeaders

"""
 * It represents a STOMP frame. Many of the callbacks pass an IFrame received from
 * the STOMP broker. For advanced usage you might need to access [headers]{@link IFrame#headers}.
 *
 * Part of `@stomp/stomppy`.
 *
 * {@link IMessage} is an extended IFrame.
"""


class IFrame(ABC):
    """
    * STOMP Command
    """
    command: str

    """
    * Headers, key value pairs.
    """
    headers: StompHeaders

    """
    # Is this frame binary (based on whether body/binaryBody was passed when creating this frame).
    """
    isBinaryBody: bool

    """
     * body of the frame as string
    """
    body: str

    """
    * body as Uint8Array
    """
    binaryBody: List[int]


class Frame(IFrame):
    pass


class FrameParams:
    command: str
    headers: StompHeaders | None
    body: str | None
    binaryBody: Uint8Array | None
    escapeHeaderValues: bool = False
    skipContentLengthHeader: bool = False

    def __init__(self, command: str, headers: StompHeaders, body: str | None = None,
                 binaryBody: Uint8Array | None = None, escapeHeaderValues: bool = False,
                 skipContentLengthHeader: bool = False):
        self.command = command
        self.headers = headers
        self.body = body
        self.binaryBody = binaryBody
        self.escapeHeaderValues = escapeHeaderValues
        self.skipContentLengthHeader = skipContentLengthHeader
