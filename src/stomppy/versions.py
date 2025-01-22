"""
 * Supported STOMP versions
 *
 * Part of `@stomp/stomppy`.
"""
from typing import List


class Versions:

    """
    * Indicates protocol version 1.0
    """
    V1_0 = '1.0'
    """
    * Indicates protocol version 1.1
    """
    V1_1 = '1.1'
    """
    * Indicates protocol version 1.2
    """
    V1_2 = '1.2'

    """
    * @internal
    """

    _default = None

    @staticmethod
    def default():
        if Versions._default is None:
            Versions._default = Versions([
                Versions.V1_2,
                Versions.V1_1,
                Versions.V1_0,
            ])
        return Versions._default

    """
    * Takes an array of versions, typical elements '1.2', '1.1', or '1.0'
    *
    * You will be creating an instance of this class if you want to override
    * supported versions to be declared during STOMP handshake.
    """

    def __init__(self, versions: List[str]):
        self.versions = versions

    """
    * Used as part of CONNECT STOMP Frame
    """

    def supported_versions(self) -> str:
        return ','.join(self.versions)

    """
    * Used while creating a WebSocket
    """

    def protocol_versions(self) -> List[str]:
        return [f"{x.replace('.', '')}.stomp" for x in self.versions]

