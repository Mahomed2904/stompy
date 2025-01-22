"""
 * A Transaction is created by calling [Client#begin]{@link Client#begin}
 *
 * Part of `@stomp/stomppy`.
 *
 * TODO: Example and caveat
"""
from abc import ABC
from typing import Callable


class ITransaction(ABC):
    """
    * You will need to access this to send, ack, or nack within this transaction.
    """
    id: str

    """
    * Commit this transaction. See [Client#commit]{@link Client#commit} for an example.
    """
    commit: Callable[[], None]

    """
    * Abort this transaction. See [Client#abort]{@link Client#abort} for an example.
    """
    abort: Callable[[], None]


class Transaction(ITransaction):

    def __init__(self, id: str, commit: Callable[[], None], abort: Callable[[], None]):
        self.id = id
        self.commit = commit
        self.abort = abort
