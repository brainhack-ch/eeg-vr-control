"""
Sample script for using the Guardian Earbud Client
- Search for the Guardian Earbuds
"""
import asyncio
from src.idun_guardian_client_beta import GuardianClient

bci = GuardianClient()

# start a recording session
device_address = asyncio.run(bci.search_device())
