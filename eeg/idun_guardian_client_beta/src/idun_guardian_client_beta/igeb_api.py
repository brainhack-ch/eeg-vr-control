"""
Guardian API websocket utilities.
"""
import os
import json
from dataclasses import dataclass, asdict
import socket
import datetime
import asyncio
import logging
import requests
import websockets
from dotenv import load_dotenv

from .config import settings

load_dotenv()


class GuardianAPI:
    """Main Guardian API client."""

    def __init__(self, debug: bool = True) -> None:
        """Initialize Guardian API client.

        Args:
            debug (bool, optional): Enable debug logging. Defaults to True.
        """
        self.ws_identifier = settings.WS_IDENTIFIER
        self.rest_api_get_url = settings.REST_API_URL_GET
        self.rest_api_login_url = settings.REST_API_LOGIN

        self.debug: bool = debug

        self.ping_timeout: int = 10
        self.retry_time: int = 5

        self.first_message_check = True
        self.final_message_check = False

        self.sentinal = object()

    def unpack_from_queue(self, package):
        """Unpack data from the queue filled with BLE data

        Args:
            package (dict): BLE data package

        Returns:
            timestamp: Timestamp of the data
            device_id: Device ID of the data
            data: Data from the BLE package
            stop: Boolean to stop the cloud streaming
            impedance: Impedance data
        """
        # check if "timestamp" is in the package
        if "timestamp" in package:
            timestamp = package["timestamp"]
        else:
            timestamp = None

        # chek if device_id is in the package
        if "device_id" in package:
            device_id = package["device_id"]
        else:
            device_id = None

        # check if "data" is in the package
        if "data" in package:
            data = package["data"]
        else:
            data = None

        # check if "type" is in the package
        if "stop" in package:
            stop = package["stop"]
        else:
            stop = None

        # check if impedance is in the package
        if "impedance" in package:
            impedance = package["impedance"]
        else:
            impedance = None

        return (timestamp, device_id, data, stop, impedance)

    async def connect_ws_api(
        self,
        data_queue: asyncio.Queue,
        device_id: str = "deviceMockID",
        recording_id: str = "dummy_recID",
    ) -> None:
        """Connect to the Guardian API websocket.

        Args:
            data_queue (asyncio.Queue): Data queue from the BLE client
            device_id (str, optional): Device ID. Defaults to "deviceMockID".
            recording_id (str, optional): Recording ID. Defaults to "dummy_recID".

        Raises:
            Exception: If the websocket connection fails
        """

        def log_first_message():
            if self.debug:
                logging.info("[API]: First package sent")
                logging.info(
                    "[API]: data_model.stop = %s",
                    data_model.stop,
                )
                logging.info(
                    "[API]: data_model.deviceID = %s",
                    data_model.deviceID,
                )
                logging.info(
                    "[API]: data_model.recordingID = %s",
                    data_model.recordingID,
                )
                logging.info(
                    "[API]: First package receipt: %s",
                    package_receipt,
                )

        def log_final_message():
            logging.info("[API]: Last package sent")
            logging.info(
                "[API]: data_model.stop = %s",
                data_model.stop,
            )
            logging.info(
                "[API]: data_model.deviceID = %s",
                data_model.deviceID,
            )
            logging.info(
                "[API]: data_model.recordingID = %s",
                data_model.recordingID,
            )
            logging.info(
                "[API]: Last package receipt: %s",
                package_receipt,
            )
            logging.info("[API]: Cloud connection sucesfully terminated")
            logging.info("[API]: Breaking inner loop of API client")

        async def unpack_and_load_data():
            """Get data from the queue and pack it into a dataclass"""
            package = await data_queue.get()
            (
                device_timestamp,
                device_id,
                data,
                stop,
                impedance,
            ) = self.unpack_from_queue(package)

            if data is not None:
                data_model.payload = data
            if device_timestamp is not None:
                data_model.deviceTimestamp = device_timestamp
            if device_id is not None:
                data_model.deviceID = device_id
            if stop is not None:
                data_model.stop = stop
            if impedance is not None:
                data_model.impedance = impedance

        async def unpack_and_load_data_termination():
            """Get data from the queue and pack it into a dataclass"""

            # check if the queue is empty
            if data_queue.empty():
                logging.info("[API]: Device queue is empty, sending computer time")
                device_timestamp = datetime.datetime.now().astimezone().isoformat()
            else:
                logging.info(
                    "[API]: Data queue is not empty, waiting for last timestamp"
                )
                package = await data_queue.get()
                (device_timestamp, _, _, _, _) = self.unpack_from_queue(package)

            if self.debug:
                logging.info("[API]: Terminating cloud connection")

            # check whether device_timestamp is None
            if device_timestamp is not None:
                data_model.deviceTimestamp = device_timestamp
            data_model.payload = "STOP_CANCELLED"
            data_model.stop = True

        self.first_message_check = True
        self.final_message_check = False

        # init data model
        data_model = GuardianDataModel(None, device_id, recording_id, None, None, False)

        while True:

            if self.final_message_check:
                if self.debug:
                    logging.info("[API]: Breakin API client while loop")
                # await asyncio.sleep(5)
                break

            if self.debug:
                logging.info("[API]: Connecting to WS API...")

            websocket_resource_url = self.ws_identifier

            try:
                async with websockets.connect(websocket_resource_url) as websocket:
                    # log the websocket resource url
                    self.first_message_check = True
                    if self.debug:
                        logging.info(
                            "[API]: Connected to websocket resource url: %s",
                            websocket_resource_url,
                        )
                        logging.info("[API]: Sending data to the cloud")
                    while True:
                        try:
                            # forward data to the cloud
                            await unpack_and_load_data()

                            # print("Sending to the cloud ", asdict(data_model))
                            await websocket.send(json.dumps(asdict(data_model)))
                            package_receipt = await websocket.recv()

                            if self.first_message_check:
                                self.first_message_check = False
                                if self.debug:
                                    log_first_message()

                            if data_model.stop:
                                if self.debug:
                                    log_final_message()
                                self.final_message_check = True
                                break

                        except (
                            asyncio.TimeoutError,
                            websockets.exceptions.ConnectionClosed,
                        ) as error:
                            if self.debug:
                                logging.info(
                                    "[API]: Interuption in sending data to the cloud: %s",
                                    error,
                                )
                            try:
                                if self.debug:
                                    logging.info(
                                        "[API]: ws client connection closed or asyncio Timeout"
                                    )
                                pong = await websocket.ping()
                                await asyncio.wait_for(pong, timeout=self.ping_timeout)
                                if self.debug:
                                    logging.info(
                                        "[API]: Ping successful, connection alive and continue.."
                                    )
                                print("Try to ping websocket successful")
                                continue
                            except Exception as error:
                                if self.debug:
                                    logging.info("[API]: Ping interuption: %s", error)
                                    logging.info(
                                        "[API]: Ping failed, connection closed"
                                    )
                                    logging.info(
                                        "[API]: Trying to reconnect in %s seconds",
                                        self.retry_time,
                                    )
                                await asyncio.sleep(self.ping_timeout)
                                break

                        except asyncio.CancelledError as error:
                            async with websockets.connect(
                                websocket_resource_url
                            ) as websocket:
                                if self.debug:
                                    logging.info(
                                        "[API]: Error in sending data to the cloud: %s",
                                        error,
                                    )
                                    logging.info(
                                        "[API]: Re-establishing cloud connection in exeption"
                                    )
                                    logging.info(
                                        "[API]: Fetching last package from queue"
                                    )
                                await unpack_and_load_data_termination()

                                # print("Sending to the cloud ", asdict(data_model))
                                await websocket.send(json.dumps(asdict(data_model)))
                                package_receipt = await websocket.recv()

                                if self.debug:
                                    log_final_message()
                                self.final_message_check = True
                                break

            except socket.gaierror as error:
                if self.debug:
                    logging.info(
                        "[API]: Interruption in connecting to the cloud: %s", error
                    )
                    logging.info(
                        "[API]: Retrying connection in %s sec ", self.retry_time
                    )
                await asyncio.sleep(self.retry_time)
                continue

            except ConnectionRefusedError as error:
                if self.debug:
                    logging.info(
                        "[API]: Interruption in connecting to the cloud: %s", error
                    )
                    logging.info(
                        "Cannot connect to API endpoint. Please check the URL and try again."
                    )
                    logging.info(
                        "Retrying connection in {} seconds".format(self.retry_time)
                    )
                await asyncio.sleep(self.retry_time)
                continue

        if self.debug:
            logging.info("[API]: -----------  API client is COMPLETED ----------- ")
            # TODO: receive response from websocket and handle it, later with bidirectional streaming

    def get_recordings_info_all(self, device_id: str = "mock-device-0", first_to_last = False) -> list:
        recordings_url = f"{self.rest_api_login_url}recordings"
        print(recordings_url)
        with requests.Session() as session:
            r = session.get(recordings_url, auth=(device_id, ""))
            if r.status_code == 200:
                print("Recording list retrieved successfully")
                recordings = r.json()
                recordings.sort(
                    key=lambda x: datetime.datetime.strptime(
                        x["startDeviceTimestamp"], "%Y-%m-%dT%H:%M:%S.%fZ"
                    ),
                    reverse=first_to_last,
                )
                print(json.dumps(recordings, indent=4, sort_keys=True))
                return r.json()
            else:
                print("Loading recording list failed")
                return []

    def get_recording_info_by_id(
        self, device_id: str, recording_id: str = "recordingId-0"
    ) -> list:
        recordings_url = f"{self.rest_api_login_url}recordings/{recording_id}"

        with requests.Session() as session:
            r = session.get(recordings_url, auth=(device_id, ""))
            if r.status_code == 200:
                print("Recording ID file found")
                print(r.json())
                return r.json()
            else:
                print("Recording not found")
                print(r.status_code)
                print(r.json())
                return []

    def download_recording_by_id(
        self, device_id: str, recording_id: str = "recordingId-0"
    ) -> None:

        recordings_folder_name = "recordings"
        recording_subfolder_name = recording_id
        # combine the folder name and subfolder name
        folder_path = os.path.join(recordings_folder_name, recording_subfolder_name)
        # create the folder if it doesn't exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # create subfolde
        recording_types = ["eeg", "imu"]

        for data_type in recording_types:
            with requests.Session() as session:

                record_url = f"{self.rest_api_login_url}recordings/{recording_id}/download/{data_type}"
                r = session.get(record_url, auth=(device_id, ""))
                if r.status_code == 200:
                    print(f"Recording ID file found, downloading {data_type} data")
                    print(r.json())
                    # get url from response
                    url = r.json()["downloadUrl"]
                    r = session.get(url)
                    filename = f"{recording_id}_{data_type}.csv"
                    # combine folder name and filename
                    file_path = os.path.join(folder_path, filename)
                    with open(file_path, "wb") as f:
                        # giving a name and saving it in any required format
                        # opening the file in write mode
                        f.write(r.content)

                    print("Downloading complete for recording ID: ", recording_id)
                else:
                    print("Data download failed")
                    print(r.status_code)
                    print(r.json())


@dataclass
class GuardianDataModel:
    """Data model for Guardian data"""

    deviceTimestamp: str
    deviceID: str
    recordingID: str
    payload: str  # This is a base64 encoded bytearray as a string
    impedance: int
    stop: bool
