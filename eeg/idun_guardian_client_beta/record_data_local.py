"""
Sample script for using the Guardian Earbud Client
- Start recording data from the Guardian Earbuds
"""
import asyncio
from src.idun_guardian_client_beta.client import GuardianClient

EXPERIMENT: str = "Testing"
RECORDING_TIMER: int = 40
LED_SLEEP: bool = False

DEVICES=[
    "F8:DB:73:4E:80:C6",
    "C3:E4:75:45:2F:A8",
]
# start a recording session
bci = GuardianClient(address=DEVICES[0])

# start a recording session
asyncio.run(
    bci.start_local_recording(
        recording_timer=RECORDING_TIMER, led_sleep=LED_SLEEP, experiment=EXPERIMENT
    )
)
