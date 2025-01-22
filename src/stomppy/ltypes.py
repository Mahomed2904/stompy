from abc import ABC
from enum import Enum

from src.stomppy.i_frame import IFrame
from src.stomppy.i_message import IMessage
from src.stomppy.stomp_headers import StompHeaders
from src.stomppy.rtypes import Uint8Array
from src.stomppy.versions import Versions

from typing import Callable, Any, List, Tuple

"""
 * This callback will receive a `string` as a parameter.
 *
 * Part of `@stomp/stomppy`.
"""


class DebugFnType(Callable[[str], None]):
    def __init__(self, fn: Callable[[str], None]):
        self.fn = fn

    def __call__(self, data: str):
        return self.fn(data)



"""
 * This callback will receive a {@link IMessage} as parameter.
 *
 * Part of `@stomp/stompjs`.
"""


class MessageCallbackType(Callable[[IMessage], None]):
    def __init__(self, fn: Callable[[IMessage], None]):
        self.fn = fn

    def __call__(self, data: IMessage):
        return self.fn(data)


"""
 * This callback will receive a {@link IFrame} as parameter.
 *
 * Part of `@stomp/stompjs`.
"""


class FrameCallbackType(Callable[[IFrame | None], None]):
    def __init__(self, fn: Callable[[IFrame], None]):
        self.fn = fn

    def __call__(self, data: IFrame):
        return self.fn(data)


"""
 * This callback will receive a [CloseEvent]{@link https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent}
 * as parameter.
 *
 * Part of `@stomp/stompjs`.
"""


class CloseEventCallbackType(Callable[[Any], None]):
    def __init__(self, fn: Callable[[Any], None]):
        self.fn = fn

    def __call__(self, data: Any):
        return self.fn(data)


"""
 * This callback will receive an [Event]{@link https://developer.mozilla.org/en-US/docs/Web/API/Event}
 * as parameter.
 *
 * Part of `@stomp/stompjs`.
"""


class WsErrorCallbackType(Callable[[Any], None]):
    def __init__(self, fn: Callable[[Any], None]):
        self.fn = fn

    def __call__(self, data: Any):
        return self.fn(data)


"""
 * Parameters for [Client#publish]{@link Client#publish}.
 * Aliased as publishParams as well.
 *
 * Part of `@stomp/stomppy`.
"""


class IPublishParams(ABC):
    """
    * destination end point
     """
    destination: str
    """
    * headers (optional)
    """
    headers: StompHeaders | None
    """
    * body (optional)
    """
    body: str
    """
    * binary body (optional)
    """
    binaryBody: List[int] | None
    """
    * By default, a `content-length` header will be added in the Frame to the broker.
    * Set it to `true` for the header to be skipped.
    """
    skipContentLengthHeader: bool | None


"""
 * Backward compatibility, switch to {@link IPublishParams}.
"""


class PublishParams(IPublishParams):

    def __init__(self,
                 destination: str = None,
                 headers: StompHeaders | None = None,
                 body: str = None,
                 binaryBody: List[int] | None = None,
                 skipContentLengthHeader: bool | None = None
             ):
        self.destination = destination
        self.headers = headers
        self.body = body
        self.binaryBody = binaryBody
        self.skipContentLengthHeader = skipContentLengthHeader



"""
 * Used in {@link IRawFrameType}
 *
 * Part of `@stomp/stompjs`.
 *
 * @internal
"""


class RawHeaderType(Tuple[str, str]):
    pass


"""
 * The parser yield frames in this structure
 *
 * Part of `@stomp/stompjs`.
 *
 * @internal
"""


class IRawFrameType:
    command: str | None
    headers: List[RawHeaderType]
    binaryBody: List[int] | None

    def __init__(self, command, headers, binaryBody):
        self.command = command
        self.headers = headers
        self.binaryBody = binaryBody


"""
 * @internal
"""


class IStompSocketMessageEvent:
    data: str | Uint8Array


class StompSocketMessageEvent(IStompSocketMessageEvent):

    def __init__(self, data: str | Uint8Array):
        self.data = data

"""
 * Copied from Websocket interface to avoid dom typelib dependency.
 *
 * @internal
"""

"""
 * Possible states for the IStompSocket
"""


class StompSocketState(Enum):
    CONNECTING = "CONNECTING"
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"


class IStompSocket:
    url: str
    onclose: Callable[[Any], Any] | None = None
    onerror: Callable[[Any], Any] | None = None
    onmessage: Callable[[IStompSocketMessageEvent], Any] | None = None
    onopen: Callable[[IStompSocketMessageEvent], Any] | None = None
    terminate: Callable[[], Any] | None = None

    """
    * Returns a string that indicates how binary data from the socket is exposed to scripts:
    * We support only 'arraybuffer'.
    """
    binaryType: str

    """
    * Returns the state of the socket connection. It can have the values of StompSocketState.
    """
    readyState: StompSocketState = StompSocketState.CLOSED

    """
    * Closes the connection.
    """

    close: Callable[[], None]

    """
    * Transmits data using the connection. data can be a string or an ArrayBuffer.
    """

    send: Callable[[str | bytes], None]


"""
 * Possible activation state
"""


class ActivationState(Enum):
    ACTIVE = "ACTIVE"
    DEACTIVATING = "DEACTIVATING"
    INACTIVE = "INACTIVE"


"""
 * @internal
"""


class IStomptHandlerConfig:
    debug: DebugFnType
    stompVersions: Versions
    connectHeaders: StompHeaders
    disconnectHeaders: StompHeaders
    heartbeatIncoming: int
    heartbeatOutgoing: int
    splitLargeFrames: bool
    maxWebSocketChunkSize: int
    forceBinaryWSFrames: bool
    logRawCommunication: bool
    appendMissingNULLonIncoming: bool
    discardWebsocketOnCommFailure: bool
    onConnect: FrameCallbackType
    onDisconnect: FrameCallbackType
    onStompError: FrameCallbackType
    onWebSocketClose: CloseEventCallbackType
    onWebSocketError: WsErrorCallbackType
    onUnhandledMessage: MessageCallbackType
    onUnhandledReceipt: FrameCallbackType
    onUnhandledFrame: FrameCallbackType


class StomptHandlerConfig(IStomptHandlerConfig):

    def __init__(self,
                 debug: DebugFnType,
                 stompVersions: Versions,
                 connectHeaders: StompHeaders,
                 disconnectHeaders: StompHeaders,
                 heartbeatIncoming: int,
                 heartbeatOutgoing: int,
                 splitLargeFrames: bool,
                 maxWebSocketChunkSize: int,
                 forceBinaryWSFrames: bool,
                 logRawCommunication: bool,
                 appendMissingNULLonIncoming: bool,
                 discardWebsocketOnCommFailure: bool,
                 onConnect: FrameCallbackType,
                 onDisconnect: FrameCallbackType,
                 onStompError: FrameCallbackType,
                 onWebSocketClose: CloseEventCallbackType,
                 onWebSocketError: WsErrorCallbackType,
                 onUnhandledMessage: MessageCallbackType,
                 onUnhandledReceipt: FrameCallbackType,
                 onUnhandledFrame: FrameCallbackType,
                 ):
        self.debug = debug
        self.stompVersions = stompVersions
        self.connectHeaders = connectHeaders
        self.disconnectHeaders = disconnectHeaders
        self.heartbeatIncoming = heartbeatIncoming
        self.heartbeatOutgoing = heartbeatOutgoing
        self.splitLargeFrames = splitLargeFrames
        self.maxWebSocketChunkSize = maxWebSocketChunkSize
        self.forceBinaryWSFrames = forceBinaryWSFrames
        self.logRawCommunication = logRawCommunication
        self.appendMissingNULLonIncoming = appendMissingNULLonIncoming
        self.discardWebsocketOnCommFailure = discardWebsocketOnCommFailure
        self.onConnect = onConnect
        self.onDisconnect = onDisconnect
        self.onStompError = onStompError
        self.onWebSocketClose = onWebSocketClose
        self.onWebSocketError = onWebSocketError
        self.onUnhandledMessage = onUnhandledMessage
        self.onUnhandledReceipt = onUnhandledReceipt
        self.onUnhandledFrame = onUnhandledFrame
