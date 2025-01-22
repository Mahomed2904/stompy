from typing import Callable

from src.stomppy.stomp_headers import StompHeaders

"""
 * Call [Client#subscribe]{@link Client#subscribe} to create a StompSubscription.
 *
 * Part of `@stomp/stompjs`.
"""


class StompSubscription:
    """
    * Id associated with this subscription.
    """
    id: str

    """
    * Unsubscribe. See [Client#unsubscribe]{@link Client#unsubscribe} for an example.
    """
    unsubscribe: Callable[[StompHeaders | None], None]

    def __init__(self, id: str, unsubscribe: Callable[[StompHeaders | None], None]):
        self.id = id
        self.unsubscribe = unsubscribe


