import asyncio
import queue
import threading
from typing import List, Tuple, Callable, Any, Union, ByteString


class Uint8Array(bytes):
    pass


class ArrayBuffer(List[int]):
    pass


class Promise:

    def __init__(self, function: Callable[[Any, ...], Any] | Callable[[], Any] = None):
        self._function = function
        self._result: Any = None
        self.run = False
        self._thread = None
        self.try_to_run_thread()

    def __await__(self):
        self.try_to_run_thread()

        async def auxiliar():
            if self._thread is not None and self._thread.is_alive():
                self._thread.join()
            return self._result
        return auxiliar().__await__()

    def try_to_run_thread(self):
        if self._thread is None and self._function is not None:
            self._thread = threading.Thread(target=self.run_function, daemon=True)
            self._thread.start()

    def run_function(self):
        self._result = self._function(lambda: None, lambda: None)

    def then(self, resolve: Union[Callable[[Any], Any], Callable[[], Any]] = None,
             reject: Union[Callable[[Any], Any], Callable[[], Any]] = None):
        self.try_to_run_thread()
        threading.Thread(target=self.collect_results, args=(resolve, reject), daemon=True).start()
        return self

    def collect_results(self, resolve: Union[Callable[[Any], Any], Callable[[], Any]] = None,
                        reject: Union[Callable[[Any], Any], Callable[[], Any]] = None):
        print("Start function")
        try:
            if self._thread is not None and self._thread.is_alive():
                self._thread.join()
            if resolve is not None:
                resolve(self._result)
        except Exception as e:
            if reject is not None:
                reject(e)
        print("End function")


class EventParams:
    code: int
    reason: str
    wasClean: bool

    def __init__(self, code: int, reason: str, wasClean: bool):
        self.code = code
        self.reason = reason
        self.wasClean = wasClean


class DeativateOptions:
    force: bool = False

    def __init__(self, force: bool = False):
        self.force = force

