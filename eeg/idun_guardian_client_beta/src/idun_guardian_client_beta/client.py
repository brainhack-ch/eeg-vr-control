"""
Initialization of the IDUN Guardian Client
"""
import os
import asyncio
import logging
from datetime import datetime
from .igeb_bluetooth import GuardianBLE
from .igeb_decryption import GuardianDecryption
from .igeb_api import GuardianAPI
from .igeb_utils import check_platform, check_valid_mac, check_valid_uuid
import uuid


class GuardianClient:
    """
    Class object for the communication between Guardian Earbuds and Cloud API
    """

    def __init__(
        self,
        address: str = None,
        debug=True,
        debug_console=True,
    ) -> None:
        """Initialize the Guardian Client

        Args:
            address (str, optional): The MAC address of the Guardian Earbuds. Defaults to "00000000-0000-0000-0000-000000000000".
            debug (bool, optional): Enable debug logging. Defaults to True.
            debug_console (bool, optional): Enable debug logging to console. Defaults to True.

        Raises:
            ValueError: If the MAC address is not valid
        """
        self.is_connected = False
        self.debug = debug
        self.debug_to_console = debug_console
        if self.debug:
            if not os.path.exists("./logs"):
                os.makedirs("logs")
            datestr = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_filename = f"./logs/ble_info-{datestr}.log"
            # if directory does not exist, create it
            if not os.path.exists(os.path.dirname(log_filename)):
                os.makedirs(os.path.dirname(log_filename))
            log_handlers = [logging.FileHandler(log_filename)]

            if self.debug_to_console:
                log_handlers.append(logging.StreamHandler())
            logging.basicConfig(
                level=logging.INFO,
                datefmt="%d-%b-%y %H:%M:%S",
                format="%(asctime)s: %(name)s - %(levelname)s - %(message)s",
                handlers=log_handlers,
            )

        if address is not None:
            if self.check_ble_address(address):
                self.guardian_ble = GuardianBLE(address=address, debug=self.debug)
                self.address = address
        else:
            logging.info("No BLE address provided, will search for device...")
            print("No BLE address provided, will search for device..")
            self.guardian_ble = GuardianBLE(debug=self.debug)

        self.guardian_api = GuardianAPI(debug=self.debug)
        self.guardian_decryption = GuardianDecryption(debug=self.debug)

    def check_ble_address(self, address: str) -> bool:
        """Check if the BLE address is valid

        Args:
            address (str): The MAC address of the Guardian Earbuds

        Returns:
            bool: True if the address is valid, False otherwise
        """
        if (
            check_platform() == "Windows"
            or check_platform() == "Linux"
            and check_valid_mac(address)
        ):
            return True
        elif check_platform() == "Darwin" and check_valid_uuid(address):
            logging.info("Platform detected: Darwin")
            # print(f"UUID is valid for system Darwin: {address}")
            return True
        else:
            logging.error("Invalid BLE address")
            raise ValueError("Invalid BLE address")

    async def search_device(self):
        """Connect to the Guardian Earbuds

        Returns:
            is_connected: bool
        """

        self.address = await self.guardian_ble.search_device()

        return self.address

    async def get_device_address(self) -> str:
        """Get the MAC address of the Guardian Earbuds.
        It searches the MAC address of the device automatically. This
        address is used as the deviceID for cloud communication
        """
        device_address = await self.guardian_ble.get_device_mac()
        return device_address

    def start_stream(self):
        """Start streaming data from the Guardian Earbuds.
        Bidirectional websocket connection to the Guardian Cloud API.
        """
        pass

    async def stop_device(self):
        """Stop streaming data from the Guardian Earbuds"""
        await self.guardian_ble.stop_stream()

    async def start_recording(
        self,
        recording_timer: int = 36000,
        led_sleep: bool = False,
        experiment: str = "None provided",
    ):
        """
        Start recording data from the Guardian Earbuds.
        Unidirectional websocket connection to the Guardian Cloud API.

        Args:
            recording_timer (int, optional): The duration of the recording in seconds. Defaults to 36000.
            led_sleep (bool, optional): Enable LED sleep mode. Defaults to False.
            experiment (str, optional): The name of the experiment. Defaults to "None provided". This will
                                        go to the log file.

        Raises:
            ValueError: If the recording timer is not valid
        """
        if self.debug:
            logging.info(
                "[CLIENT]: Recording timer set to: %s seconds", recording_timer
            )
            logging.info("[CLIENT]: Start recording")

        print(f"[CLIENT]: Recording timer set to: {recording_timer} seconds")
        print("-----Recording starting------")

        data_queue: asyncio.Queue = asyncio.Queue(maxsize=86400)
        recording_id = str(
            uuid.uuid4()
        )  # the recordingID is a unique ID for each recording
        logging.info("[CLIENT] Recording ID: %s", recording_id)
        # log the experiment name in bold using the logging module
        logging.info("[CLIENT] Experiment description: %s", experiment)

        mac_id = await self.guardian_ble.get_device_mac()
        ble_client_task = self.guardian_ble.run_ble_record(
            data_queue, recording_timer, mac_id, led_sleep
        )
        api_consumer_task = self.guardian_api.connect_ws_api(
            data_queue, mac_id, recording_id
        )

        await asyncio.wait([ble_client_task, api_consumer_task])
        if self.debug:
            logging.info("[CLIENT]: -----------  All tasks are COMPLETED -----------")
        print(f"-----Recording ID {recording_id}------")
        print(f"-----Device ID {mac_id}------")
        print("-----Recording stopped------")

    async def start_local_recording(
        self,
        recording_timer: int = 36000,
        led_sleep: bool = False,
        experiment: str = "None provided",
    ):
        """
        Start recording data from the Guardian Earbuds.
        Instead of sending the data to the cloud, decode them locally.

        Args:
            recording_timer (int, optional): The duration of the recording in seconds. Defaults to 36000.
            led_sleep (bool, optional): Enable LED sleep mode. Defaults to False.
            experiment (str, optional): The name of the experiment. Defaults to "None provided". This will
                                        go to the log file.

        Raises:
            ValueError: If the recording timer is not valid
        """
        if self.debug:
            logging.info(
                "[CLIENT]: Recording timer set to: %s seconds", recording_timer
            )
            logging.info("[CLIENT]: Start recording")

        print(f"[CLIENT]: Recording timer set to: {recording_timer} seconds")
        print("-----Recording starting------")

        data_queue: asyncio.Queue = asyncio.Queue(maxsize=86400)
        recording_id = str(
            uuid.uuid4()
        )  # the recordingID is a unique ID for each recording
        logging.info("[CLIENT] Recording ID: %s", recording_id)
        # log the experiment name in bold using the logging module
        logging.info("[CLIENT] Experiment description: %s", experiment)

        mac_id = await self.guardian_ble.get_device_mac()
        ble_client_task = self.guardian_ble.run_ble_record(
            data_queue, recording_timer, mac_id, led_sleep
        )
        decryption_consumer_task = self.guardian_decryption.decrypt_data(
            data_queue, mac_id, recording_id
        )

        await asyncio.wait([ble_client_task, decryption_consumer_task],return_when=asyncio.FIRST_COMPLETED)
        if self.debug:
            logging.info("[CLIENT]: -----------  All tasks are COMPLETED -----------")
        print(f"-----Recording ID {recording_id}------")
        print(f"-----Device ID {mac_id}------")
        print("-----Recording stopped------")

    def stop_recording(self):
        """Stop recording data from the Guardian Earbuds"""

    async def start_impedance(
        self, impedance_display_time: int = 5, mains_freq_60hz: bool = False
    ):
        """
        Start recording data from the Guardian Earbuds.
        Unidirectional websocket connection to the Guardian Cloud API.

        Args:

            impedance_display_time (int, optional): The time in seconds to display the impedance. Defaults to 5.
            mains_freq_60hz (bool, optional): Set to True if the mains frequency is 60Hz. Defaults to False.

        Returns:
            impedance (float): The impedance value
        """
        if self.debug:
            logging.info("[CLIENT]: Start recording")
        print("-----Impedance check started------")

        data_queue: asyncio.Queue = asyncio.Queue(maxsize=86400)
        recording_id = str(
            uuid.uuid4()
        )  # the recordingID is a unique ID for each recording
        logging.info("[CLIENT] Recording ID: %s", recording_id)

        mac_id = await self.guardian_ble.get_device_mac()

        ble_client_task = self.guardian_ble.get_impedance_measurement(
            data_queue, impedance_display_time, mains_freq_60hz, mac_id
        )
        api_consumer_task = self.guardian_api.connect_ws_api(
            data_queue, mac_id, recording_id
        )
        await asyncio.wait([ble_client_task, api_consumer_task])

        if self.debug:
            logging.info("[CLIENT]: Disconnect BLE and close websocket connection")
        print("-----Impedance check stopped------")

    async def start_battery(self):
        """
        Start recording data from the Guardian Earbuds.
        Unidirectional websocket connection to the Guardian Cloud API.
        """
        print("-----Battery readout started------")
        if self.debug:
            logging.info("[CLIENT]: Start recording")

        ble_client_task = self.guardian_ble.read_battery_level()
        await asyncio.wait([ble_client_task])

        if self.debug:
            logging.info("[CLIENT]: Disconnect BLE and close websocket connection")
        print("-----Battery check stopped------")
