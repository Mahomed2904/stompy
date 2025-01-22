from typing import Callable
import traceback

from src.stomppy.ltypes import IRawFrameType, RawHeaderType
from src.stomppy.enc_dec import TextEncoder, TextDecoder
from src.stomppy.rtypes import ArrayBuffer, Uint8Array

"""
 * @internal
"""
NULL = 0
"""
 * @internal
"""
LF = 10
"""
 * @internal
"""
CR = 13
"""
 * @internal
"""
COLON = 58

"""
 * self is an evented, rec descent parser.
 * A stream of Octets can be passed and whenever it recognizes
 * a complete Frame or an incoming ping it will invoke the registered callbacks.
 *
 * All incoming Octets are fed into _onByte function.
 * Depending on current state the _onByte function keeps changing.
 * Depending on the state it keeps accumulating into _token and _results.
 * State is indicated by current value of _onByte, all states are named as _collect.
 *
 * STOMP standards https://stomp.github.io/stomp-specification-1.2.html
 * imply that all lengths are considered in bytes (instead of string lengths).
 * So, before actual parsing, if the incoming data is String it is converted to Octets.
 * self allows faithful implementation of the protocol and allows NULL Octets to be present in the body.
 *
 * There is no peek function on the incoming data.
 * When a state change occurs based on an Octet without consuming the Octet,
 * the Octet, after state change, is fed again (_reinjectByte).
 * self became possible as the state change can be determined by inspecting just one Octet.
 *
 * There are two modes to collect the body, if content-length header is there then it by counting Octets
 * otherwise it is determined by NULL terminator.
 *
 * Following the standards, the command and headers are converted to Strings
 * and the body is returned as Octets.
 * Headers are returned as an array and not as Hash - to allow multiple occurrence of an header.
 *
 * self parser does not use Regular Expressions as that can only operate on Strings.
 *
 * It handles if multiple STOMP frames are given as one chunk, a frame is split into multiple chunks, or
 * any combination there of. The parser remembers its state (any partial frame) and continues when a new chunk
 * is pushed.
 *
 * Typically the higher level function will convert headers to Hash, handle unescaping of header values
 * (which is protocol version specific), and convert body to text.
 *
 * Check the parser.spec.js to understand cases that self parser is supposed to handle.
 *
 * Part of `@stomp/stompjs`.
 *
 * @internal
"""


class Parser:
    _encoder = TextEncoder()
    _decoder = TextDecoder()

    # @ts-ignore - it always has a value
    _results: IRawFrameType

    _token: ArrayBuffer = []
    _headerKey: str | None
    _bodyBytesRemaining: int | None

    # @ts-ignore - it always has a value
    _onByte: Callable[[int], None]

    def __init__(self, onFrame: Callable[[IRawFrameType], None],
                 onIncomingPing: Callable[[], None]):

        self.onFrame = onFrame
        self.onIncomingPing = onIncomingPing
        self._initState()

    def parseChunk(
            self,
            segment: str | Uint8Array,
            appendMissingNULLonIncoming: bool = False
    ):
        if type(segment).__name__ == 'str':
            chunk = ArrayBuffer(self._encoder.encode(segment))
        else:
            chunk = ArrayBuffer(segment)

        # See https://github.com/stomp-js/stompjs/issues/89
        # Remove when underlying issue is fixed.
        #
        # Send a NULL byte, if the last byte of a Text frame was not NULL.F
        if appendMissingNULLonIncoming and chunk[-1] != 0:
            chunkWithNull = ArrayBuffer()
            chunkWithNull.extend(chunk)
            chunkWithNull.append(0)
            chunk = chunkWithNull

        # tslint:disable-next-line:prefer-for-of
        for i in range(len(chunk)):
            byte = chunk[i]
            self._onByte(byte)

    # The following implements a simple Rec Descent Parser.
    # The grammar is simple and just one byte tells what should be the next state

    def _collectFrame(self, byte: int):
        if byte == NULL:
            # Ignore
            return
        if byte == CR:
            # Ignore CR
            return
        if byte == LF:
            # Incoming Ping
            self.onIncomingPing()
            return

        self._onByte = self._collectCommand
        self._reinjectByte(byte)

    def _collectCommand(self, byte: int):
        if byte == CR:
            # Ignore CR
            return
        if byte == LF:
            self._results.command = self._consumeTokenAsUTF8()
            self._onByte = self._collectHeaders
            return
        self._consumeByte(byte)

    def _collectHeaders(self, byte: int):
        if byte == CR:
            # Ignore CR
            return
        if byte == LF:
            self._setupCollectBody()
            return
        self._onByte = self._collectHeaderKey
        self._reinjectByte(byte)

    def _reinjectByte(self, byte: int):
        self._onByte(byte)

    def _collectHeaderKey(self, byte: int):
        if byte == COLON:
            self._headerKey = self._consumeTokenAsUTF8()
            self._onByte = self._collectHeaderValue
            return
        self._consumeByte(byte)

    def _collectHeaderValue(self, byte: int):
        if byte == CR:
            # Ignore CR
            return
        if byte == LF:
            self._results.headers.append(RawHeaderType((
                self._headerKey,
                self._consumeTokenAsUTF8()
            )))
            self._headerKey = None
            self._onByte = self._collectHeaders
            return
        self._consumeByte(byte)

    def _setupCollectBody(self):
        contentLengthHeader = [
            header for header in self._results.headers
            if header[0] == 'content-length'
        ]
        contentLengthHeader = contentLengthHeader[0] if len(contentLengthHeader) > 0 else None
        if contentLengthHeader:
            self._bodyBytesRemaining = int(contentLengthHeader[1])
            self._onByte = self._collectBodyFixedSize
        else:
            self._onByte = self._collectBodyNullTerminated

    def _collectBodyNullTerminated(self, byte: int):
        if byte == NULL:
            self._retrievedBody()
            return
        self._consumeByte(byte)

    def _collectBodyFixedSize(self, byte: int):
        # It is post decrement, so that we discard the trailing NULL octet
        currentBodyBytesRemaining = int(self._bodyBytesRemaining)
        self._bodyBytesRemaining -= 1
        if currentBodyBytesRemaining == 0:
            self._retrievedBody()
            return
        self._consumeByte(byte)

    def _retrievedBody(self):
        self._results.binaryBody = self._consumeTokenAsRaw()
        try:
            self.onFrame(self._results)
        except Exception as e:
            print("Ignoring an exception thrown by a frame handler. Original exception: ")
            traceback.print_exc()
        self._initState()

    # Rec Descent Parser helpers

    def _consumeByte(self, byte: int):
        self._token.append(byte)

    def _consumeTokenAsUTF8(self) -> str:
        return self._decoder.decode(self._consumeTokenAsRaw())

    def _consumeTokenAsRaw(self) -> Uint8Array:
        rawResult = self._token
        self._token = ArrayBuffer()
        return Uint8Array(rawResult)

    def _initState(self):
        self._results = IRawFrameType(
            command=None,
            headers=[],
            binaryBody=None
        )
        self._token = ArrayBuffer()
        self._headerKey = None
        self._onByte = self._collectFrame
