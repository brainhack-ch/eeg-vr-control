"""
Sample script for using the Guardian Earbud Client
- Start recording data from the Guardian Earbuds
"""
import asyncio
from src.idun_guardian_client_beta.client import GuardianClient

# Get device address
bci = GuardianClient()
bci.address = asyncio.run(bci.search_device())

# start a impedance session
asyncio.run(bci.start_battery())
