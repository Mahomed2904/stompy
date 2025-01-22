import asyncio
import time
from typing import Callable, Any
from src.stomppy.i_transaction import ITransaction
from src.stomppy.stomp_config import StompConfig
from src.stomppy.stomp_headers import StompHeaders
from src.stomppy.ltypes import StomptHandlerConfig
from src.stomppy.stomp_handler import StompHandler
from src.stomppy.stomp_subscription import StompSubscription
from src.stomppy.rtypes import Promise, DeativateOptions
from src.stomppy.ltypes import (
    ActivationState,
    CloseEventCallbackType,
    DebugFnType,
    FrameCallbackType,
    IPublishParams,
    IStompSocket,
    MessageCallbackType,
    StompSocketState,
    WsErrorCallbackType,
)
from src.stomppy.web_socket import WebSocket
from src.stomppy.versions import Versions
from src.stomppy.utils import clearTimeout, setTimeout, ScheduleTimer

'''
 * @internal
'''

'''
 * STOMP Client Class.
 *
 * Part of `stomppy`.
'''


class Client:
    """
    * The URL for the STOMP broker to connect to.
    * Typically like `"ws://broker.329broker.com:15674/ws"` or `"wss://broker.329broker.com:15674/ws"`.
    *
    * Only one of self or [Client#webSocketFactory]{@link Client#webSocketFactory} need to be set.
    * If both are set, [Client#webSocketFactory]{@link Client#webSocketFactory} will be used.
    *
    * If your environment does not support WebSockets natively, please refer to
    * [Polyfills]{@link https://stomp-js.github.io/guide/stompjs/rx-stomp/ng2-stompjs/pollyfils-for-stompjs-v5.html}.
    """
    brokerURL: str | None = None

    """
    * STOMP versions to attempt during STOMP handshake. By default, versions `1.2`, `1.1`, and `1.0` are attempted.
    *
    * Example:
    * ```javascript
    *        // Try only versions 1.1 and 1.0
    *        client.stompVersions = new Versions(['1.1', '1.0'])
    * ```
    """
    stompVersions = Versions.default()

    """
    * self function should return a WebSocket or a similar (e.g. SockJS) object.
    * If your environment does not support WebSockets natively, please refer to
    * [Polyfills]{@link https://stomp-js.github.io/guide/stompjs/rx-stomp/ng2-stompjs/pollyfils-for-stompjs-v5.html}.
    * If your STOMP Broker supports WebSockets, prefer setting [Client#brokerURL]{@link Client#brokerURL}.
    *
    * If both self and [Client#brokerURL]{@link Client#brokerURL} are set, self will be used.
    *
    * Example:
    * ```javascript
    *        // use a WebSocket
    *        client.webSocketFactory= function () {
    *          return new WebSocket("wss://broker.329broker.com:15674/ws");
    *        };
    *
    *        // Typical usage with SockJS
    *        client.webSocketFactory= function () {
    *          return new SockJS("http://broker.329broker.com/stomp");
    *        };
    * ```
    """
    webSocketFactory: Callable[[], IStompSocket | None] = None

    """
    * Will retry if Stomp connection is not established in specified milliseconds.
    * Default 0, which switches off automatic reconnection.
    """
    connectionTimeout: int = 0

    # As per https://stackoverflow.com/questions/45802988/typescript-use-correct-version-of-settimeout-node-vs-window/56239226#56239226
    _connectionWatcher: ScheduleTimer | None = None # Timer

    """
    *  automatically reconnect with delay in milliseconds, set to 0 to disable.
    """
    reconnectDelay: int = 5000

    """
    * Incoming heartbeat interval in milliseconds. Set to 0 to disable.
    """
    heartbeatIncoming: int = 10000

    """
    * Outgoing heartbeat interval in milliseconds. Set to 0 to disable.
    """
    heartbeatOutgoing: int = 10000

    """
    * self switches on a non-standard behavior while sending WebSocket packets.
    * It splits larger (text) packets into chunks of [maxWebSocketChunkSize]{@link Client#maxWebSocketChunkSize}.
    * Only Java Spring brokers seem to support self mode.
    *
    * WebSockets, by itself, split large (text) packets,
    * so it is not needed with a truly compliant STOMP/WebSocket broker.
    * Setting it for such a broker will cause large messages to fail.
    *
    * `false` by default.
    *
    * Binary frames are never split.
    """
    splitLargeFrames: bool = False

    """
    * See [splitLargeFrames]{@link Client#splitLargeFrames}.
    * self has no effect if [splitLargeFrames]{@link Client#splitLargeFrames} is `false`.
    """
    maxWebSocketChunkSize: int = 8 * 1024

    """
    * Usually the
    * [type of WebSocket frame]{@link https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/send#Parameters}
    * is automatically decided by type of the payload.
    * Default is `false`, which should work with all compliant brokers.
    *
    * Set self flag to force binary frames.
    """
    forceBinaryWSFrames: bool = False

    """
    * A bug in ReactNative chops a string on occurrence of a NULL.
    * See issue [https://github.com/stomp-js/stompjs/issues/89]{@link https://github.com/stomp-js/stompjs/issues/89}.
    * self makes incoming WebSocket messages invalid STOMP packets.
    * Setting self flag attempts to reverse the damage by appending a NULL.
    * If the broker splits a large message into multiple WebSocket messages,
    * self flag will cause data loss and abnormal termination of connection.
    *
    * self is not an ideal solution, but a stop gap until the underlying issue is fixed at ReactNative library.
    """
    appendMissingNULLonIncoming: bool = False

    """
    * Underlying WebSocket instance, READONLY.
    """

    @property
    def webSocket(self) -> IStompSocket | None:
        return self._stompHandler._webSocket if self._stompHandler else None

    """
    * Connection headers, important keys - `login`, `passcode`, `host`.
    * Though STOMP 1.2 standard marks these keys to be present, check your broker documentation for
    * details specific to your broker.
    """
    connectHeaders: StompHeaders = None

    """
    * Disconnection headers.
    """

    @property
    def disconnectHeaders(self) -> StompHeaders:
        return self._disconnectHeaders

    @disconnectHeaders.setter
    def disconnectHeaders(self, value: StompHeaders):
        self._disconnectHeaders = value
        if self._stompHandler:
            self._stompHandler.disconnectHeaders = self._disconnectHeaders

    _disconnectHeaders: StompHeaders = None

    """
    * self function will be called for any unhandled messages.
    * It is useful for receiving messages sent to RabbitMQ temporary queues.
    *
    * It can also get invoked with stray messages while the server is processing
    * a request to [Client#unsubscribe]{@link Client#unsubscribe}
    * from an endpoint.
    *
    * The actual {@link IMessage} will be passed as parameter to the callback.
    """
    onUnhandledMessage: MessageCallbackType = None

    """
    * STOMP brokers can be requested to notify when an operation is actually completed.
    * Prefer using [Client#watchForReceipt]{@link Client#watchForReceipt}. See
    * [Client#watchForReceipt]{@link Client#watchForReceipt} for examples.
    *
    * The actual {@link IFrame} will be passed as parameter to the callback.
    """
    onUnhandledReceipt: FrameCallbackType = None

    """
    * Will be invoked if {@link IFrame} of an unknown type is received from the STOMP broker.
    *
    * The actual {@link IFrame} will be passed as parameter to the callback.
    """
    onUnhandledFrame: FrameCallbackType = None

    """
    * `true` if there is an active connection to STOMP Broker
    """

    @property
    def connected(self) -> bool:
        while self.webSocket.readyState == StompSocketState.CONNECTING:
            time.sleep(0.1)
        return self._stompHandler and self._stompHandler.connected

    """
    * Callback, invoked on before a connection to the STOMP broker.
    *
    * You can change options on the client, which will impact the immediate connecting.
    * It is valid to call [Client#decativate]{@link Client#deactivate} in self callback.
    *
    * As of version 5.1, self callback can be
    * [async](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function)
    * (i.e., it can return a
    * [Promise](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise)).
    * In that case, connect will be called only after the Promise is resolved.
    * self can be used to reliably fetch credentials, access token etc. from some other service
    * in an asynchronous way.
    """
    beforeConnect: Callable[[], Promise] = None

    """
    * Callback, invoked on every successful connection to the STOMP broker.
    *
    * The actual {@link IFrame} will be passed as parameter to the callback.
    * Sometimes clients will like to use headers from self frame.
    """
    onConnect: FrameCallbackType = None

    """
    * Callback, invoked on every successful disconnection from the STOMP broker. It will not be invoked if
    * the STOMP broker disconnected due to an error.
    *
    * The actual Receipt {@link IFrame} acknowledging the DISCONNECT will be passed as parameter to the callback.
    *
    * The way STOMP protocol is designed, the connection may close/terminate without the client
    * receiving the Receipt {@link IFrame} acknowledging the DISCONNECT.
    * You might find [Client#onWebSocketClose]{@link Client#onWebSocketClose} more appropriate to watch
    * STOMP broker disconnects.
    """
    onDisconnect: FrameCallbackType = None

    """
    * Callback, invoked on an ERROR frame received from the STOMP Broker.
    * A compliant STOMP Broker will close the connection after self type of frame.
    * Please check broker specific documentation for exact behavior.
    *
    * The actual {@link IFrame} will be passed as parameter to the callback.
    """
    onStompError: FrameCallbackType = None

    """
    * Callback, invoked when underlying WebSocket is closed.
    *
    * Actual [CloseEvent]{@link https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent}
    * is passed as parameter to the callback.
    """
    onWebSocketClose: CloseEventCallbackType = None

    """
    * Callback, invoked when underlying WebSocket raises an error.
    *
    * Actual [Event]{@link https://developer.mozilla.org/en-US/docs/Web/API/Event}
    * is passed as parameter to the callback.
    """
    onWebSocketError: WsErrorCallbackType = None

    """
    * Set it to log the actual raw communication with the broker.
    * When unset, it logs headers of the parsed frames.
    *
    * Changes effect from the next broker reconnect.
    *
    * **Caution: self assumes that frames only have valid UTF8 strings.**
    """
    logRawCommunication: bool = False

    """
    * By default, debug messages are discarded. To log to `console` following can be used:
    *
    * ```javascript
    *        client.debug = function(str) {
    *          console.log(str);
    *        };
    * ```
    *
    * Currently self method does not support levels of log. Be aware that the
    * output can be quite verbose
    * and may contain sensitive information (like passwords, tokens etc.).
    """
    debug: DebugFnType = None

    """
    * Browsers do not immediately close WebSockets when `.close` is issued.
    * self may cause reconnection to take a significantly long time in case
    *  of some types of failures.
    * In case of incoming heartbeat failure, self experimental flag instructs
    * the library to discard the socket immediately
    * (even before it is actually closed).
    """
    discardWebsocketOnCommFailure: bool = False

    """
    * version of STOMP protocol negotiated with the server, READONLY
    """

    @property
    def connectedVersion(self) -> str | None:
        return self._stompHandler.connectedVersion if self._stompHandler else None

    _stompHandler: StompHandler | None = None

    """
    * if the client is active (connected or going to reconnect)
    """

    @property
    def active(self) -> bool:
        return self.state == ActivationState.ACTIVE

    """
    * It will be called on state change.
    *
    * When deactivating, it may go from ACTIVE to INACTIVE without entering DEACTIVATING.
    """
    onChangeState: Callable[[ActivationState], None] = None

    def _changeState(self, state: ActivationState):
        self.state = state
        self.onChangeState(state)

    """
    * Activation state.
    *
    * It will usually be ACTIVE or INACTIVE.
    * When deactivating, it may go from ACTIVE to INACTIVE without entering DEACTIVATING.
    """
    state: ActivationState = ActivationState.INACTIVE

    _reconnector: Any = None

    """
    * Create an instance.
    """

    def __init__(self, conf: StompConfig = StompConfig()) -> None:
        # No op callbacks
        noOp = lambda: {}
        self.debug = DebugFnType(lambda s: None)
        self.beforeConnect = lambda: Promise()
        self.onConnect = FrameCallbackType(lambda f: None)
        self.onDisconnect = FrameCallbackType(lambda f: None)
        self.onUnhandledMessage = MessageCallbackType(lambda m: None)
        self.onUnhandledReceipt = FrameCallbackType(lambda f: None)
        self.onUnhandledFrame = FrameCallbackType(lambda f: None)
        self.onStompError = FrameCallbackType(lambda f: None)
        self.onWebSocketClose = CloseEventCallbackType(lambda f: None)
        self.onWebSocketError = WsErrorCallbackType(lambda f: None)
        self.logRawCommunication = False
        self.onChangeState = lambda e: None

        # These parameters would typically get proper values before connect is called
        self.connectHeaders = StompHeaders()
        self._disconnectHeaders = StompHeaders()

        # Apply configuration
        self.configure(conf)

    """
    * Update configuration.
    """

    def configure(self, conf: StompConfig):
        # bulk assign all properties to self
        self.brokerURL = conf.brokerURL
        self.stompVersions = conf.stompVersions if conf.stompVersions else self.stompVersions
        self.webSocketFactory = conf.webSocketFactory if conf.webSocketFactory else self.webSocketFactory
        self.connectionTimeout = conf.connectionTimeout if conf.connectionTimeout else self.connectionTimeout
        self.reconnectDelay = conf.reconnectDelay if conf.reconnectDelay else self.reconnectDelay
        self.heartbeatIncoming = conf.heartbeatIncoming if conf.heartbeatIncoming else self.heartbeatIncoming
        self.splitLargeFrames = conf.splitLargeFrames if conf.splitLargeFrames else self.splitLargeFrames
        self.forceBinaryWSFrames = conf.forceBinaryWSFrames if conf.forceBinaryWSFrames else self.forceBinaryWSFrames
        self.appendMissingNULLonIncoming = conf.appendMissingNULLonIncoming if conf.appendMissingNULLonIncoming else self.appendMissingNULLonIncoming
        self.maxWebSocketChunkSize = conf.maxWebSocketChunkSize if conf.maxWebSocketChunkSize else self.maxWebSocketChunkSize
        self.connectHeaders = conf.connectHeaders if conf.connectHeaders else self.connectHeaders
        self.disconnectHeaders = conf.disconnectHeaders if conf.disconnectHeaders else self.disconnectHeaders
        self.onUnhandledMessage = conf.onUnhandledMessage if conf.onUnhandledMessage else self.onUnhandledMessage
        self.onUnhandledReceipt = conf.onUnhandledReceipt if conf.onUnhandledReceipt else self.onUnhandledReceipt
        self.onUnhandledFrame = conf.onUnhandledFrame if conf.onUnhandledFrame else self.onUnhandledFrame
        self.beforeConnect = conf.beforeConnect if conf.beforeConnect else self.beforeConnect
        self.onConnect = conf.onConnect if conf.onConnect else self.onConnect
        self.onDisconnect = conf.onDisconnect if conf.onDisconnect else self.onDisconnect
        self.onStompError = conf.onStompError if conf.onStompError else self.onStompError
        self.onWebSocketClose = conf.onWebSocketClose if conf.onWebSocketClose else self.onWebSocketClose
        self.onWebSocketError = conf.onWebSocketError if conf.onWebSocketError else self.onWebSocketError
        self.logRawCommunication = conf.logRawCommunication if conf.logRawCommunication else self.logRawCommunication
        self.debug = conf.debug if conf.debug else self.debug
        self.discardWebsocketOnCommFailure = conf.discardWebsocketOnCommFailure if conf.discardWebsocketOnCommFailure else self.discardWebsocketOnCommFailure
        self.onChangeState = conf.onChangeState if conf.onChangeState else self.onChangeState

    """
    * Initiate the connection with the broker.
    * If the connection breaks, as per [Client#reconnectDelay]{@link Client#reconnectDelay},
    * it will keep trying to reconnect.
    *
    * Call [Client#deactivate]{@link Client#deactivate} to disconnect and stop reconnection attempts.
    """

    def activate(self):
        def _activate():
            if self.active:
                self.debug('Already ACTIVE, ignoring request to activate')
                return
            self._changeState(ActivationState.ACTIVE)
            asyncio.run(self._connect())

        # if it is deactivating, wait for it to complete before activating.
        if self.state == ActivationState.DEACTIVATING:
            self.debug('Waiting for deactivation to finish before activating')
            self.deactivate().then(lambda: _activate())

        else:
            _activate()

    async def _connect(self) -> Promise | None:
        await self.beforeConnect()
        if self._stompHandler:
            self.debug('There is already a stompHandler, skipping the call to connect')
            return None

        if not self.active:
            self.debug('Client has been marked inactive, will not attempt to connect')
            return None

        # setup connection watcher
        if self.connectionTimeout > 0:
            # clear first
            if self._connectionWatcher:
                clearTimeout(self._connectionWatcher)

            def doWatch():
                if self.connected:
                    return
                # Connection not established, close the underlying socket
                # a reconnection will be attempted
                self.debug(f"Connection not established in {self.connectionTimeout}ms, closing socket")
                self.forceDisconnect()

            self._connectionWatcher = setTimeout(doWatch, self.connectionTimeout)

        # Get the actual WebSocket (or a similar object)
        webSocket = self._createWebSocket()

        def onConnect(frame):
            # Successfully connected, stop the connection watcher
            if self._connectionWatcher:
                clearTimeout(self._connectionWatcher)
                self._connectionWatcher = None

            if not self.active:
                self.debug('STOMP got connected while deactivate was issued, will disconnect now')
                self._disposeStompHandler()
                return
            self.onConnect(frame)

        def onWebSocketClose(evt):
            self._stompHandler = None  # a new one will be created in case of a reconnect
            if self.state == ActivationState.DEACTIVATING:
                # Mark deactivation complete
                self._changeState(ActivationState.INACTIVE)
            # The callback is called before attempting to reconnect, self would allow the client
            # to be `deactivated` in the callback.
            self.onWebSocketClose(evt)
            if self.active:
                self._schedule_reconnect()

        self._stompHandler = StompHandler(self, webSocket, StomptHandlerConfig(
            debug=self.debug,
            stompVersions=self.stompVersions,
            connectHeaders=self.connectHeaders,
            disconnectHeaders=self._disconnectHeaders,
            heartbeatIncoming=self.heartbeatIncoming,
            heartbeatOutgoing=self.heartbeatOutgoing,
            splitLargeFrames=self.splitLargeFrames,
            maxWebSocketChunkSize=self.maxWebSocketChunkSize,
            forceBinaryWSFrames=self.forceBinaryWSFrames,
            logRawCommunication=self.logRawCommunication,
            appendMissingNULLonIncoming=self.appendMissingNULLonIncoming,
            discardWebsocketOnCommFailure=self.discardWebsocketOnCommFailure,
            onConnect=FrameCallbackType(onConnect),
            onDisconnect=FrameCallbackType(lambda frame: self.onDisconnect(frame)),
            onStompError=FrameCallbackType(lambda frame: self.onStompError(frame)),
            onWebSocketClose=CloseEventCallbackType(onWebSocketClose),
            onWebSocketError=WsErrorCallbackType(lambda evt: self.onWebSocketError(evt)),
            onUnhandledMessage=MessageCallbackType(lambda message: self.onUnhandledMessage(message)),
            onUnhandledReceipt=FrameCallbackType(lambda frame: self.onUnhandledReceipt(frame)),
            onUnhandledFrame=FrameCallbackType(lambda frame: self.onUnhandledFrame(frame))
        ))
        self._stompHandler.start()

    def _createWebSocket(self) -> IStompSocket:
        webSocket: IStompSocket
        if self.webSocketFactory:
            webSocket = self.webSocketFactory()
        elif self.brokerURL:
            webSocket = WebSocket(
                self.brokerURL,
                self.stompVersions.protocol_versions()
            )
        else:
            raise Exception('Either brokerURL or webSocketFactory must be provided')
        webSocket.binaryType = 'arraybuffer'
        return webSocket

    def _schedule_reconnect(self):
        if self.reconnectDelay > 0:
            self.debug(f"STOMP: scheduling reconnection in ${self.reconnectDelay}ms")
        self._reconnector = setTimeout(lambda: self._connect(), self.reconnectDelay)

    """
    * Disconnect if connected and stop auto reconnect loop.
    * Appropriate callbacks will be invoked if there is an underlying STOMP connection.
    *
    * self call is async. It will resolve immediately if there is no underlying active websocket,
    * otherwise, it will resolve after the underlying websocket is properly disposed of.
    *
    * It is not an error to invoke self method more than once.
    * Each of those would resolve on completion of deactivation.
    *
    * To reactivate, you can call [Client#activate]{@link Client#activate}.
    *
    * Experimental: pass `force: true` to immediately discard the underlying connection.
    * self mode will skip both the STOMP and the Websocket shutdown sequences.
    * In some cases, browsers take a long time in the Websocket shutdown
    * if the underlying connection had gone stale.
    * Using self mode can speed up.
    * When self mode is used, the actual Websocket may linger for a while
    * and the broker may not realize that the connection is no longer in use.
    *
    * It is possible to invoke self method initially without the `force` option
    * and subsequently, say after a wait, with the `force` option.
    """

    def deactivate(self, options: DeativateOptions = DeativateOptions()) -> Promise:
        force: bool = options.force
        needToDispose = self.active
        retPromise: Promise

        if self.state == ActivationState.INACTIVE:
            self.debug(f"Already INACTIVE, nothing more to do")
            return Promise()

        self._changeState(ActivationState.DEACTIVATING)

        # Clear if a reconnection was scheduled
        if self._reconnector:
            clearTimeout(self._reconnector)
            self._reconnector = None

        if self._stompHandler and self.webSocket.readyState != StompSocketState.CLOSED:
            origOnWebSocketClose = self._stompHandler.onWebSocketClose

            # we need to wait for the underlying websocket to close
            def promiseFun(resolve, reject):
                def onWebSocketClose(evt):
                    origOnWebSocketClose(evt)
                    resolve()

                self._stompHandler.onWebSocketClose = onWebSocketClose

            retPromise = Promise(promiseFun)
        else:
            # indicate that auto reconnect loop should terminate
            self._changeState(ActivationState.INACTIVE)
            return Promise()
        if force:
            if self._stompHandler:
                self._stompHandler.discardWebsocket()
        elif needToDispose:
            self._disposeStompHandler()
        return retPromise

    """
    * Force disconnect if there is an active connection by directly closing the underlying WebSocket.
    * self is different from a normal disconnect where a DISCONNECT sequence is carried out with the broker.
    * After forcing disconnect, automatic reconnect will be attempted.
    * To stop further reconnects call [Client#deactivate]{@link Client#deactivate} as well.
    """

    def forceDisconnect(self):
        if self._stompHandler:
            self._stompHandler.forceDisconnect()

    def _disposeStompHandler(self):
        # Dispose STOMP Handler
        if self._stompHandler:
            self._stompHandler.dispose()

    """
    * Send a message to a named destination. Refer to your STOMP broker documentation for types
    * and naming of destinations.
    *
    * STOMP protocol specifies and suggests some headers and also allows broker-specific headers.
    *
    * `body` must be String.
    * You will need to covert the payload to string in case it is not string (e.g. JSON).
    *
    * To send a binary message body, use `binaryBody` parameter. It should be a
    * [Uint8Array](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Uint8Array).
    * Sometimes brokers may not support binary frames out of the box.
    * Please check your broker documentation.
    *
    * `content-length` header is automatically added to the STOMP Frame sent to the broker.
    * Set `skipContentLengthHeader` to indicate that `content-length` header should not be added.
    * For binary messages, `content-length` header is always added.
    *
    * Caution: The broker will, most likely, report an error and disconnect
    * if the message body has NULL octet(s) and `content-length` header is missing.
    *
    * ```javascript
    *        client.publish({destination: "/queue/test", headers: {priority: 9}, body: "Hello, STOMP"});
    *
    *        // Only destination is mandatory parameter
    *        client.publish({destination: "/queue/test", body: "Hello, STOMP"});
    *
    *        // Skip content-length header in the frame to the broker
    *        client.publish({"/queue/test", body: "Hello, STOMP", skipContentLengthHeader: true});
    *
    *        var binaryData = generateBinaryData(); // self need to be of type Uint8Array
    *        // setting content-type header is not mandatory, however a good practice
    *        client.publish({destination: '/topic/special', binaryBody: binaryData,
    *                         headers: {'content-type': 'application/octet-stream'}});
    * ```
    """

    def publish(self, params: IPublishParams):
        self._checkConnection()
        # @ts-ignore - we already checked that there is a _stompHandler, and it is connected
        self._stompHandler.publish(params)

    def _checkConnection(self):
        if not self.connected:
            raise TypeError('There is no underlying STOMP connection')

    """
    * STOMP brokers may carry out operation asynchronously and allow requesting for acknowledgement.
    * To request an acknowledgement, a `receipt` header needs to be sent with the actual request.
    * The value (say receipt-id) for self header needs to be unique for each use.
    * Typically, a sequence, a UUID, a random number or a combination may be used.
    *
    * A complaint broker will send a RECEIPT frame when an operation has actually been completed.
    * The operation needs to be matched based on the value of the receipt-id.
    *
    * self method allows watching for a receipt and invoking the callback
    *  when the corresponding receipt has been received.
    *
    * The actual {@link IFrame} will be passed as parameter to the callback.
    *
    * Example:
    * ```javascript
    *        // Subscribing with acknowledgement
    *        let receiptId = randomText();
    *
    *        client.watchForReceipt(receiptId, function() {
    *          // Will be called after server acknowledges
    *        });
    *
    *        client.subscribe(TEST.destination, onMessage, {receipt: receiptId});
    *
    *
    *        // Publishing with acknowledgement
    *        receiptId = randomText();
    *
    *        client.watchForReceipt(receiptId, function() {
    *          // Will be called after server acknowledges
    *        });
    *        client.publish({destination: TEST.destination, headers: {receipt: receiptId}, body: msg});
    * ```
    """

    def watchForReceipt(self, receiptId: str, callback: FrameCallbackType):
        self._checkConnection()
        # @ts-ignore - we already checked that there is a _stompHandler, and it is connected
        self._stompHandler.watchForReceipt(receiptId, callback)

    """
    * Subscribe to a STOMP Broker location. The callback will be invoked for each
    * received message with the {@link IMessage} as argument.
    *
    * Note: The library will generate a unique ID if there is none provided in the headers.
    *       To use your own ID, pass it using the `headers` argument.
    *
    * ```javascript
    *        callback = function(message) {
    *        // called when the client receives a STOMP message from the server
    *          if (message.body) {
    *            alert("got message with body " + message.body)
    *          } else {
    *            alert("got empty message");
    *          }
    *        });
    *
    *        var subscription = client.subscribe("/queue/test", callback);
    *
    *        // Explicit subscription id
    *        var mySubId = 'my-subscription-id-001';
    *        var subscription = client.subscribe(destination, callback, { id: mySubId });
    * ```
    """

    def subscribe(
            self,
            destination: str,
            callback: MessageCallbackType,
            headers: StompHeaders = StompHeaders()
    ) -> StompSubscription:
        self._checkConnection()
        # @ts-ignore - we already checked that there is a _stompHandler, and it is connected
        return self._stompHandler.subscribe(destination, callback, headers)

    """
    * It is preferable to unsubscribe from a subscription by calling
    * `unsubscribe()` directly on {@link StompSubscription} returned by `client.subscribe()`:
    *
    * ```javascript
    *        var subscription = client.subscribe(destination, onmessage);
    *        // ...
    *        subscription.unsubscribe();
    * ```
    *
    * See: https://stomp.github.com/stomp-specification-1.2.html#UNSUBSCRIBE UNSUBSCRIBE Frame
    """

    def unsubscribe(self, id: str, headers: StompHeaders = StompHeaders()):
        self._checkConnection()
        # @ts-ignore - we already checked that there is a _stompHandler, and it is connected
        self._stompHandler.unsubscribe(id, headers)

    """
    * Start a transaction, the returned ITransaction has methods - [commit]{@link ITransaction#commit}
    * and [abort]{@link ITransaction#abort}.
    *
    * `transactionId` is optional, if not passed the library will generate it internally.
    """

    def begin(self, transactionId: str = None) -> ITransaction:
        self._checkConnection()
        # @ts-ignore - we already checked that there is a _stompHandler, and it is connected
        return self._stompHandler.begin(transactionId)

    """
    * Commit a transaction.
    *
    * It is preferable to commit a transaction by calling [commit]{@link ITransaction#commit} directly on
    * {@link ITransaction} returned by [client.begin]{@link Client#begin}.
    *
    * ```javascript
    *        var tx = client.begin(txId);
    *        //...
    *        tx.commit();
    * ```
    """

    def commit(self, transactionId: str):
        self._checkConnection()
        # @ts-ignore - we already checked that there is a _stompHandler, and it is connected
        self._stompHandler.commit(transactionId)

    """
    * Abort a transaction.
    * It is preferable to abort a transaction by calling [abort]{@link ITransaction#abort} directly on
    * {@link ITransaction} returned by [client.begin]{@link Client#begin}.
    *
    * ```javascript
    *        var tx = client.begin(txId);
    *        //...
    *        tx.abort();
    * ```
    """

    def abort(self, transactionId: str):
        self._checkConnection()
        # @ts-ignore - we already checked that there is a _stompHandler, and it is connected
        self._stompHandler.abort(transactionId)

    """
    * ACK a message. It is preferable to acknowledge a message by calling [ack]{@link IMessage#ack} directly
    * on the {@link IMessage} handled by a subscription callback:
    *
    * ```javascript
    *        var callback = function (message) {
    *          // process the message
    *          // acknowledge it
    *          message.ack();
    *        };
    *        client.subscribe(destination, callback, {'ack': 'client'});
    * ```
    """

    def ack(
            self,
            messageId: str,
            subscriptionId: str,
            headers: StompHeaders = StompHeaders()
    ):
        self._checkConnection()
        # @ts-ignore - we already checked that there is a _stompHandler, and it is connected
        self._stompHandler.ack(messageId, subscriptionId, headers)

    """
    * NACK a message. It is preferable to acknowledge a message by calling [nack]{@link IMessage#nack} directly
    * on the {@link IMessage} handled by a subscription callback:
    *
    * ```javascript
    *        var callback = function (message) {
    *          // process the message
    *          // an error occurs, nack it
    *          message.nack();
    *        };
    *        client.subscribe(destination, callback, {'ack': 'client'});
    * ```
    """

    def nack(
            self,
            messageId: str,
            subscriptionId: str,
            headers: StompHeaders = StompHeaders()
    ):
        self._checkConnection()
        # @ts-ignore - we already checked that there is a _stompHandler, and it is connected
        self._stompHandler.nack(messageId, subscriptionId, headers)
