import numpy as np
import base64
from Crypto.Cipher import ChaCha20_Poly1305
from .SECRETS import DECRYPTION_KEY, NONCE, HEADER

def decrypt_data(data_enc: str) -> bytes:
    """
    Decrypt data from IGEB
    Currently only uses static pre-defined encryption key

    Args:
        data (str): Base64 encoded encrypted data

    Returns:
        list: List with decrypted data
    """
    # make it a bytearry again from base64
    data = bytearray(base64.b64decode(data_enc))
    # Remove start byte and counter
    data = data[2:-1]
    cipher = ChaCha20_Poly1305.new(key=DECRYPTION_KEY, nonce=NONCE)
    cipher.update(HEADER)
    return cipher.decrypt_and_verify(data[0:-16], data[-16:])


def convert_igeb_data(message: bytes):
    """
    Convert IGE data from bytes to dict
    This implements the processing and returning all samples from a message
    [                   Message                 ]
    [       Package 1     ][       Package 2    ]
    [ [   ADS    ]  [IMU] ||    ADS    ]  [IMU] ]
    [ [10 samples][1 sample]|| [10 samples] [1 sample]]

    Args: message (bytes): Byte array with IGE data
    (important: without startbyte (1 bit) and counter (1 bit))

    """
    data_dict: dict = {"ch1": [], "ch2": [], "acc": [], "magn": [], "gyro": []}
    scaling_factor = 0.022351744455307063

    index_ads = 0
    index_imu = [60, 138]  # imu byte index starts after

    # loop over packages
    for imu__idx_byte in index_imu:

        for _ in range(10):
            data_dict["ch1"].append(
                scaling_factor
                * int.from_bytes(message[index_ads : index_ads + 3], "big", signed=True)
            )
            data_dict["ch2"].append(
                scaling_factor
                * int.from_bytes(
                    message[index_ads + 3 : index_ads + 6], "big", signed=True
                )
            )
            index_ads += 6

        # convert 1 imu sample
        data_dict["acc"].append(
            [
                0.001
                * int.from_bytes(
                    message[imu__idx_byte : imu__idx_byte + 2],
                    "little",
                    signed=True,
                ),
                0.001
                * int.from_bytes(
                    message[imu__idx_byte + 2 : imu__idx_byte + 4],
                    "little",
                    signed=True,
                ),
                0.001
                * int.from_bytes(
                    message[imu__idx_byte + 4 : imu__idx_byte + 6],
                    "little",
                    signed=True,
                ),
            ]
        )

        data_dict["magn"].append(
            [
                0.0001
                * int.from_bytes(
                    message[imu__idx_byte + 6 : imu__idx_byte + 8],
                    "little",
                    signed=True,
                ),
                0.0001
                * int.from_bytes(
                    message[imu__idx_byte + 8 : imu__idx_byte + 10],
                    "little",
                    signed=True,
                ),
                0.0001
                * int.from_bytes(
                    message[imu__idx_byte + 10 : imu__idx_byte + 12],
                    "little",
                    signed=True,
                ),
            ]
        )

        data_dict["gyro"].append(
            [
                0.001
                * int.from_bytes(
                    message[imu__idx_byte + 12 : imu__idx_byte + 14],
                    "little",
                    signed=True,
                ),
                0.001
                * int.from_bytes(
                    message[imu__idx_byte + 14 : imu__idx_byte + 16],
                    "little",
                    signed=True,
                ),
                0.001
                * int.from_bytes(
                    message[imu__idx_byte + 16 : imu__idx_byte + 18],
                    "little",
                    signed=True,
                ),
            ]
        )

        index_ads += 18
    return data_dict



def convert_encoded_data_to_dictionary(
    time_stamp: float, data_encrypted: str, eeg_sample_rate=250, imu_sample_rate=25
) -> dict:
    """
    Convert encrypted data from IGEB to dictionary

    Args:
        time_stamp (float): Time stamp of the data
        data (str): Base64 encoded encrypted data

    Returns:
        dict: Dictionary with output of the channel 1 data in format
            {eeg_ch1 : [
                {"time_stamp" : time_stamp,
                "data" : data},
                ...
                {"time_stamp" : time_stamp,
                "data" : data},
                ...
            ],
            imu : [
                {"time_stamp" : time_stamp,
                "acc_x" : x,
                    ...
                "magn_z" : y,
                    ...
                "gyro_z" : z},
                ...
    """
    # Decrypt data and convert to bytearry
    data_decrypted = decrypt_data(data_encrypted)
    # unpack data into a not scaled dictionary
    unpacked_data_dict = convert_igeb_data(data_decrypted)
    # extract ch1 array
    cloud_format_dict = pack_data_cloud_format_dict(
        time_stamp, unpacked_data_dict, eeg_sample_rate, imu_sample_rate
    )
    return cloud_format_dict


def pack_data_cloud_format_dict(
    time_stamp: float, unpacked_data_dict: dict, eeg_sample_rate=250, imu_sample_rate=25
):
    """
    Pack data from dictionary to cloud format

    Args:
        time_stamp (float): Time stamp of the data
        unpacked_dict (dict): Dictionary with unpacked data
        eeg_sample_rate (int, optional): Sample rate of the EEG data. Defaults to 250.
        imu_sample_rate (int, optional): Sample rate of the IMU data. Defaults to 25.

    Returns:
        dict: Dictionary with output of the data in format:
            {eeg_ch1 : [
                {"time_stamp" : time_stamp,
                "data" : data},
                ...
                {"time_stamp" : time_stamp,
                "data" : data},
                ...
            ],
            imu : [
                {"time_stamp" : time_stamp,
                "acc_x" : x,
                    ...
                "magn_z" : y,
                    ...
                "gyro_z" : z},
                ...
    """
    ch1_data = np.array(unpacked_data_dict["ch1"])
    acc_data = np.array(unpacked_data_dict["acc"])
    magn_data = np.array(unpacked_data_dict["magn"])
    gyro_data = np.array(unpacked_data_dict["gyro"])
    # create dictionary with all data
    cloud_format_dict: dict = {"eeg": [], "imu": []}
    for idx, sample in enumerate(ch1_data):
        cloud_format_dict["eeg"].append(
            {"timestamp": time_stamp + idx / eeg_sample_rate, "ch1": sample}
        )
    for idx, _ in enumerate(acc_data):
        cloud_format_dict["imu"].append(
            {
                "timestamp": time_stamp + idx / imu_sample_rate,
                "acc_x": acc_data[idx][  # pylint: disable=unnecessary-list-index-lookup
                    0
                ],
                "acc_y": acc_data[idx][  # pylint: disable=unnecessary-list-index-lookup
                    1
                ],
                "acc_z": acc_data[idx][  # pylint: disable=unnecessary-list-index-lookup
                    2
                ],
                "magn_x": magn_data[
                    idx
                ][  # pylint: disable=unnecessary-list-index-lookup
                    0
                ],
                "magn_y": magn_data[
                    idx
                ][  # pylint: disable=unnecessary-list-index-lookup
                    1
                ],
                "magn_z": magn_data[
                    idx
                ][  # pylint: disable=unnecessary-list-index-lookup
                    2
                ],
                "gyro_x": gyro_data[
                    idx
                ][  # pylint: disable=unnecessary-list-index-lookup
                    0
                ],
                "gyro_y": gyro_data[
                    idx
                ][  # pylint: disable=unnecessary-list-index-lookup
                    1
                ],
                "gyro_z": gyro_data[
                    idx
                ][  # pylint: disable=unnecessary-list-index-lookup
                    2
                ],
            }
        )
    return cloud_format_dict
