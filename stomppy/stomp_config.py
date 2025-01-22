from typing import Any, Callable

from stomppy.stomp_headers import StompHeaders
from stomppy.ltypes import (ActivationState, CloseEventCallbackType,
                            DebugFnType, FrameCallbackType, MessageCallbackType,
                            WsErrorCallbackType)
from stomppy.versions import Versions
from stomppy.rtypes import Promise

"""
 * Configuration options for STOMP Client, each key corresponds to
 * field by the same name in {@link Client}. This can be passed to
 * the constructor of {@link Client} or to [Client#configure]{@link Client#configure}.
 *
 * Part of `@stomp/stomppy`.
"""


class StompConfig:
    """
    * See [Client#brokerURL]{@link Client#brokerURL}.
    """
    brokerURL: str

    """
    * See [Client#stompVersions]{@link Client#stompVersions}.
    """
    stompVersions: Versions | None

    """
    * See [Client#webSocketFactory]{@link Client#webSocketFactory}.
    """
    webSocketFactory: Callable[[], Any]

    """
    * See [Client#connectionTimeout]{@link Client#connectionTimeout}.
    """
    connectionTimeout: int

    """
    * See [Client#reconnectDelay]{@link Client#reconnectDelay}.
    """
    reconnectDelay: int

    """
    * See [Client#heartbeatIncoming]{@link Client#heartbeatIncoming}.
    """
    heartbeatIncoming: int

    """
    * See [Client#heartbeatOutgoing]{@link Client#heartbeatOutgoing}.
    """
    heartbeatOutgoing: int

    """
    * See [Client#splitLargeFrames]{@link Client#splitLargeFrames}.
    """

    splitLargeFrames: bool

    """
    * See [Client#forceBinaryWSFrames]{@link Client#forceBinaryWSFrames}.
    """
    forceBinaryWSFrames: bool

    """
    * See [Client#appendMissingNULLonIncoming]{@link Client#appendMissingNULLonIncoming}.
    """
    appendMissingNULLonIncoming: bool

    """
    * See [Client#maxWebSocketChunkSize]{@link Client#maxWebSocketChunkSize}.
    """
    maxWebSocketChunkSize: int

    """
    * See [Client#connectHeaders]{@link Client#connectHeaders}.
    """
    connectHeaders: StompHeaders

    """
    * See [Client#disconnectHeaders]{@link Client#disconnectHeaders}.
    """
    disconnectHeaders: StompHeaders

    """
    * See [Client#onUnhandledMessage]{@link Client#onUnhandledMessage}.
    """
    onUnhandledMessage: MessageCallbackType

    """
    * See [Client#onUnhandledReceipt]{@link Client#onUnhandledReceipt}.
    """
    onUnhandledReceipt: FrameCallbackType

    """
    * See [Client#onUnhandledFrame]{@link Client#onUnhandledFrame}.
    """
    onUnhandledFrame: FrameCallbackType

    """
    * See [Client#beforeConnect]{@link Client#beforeConnect}.
    """
    beforeConnect: Callable[[], None | Promise]

    """
    * See [Client#onConnect]{@link Client#onConnect}.
    """
    onConnect: FrameCallbackType

    """
    * See [Client#onDisconnect]{@link Client#onDisconnect}.
    """
    onDisconnect: FrameCallbackType

    """
    * See [Client#onStompError]{@link Client#onStompError}.
    """
    onStompError: FrameCallbackType

    """
    * See [Client#onWebSocketClose]{@link Client#onWebSocketClose}.
    """
    onWebSocketClose: CloseEventCallbackType

    """
    * See [Client#onWebSocketError]{@link Client#onWebSocketError}.
    """
    onWebSocketError: WsErrorCallbackType

    """
    * See [Client#logRawCommunication]{@link Client#logRawCommunication}.
    """
    logRawCommunication: bool

    """
    * See [Client#debug]{@link Client#debug}.
    """
    debug: DebugFnType

    """
    * See [Client#discardWebsocketOnCommFailure]{@link Client#discardWebsocketOnCommFailure}.
    """
    discardWebsocketOnCommFailure: bool

    """
    * See [Client#onChangeState]{@link Client#onChangeState}.
    """
    onChangeState: Callable[[ActivationState], None]

    def __init__(self,
                 brokerURL: str = None,
                 stompVersions: Versions | None = None,
                 webSocketFactory: Callable[[], Any] = None,
                 connectionTimeout: int = 2000,
                 reconnectDelay: int = 2000,
                 heartbeatIncoming: int = 0,
                 heartbeatOutgoing: int = 0,
                 splitLargeFrames: bool = 0,
                 forceBinaryWSFrames: bool = False,
                 appendMissingNULLonIncoming: bool = False,
                 maxWebSocketChunkSize: int = False,
                 connectHeaders: StompHeaders = None,
                 disconnectHeaders: StompHeaders = None,
                 onUnhandledMessage: MessageCallbackType = None,
                 onUnhandledReceipt: FrameCallbackType = None,
                 onUnhandledFrame: FrameCallbackType = None,
                 beforeConnect: Callable[[], None | Promise] = None,
                 onConnect: FrameCallbackType = None,
                 onDisconnect: FrameCallbackType = None,
                 onStompError: FrameCallbackType = None,
                 onWebSocketClose: CloseEventCallbackType = None,
                 onWebSocketError: WsErrorCallbackType = None,
                 logRawCommunication: bool = None,
                 debug: DebugFnType = None,
                 discardWebsocketOnCommFailure: bool = None,
                 onChangeState: Callable[[ActivationState], None] = None
    ):
        self.brokerURL = brokerURL
        self.stompVersions = stompVersions
        self.webSocketFactory = webSocketFactory
        self.connectionTimeout = connectionTimeout
        self.reconnectDelay = reconnectDelay
        self.heartbeatIncoming = heartbeatIncoming
        self.heartbeatOutgoing = heartbeatOutgoing
        self.splitLargeFrames = splitLargeFrames
        self.forceBinaryWSFrames = forceBinaryWSFrames
        self.appendMissingNULLonIncoming = appendMissingNULLonIncoming
        self.maxWebSocketChunkSize = maxWebSocketChunkSize
        self.connectHeaders = connectHeaders
        self.disconnectHeaders = disconnectHeaders
        self.onUnhandledMessage = onUnhandledMessage
        self.onUnhandledReceipt = onUnhandledReceipt
        self.onUnhandledFrame = onUnhandledFrame
        self.beforeConnect = beforeConnect
        self.onConnect = onConnect
        self.onDisconnect = onDisconnect
        self.onStompError = onStompError
        self.onWebSocketClose = onWebSocketClose
        self.onWebSocketError = onWebSocketError
        self.logRawCommunication = logRawCommunication
        self.debug = debug
        self.discardWebsocketOnCommFailure = discardWebsocketOnCommFailure
        self.onChangeState = onChangeState

