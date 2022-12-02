from collections.abc import Iterable
from datetime import datetime
import io
import csv
from .igeb_decryption import GuardianDataModel
from .decryption_utils import convert_encoded_data_to_dictionary


def decode_message(message: Message):
    # channels: {eeg_ch1, acc, magn, gyro}
    # {channel}[samples]{timestamp, value}
    timeSeconds = datetime.fromisoformat(message.deviceTimestamp).timestamp()
    return convert_encoded_data_to_dictionary(timeSeconds, message.payload)


def assembleRecording(messages: Iterable[GuardianDataModel]) -> tuple[str, str]:
    """
    Assemble a list of messages into a CSV-formatted Recording text buffer
    This applies per-message decoding and decryption.
    """

    # Alternative for lower memory consumption: temporary file https://docs.python.org/3.10/library/tempfile.html?highlight=file#tempfile.TemporaryFile
    with io.StringIO(newline="") as eegbuf, io.StringIO(newline="") as imubuf:
        eeg_csv = csv.DictWriter(
            eegbuf,
            dialect="excel",
            fieldnames=["timestamp", "ch1"],
        )
        imu_csv = csv.DictWriter(
            imubuf,
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
        for samples in map(decode_message, messages):
            eeg_csv.writerows(samples["eeg"])
            imu_csv.writerows(samples["imu"])
        eeg_recording = eegbuf.getvalue()
        imu_recording = imubuf.getvalue()

    return eeg_recording, imu_recording

