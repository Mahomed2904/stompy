from stomppy.byte import BYTE
from stomppy.i_frame import IFrame, FrameParams
from stomppy.stomp_headers import StompHeaders
from stomppy.rtypes import ArrayBuffer, Uint8Array
from stomppy.ltypes import IRawFrameType
from stomppy.enc_dec import TextDecoder, TextEncoder
import re

'''
 * Frame class represents a STOMP frame.
 *
 * @internal
'''


class FrameImpl(IFrame):
    """
    * STOMP Command
    """
    command: str

    '''
     * Headers, key value pairs.
    '''
    headers: StompHeaders

    '''
     * Is this frame binary (based on whether body/binaryBody was passed when creating this frame).
    '''
    isBinaryBody: bool

    '''
    * body of the frame
    '''
    @property
    def body(self) -> str:
        if not self._body and self.isBinaryBody:
            self._body = TextDecoder().decode(self._binaryBody)
        return self._body or ''

    _body: str | None = None

    '''
    * body as Uint8Array
    '''

    @property
    def binaryBody(self) -> Uint8Array:
        if not self._binaryBody and not self.isBinaryBody:
            self._binaryBody = TextEncoder().encode(self._body)

        # At this stage it will definitely have a valid value
        return self._binaryBody

    _binaryBody: Uint8Array | None = None
    escapeHeaderValues: bool = False
    skipContentLengthHeader: bool = False

    '''
     * Frame constructor. `command`, `headers` and `body` are available as properties.
     *
     * @internal
    '''
    def __init__(self, params: FrameParams):
        self.command = params.command
        self.headers = params.headers or StompHeaders()
        if params.binaryBody:
            self._binaryBody = params.binaryBody
            self.isBinaryBody = True
        else:
            self._body = params.body or ''
            self.isBinaryBody = False
        self.escapeHeaderValues = params.escapeHeaderValues or False
        self.skipContentLengthHeader = params.skipContentLengthHeader or False

    '''
     * deserialize a STOMP Frame from raw data.
     *
     * @internal
    '''
    @staticmethod
    def fromRawFrame(
            rawFrame: IRawFrameType,
            escapeHeaderValues: bool
    ):
        headers: StompHeaders = StompHeaders()
        trim = lambda data_str: re.sub(r"^\s+|\s+$", '', data_str)
        # In case of repeated headers, as per standards, first value need to be used
        rawFrame.headers.reverse()
        for header in rawFrame.headers:
            key = trim(header[0])
            value = trim(header[1])
            if (escapeHeaderValues and
                    rawFrame.command != 'CONNECT' and
                    rawFrame.command != 'CONNECTED'):
                value = FrameImpl._hdrValueUnEscape(value)
            headers[key] = value
        return FrameImpl(FrameParams(
            command=rawFrame.command, headers=headers,
            binaryBody=rawFrame.binaryBody,
            escapeHeaderValues=escapeHeaderValues))

    '''
     * @internal
    '''
    def __str__(self) -> str:
        return self._serializeCmdAndHeaders()

    '''
     * serialize this Frame in a format suitable to be passed to WebSocket.
     * If the body is string the output will be string.
     * If the body is binary (i.e. of type Unit8Array) it will be serialized to ArrayBuffer.
     *
     * @internal
    '''
    def serialize(self) -> str | Uint8Array:
        cmdAndHeaders = self._serializeCmdAndHeaders()
        if self.isBinaryBody:
            return FrameImpl._toUint8Array(
                    cmdAndHeaders,
                    self._binaryBody
                )
        else:
            return cmdAndHeaders + self._body + BYTE.NULL

    def _serializeCmdAndHeaders(self) -> str:
        lines = [self.command]
        if self.skipContentLengthHeader:
            del self.headers['content-length']
        for name in (self.headers or {}):
            value = self.headers[name]
            if (self.escapeHeaderValues and
                    self.command != 'CONNECT' and
                    self.command != 'CONNECTED'):
                lines.append(f"{name}:{FrameImpl._hdrValueEscape(f'{value}')}")
            else:
                lines.append(f"{name}:{value}")
        if (self.isBinaryBody or
                (not self._isBodyEmpty() and not self.skipContentLengthHeader)):
            lines.append(f"content-length:{self._bodyLength()}")
            lines.append(f"body:{self._body}")
        return BYTE.LF.join(lines) + BYTE.LF + BYTE.LF

    def _isBodyEmpty(self) -> bool:
        return self._bodyLength() == 0

    def _bodyLength(self) -> int:
        binaryBody = self.binaryBody
        return len(binaryBody) if binaryBody else 0

    '''
     * Compute the size of a UTF-8 string by counting its number of bytes
     * (and not the number of characters composing the string)
    '''
    @staticmethod
    def _sizeOfUTF8(s: str) -> int:
        return len(TextEncoder().encode(s)) if s else 0

    @staticmethod
    def _toUint8Array(
            cmdAndHeaders: str,
            binaryBody: Uint8Array
    ) -> Uint8Array:
        uint8CmdAndHeaders = TextEncoder().encode(cmdAndHeaders)
        nullTerminator = ArrayBuffer([0])
        uint8Frame = ArrayBuffer()
        uint8Frame.extend(uint8CmdAndHeaders)
        uint8Frame.extend(binaryBody)
        uint8Frame.extend(nullTerminator)
        return Uint8Array(uint8Frame)

    '''
     * Serialize a STOMP frame as per STOMP standards, suitable to be sent to the STOMP broker.
     *
     * @internal
    '''
    @staticmethod
    def marshall(params: FrameParams):
        frame = FrameImpl(params)
        return frame.serialize()

    '''
     *  Escape header values
    '''
    @staticmethod
    def _hdrValueEscape(data_str: str) -> str:
        return data_str
        # return re.sub(r':', '\\n',
        #               re.sub(r'\n', '\\n',
        #                      re.sub(r'\r', '\\r',
        #                             re.sub(r'\\', '\\\\', data_str))))

    '''
     * UnEscape header values
    '''
    @staticmethod
    def _hdrValueUnEscape(data_str: str) -> str:
        return data_str
        # return re.sub(r'\\\\', '\\',
        #               re.sub('\\n', ':',
        #                      re.sub(r'\\n', '\n',
        #                             re.sub(r'\\r', '\r', data_str))))

