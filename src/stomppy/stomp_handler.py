import copy
import datetime
from typing import Dict, Any

from src.stomppy.i_message import Message
from src.stomppy.byte import BYTE
from src.stomppy.frame_impl import FrameImpl
from src.stomppy.i_transaction import ITransaction
from src.stomppy.parser import Parser
from src.stomppy.stomp_headers import StompHeaders
from src.stomppy.enc_dec import TextDecoder, TextEncoder
from src.stomppy.i_frame import FrameParams, IFrame
from src.stomppy.i_transaction import Transaction
from src.stomppy.utils import ScheduleTimer
from src.stomppy.stomp_subscription import StompSubscription
from src.stomppy.ltypes import (
    CloseEventCallbackType,
    DebugFnType,
    FrameCallbackType,
    IPublishParams,
    IStompSocket,
    IStompSocketMessageEvent,
    IStomptHandlerConfig,
    MessageCallbackType,
    StompSocketState,
    WsErrorCallbackType,
)
from src.stomppy.versions import Versions
from src.stomppy.argument_websocket import augmentWebsocket
from src.stomppy.utils import setInterval, clearInterval

"""
 * The STOMP protocol handler
 *
 * Part of `@stomp/stompjs`.
 *
 * @internal
"""


class StompHandler:
    debug: DebugFnType
    stompVersions: Versions
    connectHeaders: StompHeaders
    disconnectHeaders: StompHeaders
    heartbeatIncoming: int
    heartbeatOutgoing: int
    onUnhandledMessage: MessageCallbackType
    onUnhandledReceipt: FrameCallbackType
    onUnhandledFrame: FrameCallbackType
    onConnect: FrameCallbackType
    onDisconnect: FrameCallbackType
    onStompError: FrameCallbackType
    onWebSocketClose: CloseEventCallbackType
    onWebSocketError: WsErrorCallbackType
    logRawCommunication: bool
    splitLargeFrames: bool
    maxWebSocketChunkSize: int
    forceBinaryWSFrames: bool
    appendMissingNULLonIncoming: bool
    discardWebsocketOnCommFailure: bool

    @property
    def connectedVersion(self) -> str | None:
        return self._connectedVersion

    _connectedVersion: str | None

    @property
    def connected(self) -> bool:
        return self._connected

    _connected: bool = False

    _subscriptions: Dict[str, MessageCallbackType] = {}
    _receiptWatchers: Dict[str, FrameCallbackType] = {}
    _partialData: str = None
    _escapeHeaderValues: bool = 0
    _counter: int = 0
    _pinger: ScheduleTimer | None = None
    _ponger: ScheduleTimer | None = None
    _lastServerActivityTS: int

    _client: Any
    _webSocket: IStompSocket
    config: IStomptHandlerConfig

    def __init__(self,
                 client: Any,
                 webSocket: IStompSocket,
                 config: IStomptHandlerConfig
                 ):
        self._client = client
        self._webSocket = webSocket
        self._config = config

        # used to index subscribers
        self._counter = 0

        # subscription callbacks indexed by subscriber's ID
        self._subscriptions = {}

        # receipt-watchers indexed by receipts-ids
        self._receiptWatchers = {}

        self._partialData = ''

        self._escapeHeaderValues = False

        self._lastServerActivityTS = int(datetime.datetime.now().timestamp() * 1000)

        self.debug = config.debug
        self.stompVersions = config.stompVersions
        self.connectHeaders = config.connectHeaders
        self.disconnectHeaders = config.disconnectHeaders
        self.heartbeatIncoming = config.heartbeatIncoming
        self.heartbeatOutgoing = config.heartbeatOutgoing
        self.splitLargeFrames = config.splitLargeFrames
        self.maxWebSocketChunkSize = config.maxWebSocketChunkSize
        self.forceBinaryWSFrames = config.forceBinaryWSFrames
        self.logRawCommunication = config.logRawCommunication
        self.appendMissingNULLonIncoming = config.appendMissingNULLonIncoming
        self.discardWebsocketOnCommFailure = config.discardWebsocketOnCommFailure
        self.onConnect = config.onConnect
        self.onDisconnect = config.onDisconnect
        self.onStompError = config.onStompError
        self.onWebSocketClose = config.onWebSocketClose
        self.onWebSocketError = config.onWebSocketError
        self.onUnhandledMessage = config.onUnhandledMessage
        self.onUnhandledReceipt = config.onUnhandledReceipt
        self.onUnhandledFrame = config.onUnhandledFrame

    def start(self) -> None:
        def onFrame(rawFrame):
            frame = FrameImpl.fromRawFrame(
                rawFrame,
                self._escapeHeaderValues
            )
            # if this.logRawCommunication is set, the rawChunk is logged at this._webSocket.onmessage
            if not self.logRawCommunication:
                self.debug(f" <<< {frame}")
            serverFrameHandler = self.serverFrameHandlers[frame.command] or self.onUnhandledFrame
            serverFrameHandler(frame)

        parser = Parser(
            # On Frame
            onFrame,
            # On Incoming Ping
            lambda: self.debug('<<< PONG')
        )

        def onMessage(evt: IStompSocketMessageEvent):
            self._lastServerActivityTS = int(datetime.datetime.now().timestamp() * 1000)
            if self.logRawCommunication:
                rawChunkAsString = TextDecoder().decode(evt.data) if type(
                    evt.data).__name__ != 'str' else evt.data
                self.debug(f" <<< {rawChunkAsString}")
            parser.parseChunk(
                evt.data,
                self.appendMissingNULLonIncoming
            )

        self._webSocket.onmessage = onMessage

        def onClose(closeEvent):
            self.debug(f"Connection to {self._webSocket.url} closed successfully ")
            self._cleanUp()
            self.onWebSocketClose(closeEvent)

        self._webSocket.onclose = onClose

        def onError(errorEvent):
            self.onWebSocketError(errorEvent)

        self._webSocket.onerror = onError

        def onOpen(evt):
            # Clone before updating
            connectHeaders = copy.deepcopy(self.connectHeaders)
            connectHeaders['accept-version'] = self.stompVersions.supported_versions()
            connectHeaders['heart-beat'] = ','.join([
                str(self.heartbeatOutgoing),
                str(self.heartbeatIncoming),
            ])
            self._transmit(FrameParams(command='CONNECT', headers=connectHeaders))

        self._webSocket.onopen = onOpen

    _serverFrameHandlers: Dict[str, FrameCallbackType] = None

    @property
    def serverFrameHandlers(self):
        if self._serverFrameHandlers is None:
            def onConnected(frame: IFrame):
                self.debug(f"connected to server {frame.headers.get('server')}")
                self._connected = True
                self._connectedVersion = frame.headers['version']
                # STOMP version 1.2 needs header values to be escaped
                if self._connectedVersion == Versions.V1_2:
                    self._escapeHeaderValues = True
                self._setupHeartbeat(frame.headers)
                if self.onConnect:
                    self.onConnect(frame)

            def onMessage(frame: IFrame):
                subscription = frame.headers.get("subscription")
                onReceive = self._subscriptions[subscription] or self.onUnhandledMessage
                # bless the frame to be a Message
                message = Message(frame)
                client = self
                messageId = (message.headers.get("ack") if self._connectedVersion == Versions.V1_2
                             else message.headers['message-id'])
                # add `ack()` and `nack()` methods directly to the returned frame
                # so that a simple call to `message.ack()` can acknowledge the message.
                message.ack = lambda headers=StompHeaders(): client.ack(messageId, subscription, headers)
                message.nack = lambda headers=StompHeaders(): client.nack(messageId, subscription, headers)
                onReceive(message)

            def onReceipt(frame):
                callback = self._receiptWatchers[frame.headers['receipt-id']]
                if callback:
                    callback(frame)
                    # Server will acknowledge only once, remove the callback
                    del self._receiptWatchers[frame.headers['receipt-id']]
                else:
                    self.onUnhandledReceipt(frame)

            def onError(frame):
                self.onStompError(frame)

            self._serverFrameHandlers = {
                "CONNECTED": FrameCallbackType(onConnected),
                # [MESSAGE Frame](https://stomp.github.com/stomp-specification-1.2.html#MESSAGE)
                "MESSAGE": FrameCallbackType(onMessage),
                # [RECEIPT Frame](https://stomp.github.com/stomp-specification-1.2.html#RECEIPT)
                "RECEIPT": FrameCallbackType(onReceipt),
                # [ERROR Frame](https://stomp.github.com/stomp-specification-1.2.html#ERROR)
                "ERROR": FrameCallbackType(onError)
            }
        return self._serverFrameHandlers

    def _setupHeartbeat(self, headers: StompHeaders):
        if (headers["version"] != Versions.V1_1 and
                headers["version"] != Versions.V1_2):
            return
        # It is valid for the server to not send this header
        # https://stomp.github.io/stomp-specification-1.2.html#Heart-beating
        if not headers['heart-beat']:
            return

        # heart-beat header received from the server looks like:
        # heart-beat: sx, sy
        serverOutgoing, serverIncoming = [int(v) for v in headers['heart-beat'].split(',')]
        if self.heartbeatOutgoing != 0 and serverIncoming != 0:
            ttl: int = max(self.heartbeatOutgoing, serverIncoming)
            self.debug(f"send PING every {ttl}ms")

            def callback():
                if self._webSocket.readyState == StompSocketState.OPEN:
                    self._webSocket.send(BYTE.LF)
                    self.debug('>>> PING')

            self._pinger = setInterval(callback, ttl)
        if self.heartbeatIncoming != 0 and serverOutgoing != 0:
            ttl: int = max(self.heartbeatIncoming, serverOutgoing)
            self.debug(f"check PONG every {ttl}ms")

            def callback():
                delta = int(datetime.datetime.now().timestamp() * 1000) - self._lastServerActivityTS
                # We wait twice the TTL to be flexible on window's setInterval calls
                if delta > ttl * 2:
                    self.debug(f"did not receive server activity for the last {delta}ms")
                    self._closeOrDiscardWebsocket()

            self._ponger = setInterval(callback, ttl)

    def _closeOrDiscardWebsocket(self):
        if self.discardWebsocketOnCommFailure:
            self.debug('Discarding websocket, the underlying socket may linger for a while')
            self.discardWebsocket()
        else:
            self.debug('Issuing close on the websocket')
            self._closeWebsocket()

    def forceDisconnect(self):
        if self._webSocket and (self._webSocket.readyState == StompSocketState.CONNECTING or
                                self._webSocket.readyState == StompSocketState.OPEN):
            self._closeOrDiscardWebsocket()

    def _closeWebsocket(self):
        self._webSocket.onmessage = lambda: {}  # ignore messages
        self._webSocket.close()

    def discardWebsocket(self):
        if type(self._webSocket.terminate).__name__ != 'function':
            augmentWebsocket(self._webSocket, lambda msg: self.debug(msg))
        # @ts-ignore - this method will be there at this stage
        self._webSocket.terminate()

    def _transmit(self, params: FrameParams):
        params.escapeHeaderValues = self._escapeHeaderValues
        frame = FrameImpl(params)
        rawChunk = frame.serialize()
        if self.logRawCommunication:
            self.debug(f">>> {rawChunk}")
        else:
            self.debug(f">>> {frame}")
        if self.forceBinaryWSFrames and type(rawChunk).__name__ == 'str':
            rawChunk = TextEncoder().encode(rawChunk)
        if type(rawChunk).__name__ != 'str' or not self.splitLargeFrames:
            self._webSocket.send(rawChunk)
        else:
            out = str(rawChunk)
            while len(out) > 0:
                chunk = out[0:self.maxWebSocketChunkSize]
                out = out[self.maxWebSocketChunkSize:]
                self._webSocket.send(chunk)
                self.debug(f"chunk sent = {len(chunk)}, remaining = {len(out)}")

    def dispose(self):
        if self.connected:
            try:
                # clone before updating
                disconnectHeaders = self.disconnectHeaders if self.disconnectHeaders else StompHeaders()
                if not disconnectHeaders.get("receipt"):
                    disconnectHeaders["receipt"] = f"close-{self._counter}"
                    self._counter += 1

                def receiptHandler(frame):
                    self._closeWebsocket()
                    self._cleanUp()
                    self.onDisconnect(frame)

                self.watchForReceipt(disconnectHeaders["receipt"], FrameCallbackType(receiptHandler))
                self._transmit(FrameParams(command='DISCONNECT', headers=disconnectHeaders))
            except Exception as error:
                self.debug(f"Ignoring error during disconnect {error}")
        else:
            if (self._webSocket.readyState == StompSocketState.CONNECTING or
                    self._webSocket.readyState == StompSocketState.OPEN):
                self._closeWebsocket()

    def _cleanUp(self):
        self._connected = False
        if self._pinger:
            clearInterval(self._pinger)
            self._pinger = None
        if self._ponger:
            clearInterval(self._ponger)
            self._ponger = None

    def publish(self, params: IPublishParams):
        hdrs: StompHeaders = copy.deepcopy(params.headers) if params.headers else StompHeaders()
        hdrs["destination"] = params.destination
        self._transmit(FrameParams(
            command='SEND',
            headers=hdrs,
            body=params.body,
            binaryBody=params.binaryBody,
            skipContentLengthHeader=params.skipContentLengthHeader,
        ))

    def watchForReceipt(self, receiptId: str, callback: FrameCallbackType):
        self._receiptWatchers[receiptId] = callback

    def subscribe(
            self,
            destination: str,
            callback: MessageCallbackType,
            headers: StompHeaders = StompHeaders()
    ) -> StompSubscription:
        headers = copy.deepcopy(headers)
        if not headers.get("id"):
            headers["id"] = f"sub-{self._counter}"
            self._counter += 1
        headers["destination"] = destination
        self._subscriptions[headers["id"]] = callback
        self._transmit(FrameParams(command='SUBSCRIBE', headers=headers))
        client = self
        return StompSubscription(id=headers["id"], unsubscribe=lambda hdrs: client.unsubscribe(headers["id"], hdrs))

    def unsubscribe(self, id: str, headers: StompHeaders = StompHeaders()):
        headers = copy.deepcopy(headers)
        del self._subscriptions[id]
        headers["id"] = id
        self._transmit(FrameParams(command='UNSUBSCRIBE', headers=headers))

    def begin(self, transactionId: str) -> ITransaction:
        txId = transactionId or f"tx-{self._counter}"
        self._counter += 1
        self._transmit(FrameParams(
            command='BEGIN',
            headers=StompHeaders({"transaction": txId}),
        ))
        client = self
        return Transaction(
            id=txId,
            commit=lambda: client.commit(txId),
            abort=lambda: client.abort(txId)
        )

    def commit(self, transactionId: str):
        self._transmit(FrameParams(
            command='COMMIT',
            headers=StompHeaders(
                {"transaction": transactionId}
            )
        ))

    def abort(self, transactionId: str):
        self._transmit(FrameParams(
            command='ABORT',
            headers=StompHeaders({
                "transaction": transactionId,
            })
        ))

    def ack(
            self,
            messageId: str,
            subscriptionId: str,
            headers: StompHeaders = StompHeaders()
    ):
        headers = copy.deepcopy(headers)
        if self._connectedVersion == Versions.V1_2:
            headers["id"] = messageId
        else:
            headers['message-id'] = messageId
        headers["subscription"] = subscriptionId
        self._transmit(FrameParams(command='ACK', headers=headers))

    def nack(
            self,
            messageId: str,
            subscriptionId: str,
            headers: StompHeaders = StompHeaders()
    ):
        headers = copy.deepcopy(headers)
        if self._connectedVersion == Versions.V1_2:
            headers["id"] = messageId
        else:
            headers['message-id'] = messageId
        headers["subscription"] = subscriptionId
        return self._transmit(FrameParams(command='NACK', headers=headers))

