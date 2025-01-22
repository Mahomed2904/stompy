import json
import time

from src import stomppy
from src.stomppy import PublishParams, DebugFnType

stompClient = stomppy.Client(
    stomppy.StompConfig(brokerURL='ws://localhost:8080/gs-guide-websocket',
                        debug=DebugFnType(lambda msg: print(msg)))
)

def onConnect(frame):
    print('Connected: ' + str(frame))
    stompClient.subscribe('/topic/greetings', lambda greeting: print(greeting.body))
stompClient.onConnect = onConnect

stompClient.onWebSocketError = lambda error: print('Error with websocket', error)

stompClient.onStompError = lambda frame: (print('Broker reported error: ' + frame.headers['message']),
                                          print('Additional details: ' + frame.body))


def connect():
    stompClient.activate()


def disconnect():
    stompClient.deactivate()


def sendName(name: str):
    stompClient.publish(PublishParams(
        destination="/app/hello",
        body=json.dumps({"name": name})
    ))


connect()
sendName("Mahomed")
sendName("John Doe")
sendName("Carla Andego")
sendName("Carla Andego")
sendName("Carla Andego")
time.sleep(1.1)
disconnect()
