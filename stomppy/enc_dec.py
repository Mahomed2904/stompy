from stomppy.rtypes import Uint8Array


class TextEncoder:

    @staticmethod
    def encode(data: str) -> Uint8Array:
        return Uint8Array(data.encode('utf-8'))


class TextDecoder:

    @staticmethod
    def decode(data: Uint8Array) -> str:
        return bytes(data).decode("utf-8")
