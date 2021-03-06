"""
/*
 * Copyright 2010-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License").
 * You may not use this file except in compliance with the License.
 * A copy of the License is located at
 *
 *  http://aws.amazon.com/apache2.0
 *
 * or in the "license" file accompanying this file. This file is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 * express or implied. See the License for the specific language governing
 * permissions and limitations under the License.
 */
"""

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import argparse
import json
import os
import subprocess

AllowedActions = ['both', 'publish', 'subscribe']

pid = str(os.getpid())
pidFile = "/Oya/pid/mqtt"

file(pidFile, 'w').write(pid)

# Custom MQTT message callback
def customCallback(client, userdata, message):
    try:
        command=message.payload['command']
        if (command == "OTA"):
            subprocess.call(['sh','/Oya/ota/ota.sh'])
    except:
        print("Exception at custom callback")
        
    return

#subscribe
def mqttSubscribe(topic):
    myAWSIoTMQTTClient.subscribe(topic, 1, customCallback)
    time.sleep(2)

def get_state(s_file):
    try:
        file = open("/Oya/state/"+s_file, "r")
        ret = file.read()
    except Exception as inst:
        print("Error reading state file: "+s_file+" !", inst)
        return "ERR"
    else:
        try:
            r = ret.split()[0]
        except:
            return "ERR"
        else:
            return r

def get_info_recording(s_file):
    try:
        file = open("/Oya/recording/"+s_file, "r")
        ret = file.read()
    except Exception as inst:
        print("Error reading state file: "+s_file+" !", inst)
        return "ERR"
    else:
        try:
            r = ret.split()[0]
        except:
            return "ERR"
        else:
            return r

def get_info_uploading(s_file):
    try:
        file = open("/Oya/uploading/"+s_file, "r")
        ret = file.read()
    except Exception as inst:
        print("Error reading state file: "+s_file+" !", inst)
        return "ERR"
    else:
        try:
            r = ret.split()[0]
        except:
            return "ERR"
        else:
            return r

# Read in command-line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-e", "--endpoint", action="store", required=True, dest="host", help="Your AWS IoT custom endpoint")
parser.add_argument("-r", "--rootCA", action="store", required=True, dest="rootCAPath", help="Root CA file path")
parser.add_argument("-c", "--cert", action="store", dest="certificatePath", help="Certificate file path")
parser.add_argument("-k", "--key", action="store", dest="privateKeyPath", help="Private key file path")
parser.add_argument("-p", "--port", action="store", dest="port", type=int, help="Port number override")
parser.add_argument("-w", "--websocket", action="store_true", dest="useWebsocket", default=False,
                    help="Use MQTT over WebSocket")
parser.add_argument("-id", "--clientId", action="store", dest="clientId", default="basicPubSub",
                    help="Targeted client id")
parser.add_argument("-t", "--topic", action="store", dest="topic", default="sdk/test/Python", help="Targeted topic")
parser.add_argument("-m", "--mode", action="store", dest="mode", default="both",
                    help="Operation modes: %s"%str(AllowedActions))
parser.add_argument("-M", "--message", action="store", dest="message", default="Hello World!",
                    help="Message to publish")

args = parser.parse_args()
host = args.host
rootCAPath = args.rootCAPath
certificatePath = args.certificatePath
privateKeyPath = args.privateKeyPath
port = args.port
useWebsocket = args.useWebsocket
clientId = args.clientId
topic = args.topic

if args.mode not in AllowedActions:
    parser.error("Unknown --mode option %s. Must be one of %s" % (args.mode, str(AllowedActions)))
    exit(2)

if args.useWebsocket and args.certificatePath and args.privateKeyPath:
    parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
    exit(2)

if not args.useWebsocket and (not args.certificatePath or not args.privateKeyPath):
    parser.error("Missing credentials for authentication.")
    exit(2)

# Port defaults
if args.useWebsocket and not args.port:  # When no port override for WebSocket, default to 443
    port = 443
if not args.useWebsocket and not args.port:  # When no port override for non-WebSocket, default to 8883
    port = 8883

# Configure logging
logger = logging.getLogger("AWSIoTPythonSDK.core")
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

# Init AWSIoTMQTTClient
myAWSIoTMQTTClient = None
if useWebsocket:
    myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId, useWebsocket=True)
    myAWSIoTMQTTClient.configureEndpoint(host, port)
    myAWSIoTMQTTClient.configureCredentials(rootCAPath)
else:
    myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId)
    myAWSIoTMQTTClient.configureEndpoint(host, port)
    myAWSIoTMQTTClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTClient connection configuration
myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

# Connect and subscribe to AWS IoT
try:
    myAWSIoTMQTTClient.connect()
except Exception as inst:
    print("Exception at connect")

topic = "dummyres/status/"+clientId
subtopic="dummyres/command/"+clientId
mqttSubscribe(subtopic)
time.sleep(2)


# Publish to the same topic in a loop forever
loopCount = 0

while True:
    if args.mode == 'both' or args.mode == 'publish':
        message = {
        'DeviceID':"",
        'State':{},
        'Recording':{},
        'Uploading':{}
        }
        message['DeviceID'] = clientId
        message['State']['Uploading'] = get_state('uploading')
        message['State']['Recording'] = get_state('recording')
        message['State']['isLinked'] = get_state('islinked')
        message['State']['Mute'] = get_state('mute')
        message['Recording']['Destination'] = get_info_recording('destination')
        message['Recording']['Duration'] = get_info_recording('duration')
        message['Recording']['lastRecordedTime'] =  get_info_recording('lastRecordedTime')
        message['Uploading']['lastUploadedTime'] = get_info_uploading('lastUploadedTime')
        message['Uploading']['uploadURL'] = get_info_uploading('uploadURL')

        messageJson = json.dumps(message)
        try:
            myAWSIoTMQTTClient.publish(topic, messageJson, 1)
        except Exception as inst:
            print("Exception thrown at publish(): ", inst)
            try:
                myAWSIoTMQTTClient.connect()
                mqttSubscribe(subtopic)
                time.sleep(2)
                myAWSIoTMQTTClient.publish(topic, messageJson, 1)
            except:
                print("Exception")

    time.sleep(10)
