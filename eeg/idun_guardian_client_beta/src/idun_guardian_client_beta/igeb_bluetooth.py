"""
Guardian Bluetooth utils.
"""
import sys
import asyncio
import os
from codecs import utf_8_encode
import logging
import time
import base64
import datetime
from bleak import BleakClient, BleakScanner, exc

from .config import settings


class GuardianBLE:
    """Main Guardian BLE client."""

    def __init__(self, address: str = "", debug: bool = True) -> None:
        """Initialize the Guardian BLE client.

        Args:
            address (str, optional): BLE device address. Defaults to "".
            debug (bool, optional): Debug mode. Defaults to True.
        """
        self.client: BleakClient

        # Debugging mode
        self.address = address
        self.debug = debug
        self.write_to_file: bool = debug

        # Initial connection flags
        self.initialise_connection: bool = True
        self.connection_established = False
        self.time_left = True
        self.initial_time = True

        # Bluetooth reconnect delay
        self.original_time = time.time()
        self.reconnect_try_amount = 50
        self.try_to_connect_timeout = self.reconnect_try_amount

        # Bluetooth timings
        self.ble_delay = 1
        self.ble_stop_delay = 3
        self.device_lost = False

        # API timeings
        self.sent_final_package_time = 6

        # The timing constants
        self.sample_rate = 250
        self.amount_samples_packet = 20
        self.max_index = 256

        self.get_ble_characteristic()

        if self.debug:
            logging.info("[BLE]: BLE client initiliazed")

    def get_ble_characteristic(self) -> None:
        """Get the environment variables."""
        # General information
        self.battery_id = settings.UUID_BATT_GDK
        self.device_service = settings.UUID_DEVICE_SERVICE
        self.mac_uuid = settings.UUID_MAC_ID
        self.firmware_uuid = settings.UUID_FIRMWARE_VERSION

        # EEG/IMU measurement
        self.meas_eeg_id = settings.UUID_MEAS_EEGIMU
        self.command_id = settings.UUID_CMD
        self.start_cmd = settings.START_CMD
        self.stop_cmd = settings.STOP_CMD

        # Impedance measurement
        self.meas_imp_id = settings.UUID_MEAS_IMP
        self.start_imp_cmd = settings.START_IMP_CMD
        self.stop_imp_cmd = settings.STOP_IMP_CMD
        self.notch_freq_50_cfg = settings.NOTCH_FREQ_50_CFG
        self.notch_freq_60_cfg = settings.NOTCH_FREQ_60_CFG

        # LED control
        self.cfg_id = settings.UUID_CFG
        self.led_on_cfg = settings.LED_ON_CFG
        self.led_off_cfg = settings.LED_OFF_CFG

    async def get_ble_devices(self) -> list:
        """
        Scan for devices and return a list of devices.
        """
        devices_dict: dict = {}
        ble_device_list: list = []
        devices = await BleakScanner.discover()
        igeb_name = "IGEB"
        device_idx = 0
        print("\n----- Available devices -----\n")
        print("Index | Name | Address")
        print("----------------------------")
        for _, device in enumerate(devices):
            # print device discovered
            if device.name == igeb_name:
                print(f"{device_idx}     | {device.name} | {device.address}")
                # put device information in list
                devices_dict[device.address] = []
                devices_dict[device.address].append(device.name)
                # devices_dict[device.address].append(device.metadata["uuids"])
                ble_device_list.append(device.address)
                device_idx += 1
        print("----------------------------\n")
        return ble_device_list

    async def stop_stream(self) -> None:
        """Stop the stream."""
        try:
            async with BleakClient(self.address) as client:
                await client.write_gatt_char(
                    self.command_id, utf_8_encode(self.stop_cmd)[0]
                )
                if self.debug:
                    logging.info("[BLE]: Recording successfully stopped")
        except exc.BleakError:
            logging.info("[BLE]: failed to stop measurement")

    async def get_device_mac(self) -> str:
        """Get the device MAC address.
        This is different from BLE device address
        (UUID on Mac or MAC address on Windows)

        Args:
            device_name (str): Device name

        Returns:
            str: MAC address
        """
        async with BleakClient(self.address) as client:
            logging.info("[BLE]: Searching for MAC address")

            value = bytes(await client.read_gatt_char(self.mac_uuid))
            await asyncio.sleep(self.ble_delay)
            firmware_version = bytes(await client.read_gatt_char(self.firmware_uuid))
            # log the mac address of the device
            # convert bytes to string
            mac_address = value.decode("utf-8")
            firmware_decoded = firmware_version.decode("utf-8")
            mac_address = mac_address.replace(":", "-")
            logging.info("[BLE] Device ID (based on MAC address is): %s", mac_address)
            logging.info("[BLE]: Firmware version: %s", firmware_decoded)
            return mac_address  # convert bytes to string

    async def search_device(self) -> str:
        """This function searches for the device and returns the address of the device.
        If the device is not found, it exits the program. If multiple devices are found,
        it asks the user to select the device. If one device is found, it returns the
        address of the device.

        Returns:
            _type_: _description_
        """

        ble_device_list = await self.get_ble_devices()

        if len(ble_device_list) == 0:
            logging.info("[BLE]: No IGEB device found, exiting ...n")
            try:
                sys.exit(0)
            except SystemExit:
                os._exit(0)
        elif len(ble_device_list) == 1:
            logging.info(
                "[BLE]: One IGEB device found, assinging address %s", ble_device_list[0]
            )
            self.address = ble_device_list[0]
        else:
            index_str = input(
                "Enter the index of the GDK device you want to connect to \
                \nIf cannot find the device, please restart the program and try again: "
            )
            index = int(index_str)
            self.address = ble_device_list[index]
        if self.debug:
            logging.info("[BLE]: Address is %s", self.address)
            logging.info("[BLE]: .............................................")
            logging.info("[BLE]: Connecting to %s", self.address)

        return self.address

    async def connect_to_device(self):
        """
        This function initialises the connection to the device.
        It finds the device using the address, sets up callback,
        and connects to the device.
        """
        if self.debug:
            logging.info("[BLE]: Trying to connect to %s.....", self.address)
        device = await BleakScanner.find_device_by_address(self.address, timeout=20.0)
        if not device:
            raise exc.BleakError(
                f"A device with address {self.address} could not be found."
            )
        self.client = BleakClient(
            device, disconnected_callback=self.disconnected_callback
        )
        if self.debug:
            logging.info("[BLE]: Connecting to %s", self.address)
        await self.client.connect()
        self.connection_established = True
        if self.debug:
            logging.info("[BLE]: Connected to %s", self.address)

    def disconnected_callback(self, client):  # pylint: disable=unused-argument
        """
        Callback function when device is disconnected.

        Args:
            client (BleakClient): BleakClient object
        """
        if self.debug:
            logging.info("[BLE]: Callback function recognised a disconnection.")
        self.connection_established = False
        self.initialise_connection = True

    async def run_ble_record(
        self,
        data_queue: asyncio.Queue,
        record_time=60,
        mac_id="MAC_ID",
        led_sleep: bool = False,
    ) -> None:
        """
        This function runs the recording of the data. It sets up the bluetooth
        connection, starts the recording, and then reads the data and adds it to
        the queue. The API class then reads the data from the queue and sends it
        to the cloud.

        Args:
            data_queue (asyncio.Queue): Queue to store the data
            record_time (_type_): The time to record for
            mac_id (_type_): The MAC address of the device
            led_sleep (_type_): Whether to turn off the LED

        Raises:
            BleakError: _description_
        """

        def time_stamp_creator(new_index):
            """
            This function creates a timestamp for the cloud based on the
            time the recording started. Each time stamp is based on the index
            of that is sent from the device. The index is the number of iterates
            between 0 and 256. The time stamp is the 1/250s multiplied by the
            index.

            Args:
                new_index (int): Index of the data point from the ble packet

            Returns:
                str: Timestamp in the format of YYYY-MM-DDTHH:MM:SS
            """
            index_diff = new_index - self.prev_index

            if self.prev_timestamp == 0:
                time_data = datetime.datetime.now().astimezone().isoformat()
                # convert time_data to a float in seconds
                time_data = time.mktime(
                    datetime.datetime.strptime(
                        time_data, "%Y-%m-%dT%H:%M:%S.%f%z"
                    ).timetuple()
                )
                new_time_stamp = time_data
            else:
                multiplier = (index_diff + self.max_index) % self.max_index
                new_time_stamp = (
                    self.amount_samples_packet * (1 / self.sample_rate) * multiplier
                ) + self.prev_timestamp

            self.prev_index = new_index
            self.prev_timestamp = new_time_stamp

            time_stamp_isoformat = datetime.datetime.fromtimestamp(
                new_time_stamp
            ).isoformat()

            return time_stamp_isoformat

        async def data_handler(_, data):
            """Data handler for the BLE client.
                Data is put in a queue and forwarded to the API.

            Args:
                callback (handler Object): Handler object
                data (bytes): Binary data package
            """
            data_base_64 = base64.b64encode(data).decode("ascii")
            new_time_stamp = time_stamp_creator(data[1])

            if self.write_to_file:
                self.data_recording_logfile.write(f"{data_base_64},\n")

            package = {
                "timestamp": new_time_stamp,
                "device_id": mac_id,
                "data": data_base_64,
                "stop": False,
            }
            await data_queue.put(package)

        async def battery_handler(_, data):
            """Battery handler for the BLE client.
            Args:
                callback (handler Object): Handler object
                data (bytes): Battery Level as uint8_t
            """
            if self.debug:
                logging.info(
                    "[BLE]: Battery level: %d%%",
                    int.from_bytes(data, byteorder="little"),
                )

        async def send_start_commands_recording():
            """Send start commands to the device."""
            if self.debug:
                logging.info("[BLE]: Sending start commands")

            # ------------------ Configuration ------------------
            if led_sleep:
                await asyncio.sleep(self.ble_delay)
                await self.client.write_gatt_char(
                    self.cfg_id, utf_8_encode(self.led_off_cfg)[0]
                )

            # ------------------ Subscribe to notifications ------------------
            # Notify the client that these two services are required
            if self.debug:
                logging.info("[BLE]: Subscribing to EEG notifications")
            await asyncio.sleep(self.ble_delay)
            await self.client.start_notify(self.meas_eeg_id, data_handler)

            if self.debug:
                logging.info("[BLE]: Subscribing to Battery notifications")
            await asyncio.sleep(self.ble_delay)
            await self.client.start_notify(self.battery_id, battery_handler)

            # ------------------ Start commands ------------------
            # sleep so that cleint can respond
            await asyncio.sleep(self.ble_delay)
            # send start command for recording data
            await self.client.write_gatt_char(
                self.command_id, utf_8_encode(self.start_cmd)[0]
            )

        async def stop_recording_timeout():
            """Stop recording gracefully."""

            # ------------------------- TEST
            await asyncio.sleep(self.ble_delay)
            # make sure the last data is now a stop command
            package = {
                "timestamp": datetime.datetime.now().astimezone().isoformat(),
                "device_id": mac_id,
                "data": "STOP_TIMEOUT",
                "stop": True,
            }

            # ------------------ Load final stop package ------------------
            await data_queue.put(package)
            if self.debug:
                logging.info("[BLE]: Stop command loaded into queue")

            # ------------------ API should send already loaded package  ------------------
            if self.debug:
                logging.info("[BLE]: Giving time for API to send last data")
            await asyncio.sleep(
                self.sent_final_package_time
            )  # This gives time for the api to send already loaded data

            if self.debug:
                logging.info("[BLE]: Sending stop command to device")
            await asyncio.sleep(self.ble_delay)
            await self.client.write_gatt_char(
                self.command_id, utf_8_encode(self.stop_cmd)[0]
            )

            if led_sleep:
                if self.debug:
                    logging.info("[BLE]: Turning LED on")
                await asyncio.sleep(self.ble_delay)
                await self.client.write_gatt_char(
                    self.cfg_id, utf_8_encode(self.led_on_cfg)[0]
                )

            # ------------------ Disconnect command to device ------------------
            if self.debug:
                logging.info("[BLE]: Sending disconnect command to device")
            await asyncio.sleep(self.ble_stop_delay)
            await self.client.disconnect()
            await asyncio.sleep(self.ble_stop_delay)

            if self.write_to_file:
                self.data_recording_logfile.close()

            if self.debug:
                logging.info("[BLE]: Recording successfully stopped")

        async def stop_recording_cancelled_script():
            """Stop recording abruptly."""
            if self.debug:
                logging.info("[BLE]: KeyboardInterrupt applied, terminating...")
                logging.info(
                    "[BLE]: Sending stop signal to device and cloud, please wait a moment ..."
                )

            # ------------------ Sending final API packages ------------------
            if self.debug:
                logging.info(
                    "[BLE]: Giving time for the API to send already loaded data"
                )
            await asyncio.sleep(
                self.sent_final_package_time
            )  # Give API time to send last package
            # With its own interupt handling

            # ------------------ Send stop EEG recording command ------------------
            if self.debug:
                logging.info("[BLE]: Sending stop command to device")
            await asyncio.sleep(self.ble_delay)
            await self.client.write_gatt_char(
                self.command_id, utf_8_encode(self.stop_cmd)[0]
            )

            # ------------------ Configuring LED back on ------------------
            if led_sleep:
                if self.debug:
                    logging.info("[BLE]: Turning LED on")
                await asyncio.sleep(self.ble_delay)
                await self.client.write_gatt_char(
                    self.cfg_id, utf_8_encode(self.led_on_cfg)[0]
                )

            # ------------------ Disconnecting commands ------------------
            if self.debug:
                logging.info("[BLE]: Disconnecting the device")
            await asyncio.sleep(self.ble_stop_delay)
            await self.client.disconnect()
            await asyncio.sleep(self.ble_stop_delay)

            # ------------------ Closing file  ------------------
            if self.write_to_file:
                self.data_recording_logfile.close()

            if self.debug:
                logging.info("[BLE]: Recording successfully stopped on device side")

            # ------------------ Sending final API packages ------------------
            if self.debug:
                logging.info("[BLE]: Final time given for the API to send stop signal")
            await asyncio.sleep(
                self.sent_final_package_time
            )  # Give API time to send last package
            # With its own interupt handling

        async def stop_recording_device_lost():
            """Stop recording device lost."""
            if self.debug:
                logging.info("[BLE]: Device lost, terminating...")

            # ------------------ Sending final API packages ------------------
            if self.debug:
                logging.info("[BLE]: Giving API time to clean buffer")
            await asyncio.sleep(self.ble_delay)  # Give API time to send last package

            # ------------------ Loading last package ------------------
            if self.debug:
                logging.info("[BLE]: Loading last package")

            package = {
                "timestamp": datetime.datetime.now().astimezone().isoformat(),
                "device_id": mac_id,
                "data": "STOP_DEVICE_LOST",
                "stop": True,
            }
            # pack the stop command
            await data_queue.put(package)

            # ------------------ Sending final API packages ------------------
            if self.debug:
                logging.info("[BLE]: Final time given for the API to send stop signal")
            await asyncio.sleep(
                self.sent_final_package_time
            )  # Give API time to send last package

            # ------------------ Closing file ------------------
            if self.write_to_file:
                self.data_recording_logfile.close()

            return True

        async def bluetooth_reconnect():
            self.try_to_connect_timeout = self.try_to_connect_timeout - 1
            if self.try_to_connect_timeout <= 0:
                self.device_lost = await stop_recording_device_lost()
            if self.debug:
                logging.warning(
                    " [BLE] Connection lost, will try to reconnect %s more times",
                    self.try_to_connect_timeout,
                )
            self.connection_established = False
            self.initialise_connection = True

        # >>>>>>>>>>>>>>>>>>>>> Start of recording process <<<<<<<<<<<<<<<<<<<<<<<<
        # ------------------ Initialise values for timestamps ------------------
        self.prev_timestamp = 0
        self.prev_index = -1

        # ------------------ Initialise time values for recording timeout ------------------
        # This has been decoupled from the device timing for robustness
        self.original_time = time.time()
        self.initial_time = True
        self.time_left = True
        self.initial_time = True

        # ------------------ Initialise connection values for trying to connect again ------------------
        self.connection_established = False
        self.try_to_connect_timeout = self.reconnect_try_amount

        # ------------------ Initialise log file ------------------
        if self.write_to_file:
            if not os.path.exists("./logs"):
                os.makedirs("logs")
            datestr = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            recording_filename = f"./logs/IGEB-rec-{datestr}.txt"
            self.data_recording_logfile = open(
                recording_filename, "w", encoding="utf-8"
            )

        while True:
            try:

                if self.initialise_connection:
                    self.initialise_connection = False
                    await self.connect_to_device()

                if self.client.is_connected:
                    if self.debug:
                        logging.info("[BLE]: Device Connected")
                    await send_start_commands_recording()
                    if self.debug:
                        logging.info("[BLE]: Recording successfully started")
                    self.try_to_connect_timeout = (
                        self.reconnect_try_amount
                    )  # reset counter

                    # >>>>>>>>>>>>>>>>>>>>> Main loop <<<<<<<<<<<<<<<<<<<<<<<<
                    if self.initial_time:
                        self.initial_time = (
                            False  # record that this is the initial time
                        )
                        self.original_time = time.time()
                    while (
                        self.connection_established is True and self.time_left is True
                    ):
                        await asyncio.sleep(
                            self.ble_delay
                        )  # sleep so that everything can happen
                        remaining_time = record_time - (
                            time.time() - self.original_time
                        )
                        print(f"Time left: {round(remaining_time)}s")
                        if remaining_time <= 0:
                            self.time_left = False
                            if self.debug:
                                logging.info(
                                    "[BLE]: Recording stopped, time reached : %s",
                                    round(time.time() - self.original_time, 2),
                                )
                    # >>>>>>>>>>>>>>>>>>>>> Main loop <<<<<<<<<<<<<<<<<<<<<<<<
                    if not self.time_left:
                        if self.debug:
                            logging.info("[BLE]: Time out reached")
                        await stop_recording_timeout()
                        break

                if not self.connection_established:
                    if self.debug:
                        logging.info("[BLE]: Bluetooth disconnected")
                    await bluetooth_reconnect()
                    if self.device_lost:
                        break

            except asyncio.CancelledError:
                await stop_recording_cancelled_script()
                break

            except Exception as error:
                logging.error("[BLE]: Error in bluetooth client: %s", error)

            finally:
                if self.debug:
                    logging.info("[BLE]: Ensuring device is disconnected")
                await asyncio.sleep(self.ble_stop_delay)
                await self.client.disconnect()
                await asyncio.sleep(self.ble_stop_delay)
                self.connection_established = False

        if self.debug:
            logging.info("[BLE]: -----------  BLE client is COMPLETED ----------- ")

    async def get_service_and_char(self) -> None:
        """Get the services and characteristics of the device."""
        try:
            async with BleakClient(self.address) as client:
                logging.info("BLE: Device connected")

                for service in client.services:
                    logging.info("[Service] %s: %s", service.uuid, service.description)
                    for char in service.characteristics:
                        if "read" in char.properties:
                            try:
                                value = bytes(await client.read_gatt_char(char.uuid))
                            except exc.BleakError as err:
                                value = str(err).encode()
                        else:
                            value = None
                        logging.info(
                            "\t[Characteristic] %s: (Handle: %s) (%s) \
                                | Name: %s, Value: %s ",
                            char.uuid,
                            char.handle,
                            ",".join(char.properties),
                            char.description,
                            value,
                        )

                await asyncio.sleep(self.ble_stop_delay)
                await client.disconnect()
                await asyncio.sleep(self.ble_stop_delay)
                if self.debug:
                    logging.info("Disconnected from BLE device")
        except exc.BleakError as err:
            logging.error("[BLE]: Device connection failed - %s", err)

    async def read_battery_level(self) -> None:
        """Read the battery level of the device given pre-defined interval."""
        if self.debug:
            logging.info("Reading battery level")

        async with BleakClient(self.address) as client:
            if self.debug:
                logging.info("[BLE]: Device connected")

            try:
                await asyncio.sleep(self.ble_delay)
                value = int.from_bytes(
                    (await client.read_gatt_char(self.battery_id)), byteorder="little"
                )
                print("-----------------------------")
                print(f"\nBattery level: {value}%\n")
                print("-----------------------------")
                if self.debug:
                    logging.info("Battery level: %s%%", value)

                await asyncio.sleep(self.ble_stop_delay)
                await client.disconnect()
                await asyncio.sleep(self.ble_stop_delay)
                if self.debug:
                    logging.info("Disconnected from BLE device")

            except exc.BleakError as err:
                # log the error
                logging.error("[BLE]: Device connection failed - %s", err)

    async def get_device_information(self) -> dict:
        """Read the device information of the device."""

        device_info = {}

        if self.debug:
            logging.info("[BLE]: Reading device information")

        async with BleakClient(self.address) as client:
            logging.info("[BLE]: Device connected")

            for service in client.services:
                if service.uuid == self.device_service:
                    for char in service.characteristics:
                        if "read" in char.properties:
                            try:
                                value = bytes(await client.read_gatt_char(char.uuid))
                            except exc.BleakError as err:
                                value = str(err).encode()
                        else:
                            value = None

                        print(f"{ char.description}:{str(value)}")
                        device_info[char.description] = str(value)
                        if self.debug:
                            logging.info("%s : %s", char.description, str(value))

        return device_info

    async def get_impedance_measurement(
        self,
        data_queue: asyncio.Queue,
        impedance_display_time=5,
        mains_freq_60hz=False,
        mac_id="deviceMockID",
    ) -> None:
        """Get impedance measurement."""
        if self.debug:
            logging.info("[BLE]: Getting impedance measurement")
            logging.info(
                "[BLE]: Impedance display time: %s seconds", impedance_display_time
            )

        if self.write_to_file:
            if not os.path.exists("./logs"):
                os.makedirs("logs")
            datestr = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            local_impedance_recording = open(
                f"./logs/IGEB-imp-{datestr}.txt", "w", encoding="utf-8"
            )

        def write_impedance_to_local(data_int):
            """Write data to local file."""
            # convert data from bytes to int

            print(f"[BLE]: Impedance value : {round(data_int/1000,2)} kOhms")
            if self.write_to_file:
                local_impedance_recording.write(f"{data_int}\n")

        async def impedance_handler(_, data):
            """Impedance handler for the BLE client.
                Data is put in a queue and forwarded to the API.

            Args:
                callback (handler Object): Handler object
                data (bytes): Binary data package with impedance values
            """
            data_int = int.from_bytes(data, byteorder="little")
            if self.write_to_file:
                write_impedance_to_local(data_int)

            package = {
                "timestamp": datetime.datetime.now().astimezone().isoformat(),
                "device_id": mac_id,
                "stop": False,
                "impedance": data_int,
            }
            # add the received impedance data to the queue
            await data_queue.put(package)

        async with BleakClient(self.address) as client:
            logging.info("[BLE]: Device connected")
            logging.info("[BLE]: Starting impedance measurement")

            # ----------------- Configuration -----------------
            if mains_freq_60hz:
                await asyncio.sleep(self.ble_delay)
                await client.write_gatt_char(
                    self.cfg_id, utf_8_encode(self.notch_freq_60_cfg)[0]
                )
            else:
                await asyncio.sleep(self.ble_delay)
                await client.write_gatt_char(
                    self.cfg_id, utf_8_encode(self.notch_freq_50_cfg)[0]
                )

            # ----------------- Subscribe -----------------
            if self.debug:
                logging.info("[BLE]: Subscribed to impedance measurement")
            await asyncio.sleep(self.ble_delay)
            await client.start_notify(self.meas_imp_id, impedance_handler)

            # ----------------- Send start command -----------------
            if self.debug:
                logging.info("[BLE]: Sending start impedance command")
            await asyncio.sleep(self.ble_delay)
            await client.write_gatt_char(
                self.command_id, utf_8_encode(self.start_imp_cmd)[0]
            )

            # ----------------- Create a delay for impedance -----------------
            if self.debug:
                logging.info("[BLE]: Displaying impedance measurement")
            await asyncio.sleep(impedance_display_time)

            # ----------------- Stop imedance readout -----------------
            if self.debug:
                logging.info("[BLE]: Stopping impedance measurement")
            await client.write_gatt_char(
                self.command_id, utf_8_encode(self.stop_imp_cmd)[0]
            )

            # send stop command to the queue
            package = {
                "timestamp": datetime.datetime.now().astimezone().isoformat(),
                "device_id": mac_id,
                "stop": True,
            }
            # add the received impedance data to the queue
            await data_queue.put(package)

            # ------------------ Sending final API packages ------------------
            if self.debug:
                logging.info("[BLE]: Final time given for the API to send stop signal")
            await asyncio.sleep(
                self.sent_final_package_time
            )  # Give API time to send last package

            # ----------------- Stop device -----------------
            if self.debug:
                logging.info("[BLE]: Disconnecting from device")
            await asyncio.sleep(self.ble_stop_delay)
            await client.disconnect()
            await asyncio.sleep(self.ble_stop_delay)

            if self.write_to_file:
                local_impedance_recording.close()

            if self.debug:
                logging.info("[BLE]: -----------  BLE client is COMPLETED ----------- ")
