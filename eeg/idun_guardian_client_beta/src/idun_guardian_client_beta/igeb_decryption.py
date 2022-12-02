"""
Guardian API websocket utilities.
"""
import json
from dataclasses import dataclass
import datetime
import asyncio
import logging
from dotenv import load_dotenv
import csv

from .config import settings
from .decryption_utils import convert_encoded_data_to_dictionary

load_dotenv()


class GuardianDecryption:
    """Main Guardian Decryption client."""

    def __init__(self, debug: bool = True) -> None:
        """Initialize Guardian Decryption client.

        Args:
            debug (bool, optional): Enable debug logging. Defaults to True.
        """

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
            stop: Boolean to stop the streaming
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

    async def decrypt_data(
        self,
        data_queue: asyncio.Queue,
        device_id: str = "deviceMockID",
        recording_id: str = "dummy_recID",
    ) -> None:
        """Decrypt the data locally.

        Args:
            data_queue (asyncio.Queue): Data queue from the BLE client
            device_id (str, optional): Device ID. Defaults to "deviceMockID".
            recording_id (str, optional): Recording ID. Defaults to "dummy_recID".

        Raises:
            Exception: If the websocket connection fails
        """

        def log_first_message():
            if self.debug:
                logging.info("[DECRYPT]: First package sent")
                logging.info(
                    "[DECRYPT]: data_model.stop = %s",
                    data_model.stop,
                )
                logging.info(
                    "[DECRYPT]: data_model.deviceID = %s",
                    data_model.deviceID,
                )
                logging.info(
                    "[DECRYPT]: data_model.recordingID = %s",
                    data_model.recordingID,
                )

        def log_final_message():
            logging.info("[DECRYPT]: Last package sent")
            logging.info(
                "[DECRYPT]: data_model.stop = %s",
                data_model.stop,
            )
            logging.info(
                "[DECRYPT]: data_model.deviceID = %s",
                data_model.deviceID,
            )
            logging.info(
                "[DECRYPT]: data_model.recordingID = %s",
                data_model.recordingID,
            )
            logging.info("[DECRYPT]: Connection sucesfully terminated")
            logging.info("[DECRYPT]: Breaking inner loop of API client")

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

            # decrypt timestamp that is in .isoformat() and convert to seconds
            timestamp = datetime.datetime.fromisoformat(device_timestamp).timestamp()

            # do decryption
            decrypted_data = convert_encoded_data_to_dictionary(timestamp,data)

            if data is not None:
                data_model.payload = decrypted_data
            if device_timestamp is not None:
                data_model.deviceTimestamp = timestamp
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
                logging.info("[DECRYPT]: Device queue is empty, sending computer time")
                device_timestamp = datetime.datetime.now().astimezone().isoformat()
            else:
                logging.info(
                    "[DECRYPT]: Data queue is not empty, waiting for last timestamp"
                )
                package = await data_queue.get()
                (device_timestamp, _, _, _, _) = self.unpack_from_queue(package)

            if self.debug:
                logging.info("[DECRYPT]: Terminating connection")

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
                    logging.info("[DECRYPT]: Breakin DECRYPT client while loop")
                # await asyncio.sleep(5)
                break

            if self.debug:
                logging.info("[DECRYPT]: DECRYPTING data...")

            #websocket_resource_url = self.ws_identifier

            try:
                #async with websockets.connect(websocket_resource_url) as websocket:
                # log the websocket resource url
                self.first_message_check = True
                if self.debug:
                    # logging.info(
                    #     "[API]: Connected to websocket resource url: %s",
                    #     websocket_resource_url,
                    # )
                    logging.info("[DECRYPT]: Sending data to the decrypt")
                eeg_f = open('eeg.csv', 'w')
                imu_f = open('imu.csv', 'w')
                eeg_csv = csv.DictWriter(
                    eeg_f,
                    dialect="excel",
                    fieldnames=["timestamp", "ch1"],
                )
                imu_csv = csv.DictWriter(
                    imu_f,
                    dialect="excel",
                    fieldnames=[
                        "timestamp",
                        "acc_x",
                        "acc_y",
                        "acc_z",
                        "magn_x",
                        "magn_y",
                        "magn_z",
                        "gyro_x",
                        "gyro_y",
                        "gyro_z",
                    ],
                )
                eeg_csv.writeheader()
                imu_csv.writeheader()

                while True:
                    try:
                        # forward data to the cloud
                        await unpack_and_load_data()

                        #print("Sending to the decrypt ", asdict(data_model))
                        # print data.payload pretty
                        # print(json.dumps(data_model.payload, indent=4))

                        eeg_csv.writerows(data_model.payload["eeg"])
                        imu_csv.writerows(data_model.payload["imu"])

                        # await websocket.send(json.dumps(asdict(data_model)))
                        # package_receipt = await websocket.recv()

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
                        # websockets.exceptions.ConnectionClosed,
                    ) as error:
                        if self.debug:
                            logging.info(
                                "[DECRYPT]: Interuption: %s",
                                error,
                            )
                        try:
                            if self.debug:
                                logging.info(
                                    "[DECRYPT]: Some error occured, trying to reconnect"
                                )
                            continue
                        except Exception as error:
                            if self.debug:
                                logging.info(
                                    "[DECRYPT]: Trying again in %s seconds",
                                    self.retry_time,
                                )
                            await asyncio.sleep(self.ping_timeout)
                            break

                    except asyncio.CancelledError as error:
                        eeg_f.close()
                        imu_f.close()
                        # async with websockets.connect(
                        #     websocket_resource_url
                        # ) as websocket:
                        if self.debug:
                            logging.info(
                                "[DECRYPT]: Error occured: %s",
                                error,
                            )
                        await unpack_and_load_data_termination()

                        print(json.dumps(data_model.payload, indent=4))
                        #decrypted_queue.
                        # await websocket.send(json.dumps(asdict(data_model)))
                        # package_receipt = await websocket.recv()

                        if self.debug:
                            log_final_message()
                        self.final_message_check = True
                        break

            except Exception as error:
                if self.debug:
                    logging.info(
                        "[DECRYPT]: Error occured: %s", error
                    )
                # await asyncio.sleep(self.retry_time)
                continue

        if self.debug:
            logging.info("[DECRYPT]: -----------  DECRYPT client is COMPLETED ----------- ")
            # TODO: receive response from websocket and handle it, later with bidirectional streaming

@dataclass
class GuardianDataModel:
    """Data model for Guardian data"""

    deviceTimestamp: float
    deviceID: str
    recordingID: str
    payload: dict  # This is a base64 encoded bytearray as a string
    impedance: int
    stop: bool
