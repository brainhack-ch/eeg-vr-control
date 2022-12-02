"""
Sample script for using the Guardian Earbud Client
- Start recording data from the Guardian Earbuds
"""
import asyncio
from src.idun_guardian_client_beta.client import GuardianClient

EXPERIMENT: str = "Testing"
RECORDING_TIMER: int = 10
LED_SLEEP: bool = False

# start a recording session
bci = GuardianClient()
bci.address = asyncio.run(bci.search_device())

# start a recording session
asyncio.run(
    bci.start_local_recording(
        recording_timer=RECORDING_TIMER, led_sleep=LED_SLEEP, experiment=EXPERIMENT
    )
)
