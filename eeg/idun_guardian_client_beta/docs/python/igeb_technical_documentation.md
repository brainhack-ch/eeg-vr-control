# Documentation of the Python SDK

Technical documentation of the Python SDK

![Python SDK Overview](figs/Python_SDK_overview.png)

## Release Version and features

| Features      | Doc Version    | Date updated |
|--------------|-----------|------------|
| BLE, API, Download, Recording |   v0.1  |  17th Oct 2022      |

## Software requirements

The Python SDK runs (and was tested) on the following operating systems and has the following software requirements:
| Features      | Doc Version    | Date updated |
|--------------|-----------|------------|
| W |   v0.1  |  17th Oct 2022      |

---

## Introduction

This documentation describes the functionalities of the Python SDK for the IDUN Guardian Earbud. The Python SDK has the goal to establish the communication (or acts as a bridge) between the earbud and the cloud platform. Specifically, it consumes data from the earbud via Bluetooth Low Energy 4.2 (BLE) and forwards the decrypted data package from the BLE to the cloud through a websocket connection. The Python SDK is designed to be used by researchers/engineers who are familiar with hands-on coding and who want to build their own application and extend the python SDK to their own purpose.

---

## Python SDK - Communication Flow

The basic communication in the Python SDK starts with the instantiation of the client class (`client.py`). Based on a user's example script (e.g., `record_data.py` ) composed of two main components: the BLE component and the Websocket component. The BLE component is responsible for establishing the BLE connection with the earbud and receiving the data package from the earbud. In addition, it also allows to send commands to the device dependent which functionality is required. The Websocket component is responsible for establishing the websocket connection with the cloud platform and sending the data package to the cloud platform.

### Recording data with the Python SDK

![Python SDK - Recording data](figs/sequence_diagram_recording.jpg )
 ***Python SDK - Recording data**. Depiction of the communication flow of the **Recording function** as visualized in the sequence diagram. Particularly, Numberings in the figure represent the sequential steps (ordered from 1) of communication.*

### Downloading data with the Python SDK

![Python SDK - Downloading data](figs/sequence_diagram_download.jpg) ***Python SDK - Download data**. Depiction of the communication flow of the **Download function** as visualized in the sequence diagram. Numberings in the figure represent the sequential steps (ordered from 1) of communication.*

### Bidirectional streaming with the python SDK

![Python SDK - Streaming data](figs/sequence_diagram_bidirectional.jpg) ***Python SDK - Streaming data**. Depiction of the communication flow of the **Streaming function** as visualized in the sequence diagram. Numberings in the figure represent the sequential steps (ordered from 1) of communication.*

## BLE specification

Here is a short description of the Bluetooth specifications which is used to interact with the IDUN Guardian earbuds.
For more detailed information on the latest version of the BLE specification or the interface in general please refer to the hardware manual. [Link to hardware manual](https://github.com/iduntech/idn-guardian-hardware-manual)

For the current version of the implementation of the BLE communication, we use this

```bash
# IDUN Guardian Earbud - BLE characteristic

STARTBYTE=0xF0
ENDBYTE=0x0F

# BLE characteristic UUID
UUID_MEAS_EEGIMU=beffd56c-c915-48f5-930d-4c1feee0fcc4
UUID_MEAS_EEG=beffd56c-c915-48f5-930d-4c1feee0fcc5
UUID_MEAS_IMP=beffd56c-c915-48f5-930d-4c1feee0fcc8
UUID_DEVICE_SERVICE=0000180a-0000-1000-8000-00805f9b34fb
UUID_BATTERY_ID=00002a19-0000-1000-8000-00805f9b34fb

# BLE characteristic properties for sending commands to the earbud
UUID_CMD=beffd56c-c915-48f5-930d-4c1feee0fcca

# BLE characteristic properties for starting and stopping the recording
START_CMD=M #'\x62' #b -> start measurement
STOP_CMD=S # '\x73' #s -> stop measurement

# BLE characteristic properties for starting and stopping the impedance
START_IMP_CMD=Z # '\x7a' #z -> start impedance
STOP_IMP_CMD=X # '\x78' #x -> stop impedance
```

---

## Function overview

The Python SDK provides the following functionalities (seperated in each class):

- Guardian client - main wrapper using BLE and API class - [Client.py]()
  - `search_device`
  - `connect`
  - `record`
  - `download`

- Main BLE logic: **igeb_bluetooth.py**
- Main API logic: **igeb_api.py**



---

## Sequence diagram

---

## Data model

- Format of the JSON message that is being sent to the AWS cloud via websocket connection

```python
Message = {
    'deviceTimestamp': str, # ISO 8601 format with ms accuracy and tz offset
    'deviceID' : str,
    'connectionID' : str(UUID),
    'payload': bytearray #Devicepacket - byte package encoded (base64),
    'stop': bool
}
```


- Sample of the data package
```python
Devicepacket ={
    'ch1': [1 x 20] array
    'ch2': [1 x 20] array
    'acc': [3 x 20] array
    'gyro': [3 x 20] array
    'mag': [3 x 20] array
}

- Size of single package
  - 404 bytes

- **size estimation**
- 50 * 404 Bytes =  20 KiloBytes per package (20 samples)
- 20 kb * 12.5 = 250 KiloBytes per second (250 samples per second)
- 250 KiloBytes * 60 * 60 = 900 MB per hour → 9 GB for 10 hours*

```
