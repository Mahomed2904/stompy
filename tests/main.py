import json
import time

from src import stomppy
from src.stomppy import PublishParams, DebugFnType, MessageCallbackType, FrameCallbackType

stompClient = stomppy.Client(
    stomppy.StompConfig(brokerURL='ws://localhost:8080/api/coral-websocket',
                        debug=DebugFnType(lambda msg: print(msg)),
                        onStompError=FrameCallbackType(lambda msg: print(msg)),
                        connectHeaders=stomppy.StompHeaders({"Authorization": "Bearer eyJhbGciOiJIUzM4NCJ9.eyJzdWIiOiJuYWNhbGEiLCJpYXQiOjE3NTA3ODM4OTgsImV4cCI6MTc1MDc4NzQ5OH0.dzPP3JptRHaeqHaQSJc4Ou5xK3qxbGoU1NWAj9oxSwm0qlR_hd7NduExi0CNvE3X"}))
)


def onConnect(frame):
    print('Connected: ' + str(frame))
    stompClient.subscribe('/topic/sync-feedback', MessageCallbackType(lambda greeting: print(greeting.body)))
    stompClient.subscribe('/topic/data-synchronization', MessageCallbackType(lambda greeting: print(greeting.body)))


stompClient.onConnect = onConnect

stompClient.onWebSocketError = lambda error: print('Error with websocket', error)

stompClient.onStompError = lambda frame: (print('Broker reported error: ' + frame.headers['message']),
                                          print('Additional details: ' + frame.body))


def connect():
    stompClient.activate()


def disconnect():
    stompClient.deactivate()


def sendName():
    stompClient.publish(PublishParams(
        destination="/app/data-resumes/sync",
        body=json.dumps(
            {
                "id": 1,
                "action": "EDIT",
                "data": {
                    "id": 1,
                    "name": "TOTAL_NUMBER_OF_CAPTURED_IMAGES",
                    "value": 3
                },
                "tableName": "data_resume"
            }
        )
    ))


connect()

time.sleep(10)

try:
    sendName()
except Exception:
    pass

time.sleep(5)

disconnect()
