import copy
import datetime
import random
from typing import Callable

from stomppy.rtypes import EventParams
from stomppy.ltypes import IStompSocket

"""
 * @internal
"""


def augmentWebsocket(webSocket: IStompSocket,
                     debug: Callable[[str], None]):
    def terminate(self):
        noOp = lambda: {}
        self.onerror = noOp
        self.onmessage = noOp
        self.onopen = noOp

        ts = datetime.datetime.now()
        id = str(random.random())[2:8]
        webSocketCopy = copy.deepcopy(webSocket)

        def onclose(closeEvent):
            delay = datetime.datetime.now().timestamp() - ts.timestamp()
            debug(
                f"Discarded socket(#{id})  closed after {delay}ms, with code/reason: {closeEvent.code}/{closeEvent.reason}"
            )
        self.onclose = onclose
        self.close()

        webSocketCopy.onclose(EventParams(
            code=4001,
            reason=f"Quick discarding socket(  # ${id}) without waiting for the shutdown sequence.",
            wasClean=False))

    webSocket.terminate = terminate
