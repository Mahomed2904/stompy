from stomppy.i_frame import IFrame
from stomppy.stomp_headers import StompHeaders
from typing import Callable

"""
 * Instance of Message will be passed to [subscription callback]{@link Client#subscribe}
 * and [Client#onUnhandledMessage]{@link Client#onUnhandledMessage}.
 * Since it is an extended {@link IFrame}, you can access [headers]{@link IFrame#headers}
 * and [body]{@link IFrame#body} as properties.
 *
 * Part of `@stomp/stomppy`.
 *
 * See [Client#subscribe]{@link Client#subscribe} for example.
"""


class IMessage(IFrame):
    """
    * When subscribing with manual acknowledgement, call this method on the message to ACK the message.
    *
    * See [Client#ack]{@link Client#ack} for an example.
    """
    ack: Callable[[StompHeaders], None] | None = None

    """
    * When subscribing with manual acknowledgement, call this method on the message to NACK the message.
    *
    * See [Client#nack]{@link Client#nack} for an example.
    """
    nack: Callable[[StompHeaders], None] | None = None


class Message(IMessage):

    def __init__(self, frame: IFrame):
        self.command = frame.command
        self.headers = frame.headers
        self.body = frame.body
        self.binaryBody = frame.binaryBody
        self.isBinaryBody = frame.isBinaryBody
        self.ack = None
        self.nack = None
