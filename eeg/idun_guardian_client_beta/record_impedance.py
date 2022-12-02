"""
Sample script for using the Guardian Earbud Client
- Start recording data from the Guardian Earbuds
"""
import asyncio
from src.idun_guardian_client_beta.client import GuardianClient


IMPEDANCE_DURATION = 100  # duration of impedance measurement in seconds
MAINS_FREQUENCY_60Hz = (
    False  # mains frequency in Hz (50 or 60), for Europe 50Hz, for US 60Hz
)

DEVICES=[
    "F8:DB:73:4E:80:C6",
    "C3:E4:75:45:2F:A8",
]
# start a recording session
bci = GuardianClient(address=DEVICES[0])

# start a recording session
asyncio.run(
    bci.start_impedance(
        impedance_display_time=IMPEDANCE_DURATION, mains_freq_60hz=MAINS_FREQUENCY_60Hz
    )
)
