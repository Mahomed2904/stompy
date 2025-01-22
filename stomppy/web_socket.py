import threading
import time
from typing import List
import websocket

from stomppy.ltypes import IStompSocket, StompSocketState, StompSocketMessageEvent


class WebSocket(IStompSocket):

    def __init__(self, url: str, protocols: str | List[str] | None):
        self.url = url
        self.protocols = protocols
        self.ws = websocket.WebSocketApp(self.url, header={})
        self.ws.on_open = self._on_open
        self.ws.on_message = self._on_message
        self.ws.on_close = self._on_close
        self.ws.on_error = self._on_error
        self.thread = threading.Thread(target=self.run_websocket, name="Web socket thread")
        self.readyState = StompSocketState.CONNECTING
        self.thread.start()
        threading.Thread(target=self._look_timeout, name="Check timeout thread", args=(5000,)).start()

    def run_websocket(self):
        self.ws.run_forever()

    def _look_timeout(self, timeout=0):
        total_ms = 0
        while self.readyState != StompSocketState.OPEN:
            time.sleep(.10)
            total_ms += 250
            if 0 < timeout < total_ms:
                raise TimeoutError(f"Connection to {self.url} timed out")

    def _on_open(self, ws_app, *args):
        self.readyState = StompSocketState.OPEN
        if self.onopen:
            self.onopen(ws_app)

    def _on_close(self, ws_app, *args):
        self.readyState = StompSocketState.CLOSED
        # print("Whoops! Lost connection to " + self.ws.url)
        if self.onclose:
            self.onclose(ws_app)
        self._clean_up()

    def _on_error(self, ws_app, error, *args):
        # print(error, args)
        if self.onerror:
            self.onerror(ws_app)

    def _clean_up(self):
        self.readyState = StompSocketState.CLOSED

    def _on_message(self, ws_app, message, *args):
        if self.onmessage:
            self.onmessage(StompSocketMessageEvent(message))

    def send(self, data: str | bytes):
        self.ws.send(data)

    def close(self):
        self.readyState = StompSocketState.CLOSING
        self.ws.close()

