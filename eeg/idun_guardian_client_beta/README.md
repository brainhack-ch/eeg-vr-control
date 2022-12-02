# User guide and documentation

## What can you do with the Python SDK?

1. You can use the Python SDK to search for the device.
2. You can use the Python SDK to connect and record data from the earbud.
3. You can download the data to your local machine.

---

## Prerequisites

- [Python 3.10](https://www.python.org/downloads/release/python-3100), if you already have another python version installed and you do not want to create a virtual environment to run the SDK, then you have to install Python 3.10 and [set it as your default Python](https://www.youtube.com/watch?v=zriWqGNJg4k).
    - If you have conflicts with other packages when installing the Python SDK:
        -  Use [Conda](https://www.anaconda.com/products/distribution) which will create an environment and configure your python version to the correct one with the following command: 
        
        ```bash
        conda create -n idun_env python=3.10
        ```
        or
        - Use [Pipenv](https://pypi.org/project/pipenv/) which will create your virtual environment manually using the following command.
        ```bash
        pipenv install --python 3.10
        ```
---

## Quick installation guide

1. Create a new repository or folder
2. Open the terminal in the same folder location or direct to that location within an already open terminal. For Windows you can use command prompt or Anaconda prompt, and Mac OS you can use the terminal or Anaconda prompt.

3. First activate the virtual environment if you have created one by using the following command, this command must always be run before using the python SDK:
    ```bash
    conda activate idun_env
    ```
    or
    ```bash
    pipenv shell
    ```

4. After the environment is activated, install the Python SDK using the following command:
    - With a [conda environment](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html) use the following command:
    ```bash
    pip install idun-guardian-client-beta
    ```
    or
    - With a [pipenv environment](https://pypi.org/project/pipenv/) use the following command:
    ```bash
    pipenv install idun-guardian-client-beta
    ```

5. After installing the package, make sure that the dependencies are correctly installed by running the following command and inspecting the packages installed in the terminal output:

    ```bash
    pip list
    ```

---

## How to use the Python SDK

You can also download all the SDK example files from our [GitHub repository](https://github.com/iduntech/idun-guardian-client-examples.git), or copy and paste it from the examples below.

### Example 1: Search for the device

1. Create a new file inside the folder where you created your environment and name it `search.py`
2. Open the terminal in the folder and activate your virtual environment using the steps from the [Quick installation guide](#quick-installation-guide).
3. Open the `search.py` file and copy the code from step 1 below.
4. Activate the virtual environment **only** if you have not already done so by using:

    ```bash
    conda activate idun_env
    ```
    or
    ```bash
    pipenv shell
    ```
4. Run the following command in the terminal to run the code after you have activate the enviroment:
    ```bash
    python search.py
    ```

#### Recommendation of steps to follow which is elaborated further below

1. Search for the device
2. Check the battery level
3. Check the impedance
4. Record data from the earbud
5. Download the data from the cloud using the recording ID

### **1. Search the earbud manually**

- To search for the earbud, you need to run the following command in your python shell or in your python script:

```python
import asyncio
from idun_guardian_client_beta import GuardianClient

bci = GuardianClient()

device_address = asyncio.run(bci.search_device())
```

- Follow the steps in the terminal to search for the earbud with the name `IGEB`
- If there are more than one IGEB device in the area, you will be asked to select the device you want to connect to connect to, a list such as below will pop up in the terminal:

    - For Windows:
    ```bash
    ----- Available devices -----

    Index | Name | Address
    ----------------------------
    0     | IGEB | XX:XX:XX:XX:XX:XX
    1     | IGEB | XX:XX:XX:XX:XX:XX
    2     | IGEB | XX:XX:XX:XX:XX:XX
    ----------------------------
    ```
    - For Mac OS:
    ```bash
    ----- Available devices -----
    Index | Name | UUID
    ----------------------------
    0    | IGEB | XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
    1    | IGEB | XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
    2    | IGEB | XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
    ----------------------------
    ```

- Enter the index number of the device you want to connect to.


### **2. Check battery level**

- To read out the battery level, you need to run the following command in your python shell or in your python script:

```python
import asyncio
from idun_guardian_client_beta import GuardianClient

bci = GuardianClient()
bci.address = asyncio.run(bci.search_device())

asyncio.run(bci.start_battery())
```

### **3. Check impedance values**

- To read out the impedance values, you need to run the following command in your python shell or in your python script:

```python
import asyncio
from idun_guardian_client_beta import GuardianClient

IMPEDANCE_DURATION = 5  # duration of impedance measurement in seconds
MAINS_FREQUENCY_60Hz = False
# mains frequency in Hz (50 or 60), for Europe 50Hz, for US 60Hz


# Get device address
bci = GuardianClient()
bci.address = asyncio.run(bci.search_device())

# start a recording session
asyncio.run(
    bci.start_impedance(
        impedance_display_time=IMPEDANCE_DURATION,
        mains_freq_60hz=MAINS_FREQUENCY_60Hz)
)
```

### **4. Start a recording**

- To start a recording with a pre-defined timer (e.g. `100` in seconds), you need to run the following command in your python shell or in your python script:

```python
import asyncio
from idun_guardian_client_beta import GuardianClient

EXPERIMENT: str = "Sleeping"
RECORDING_TIMER: int = 36000 # 10 hours in seconds
LED_SLEEP: bool = False

# start a recording session
bci = GuardianClient()
bci.address = asyncio.run(bci.search_device())

# start a recording session
asyncio.run(
    bci.start_recording(
        recording_timer=RECORDING_TIMER,
        led_sleep=LED_SLEEP,
        experiment=EXPERIMENT
    )
)

```

- To stop the recording, either wait for the timer to run out or interrupt the recording
    - with Mac OS enter the cancellation command in the terminal running the script, this would be `Ctrl+.` or `Ctrl+C`
    - with Windows enter the cancellation command in the terminal running the script, this would be `Ctrl+C` or `Ctrl+Shift+C`

### **4. Get all recorded info**

- To download the data, you need to first get the list of all your recordings and choose the one you would like to download
- Run the following command in your python shell or in your python script:

```python
from idun_guardian_client_beta.igeb_api import GuardianAPI

api = GuardianAPI()

# get a list of all recordings
recording_list = api.get_recordings_info_all(device_id = "XX-XX-XX-XX-XX-XX") # Device ID is derived from the MAC address of the earbud and in the log file

```

### **5. Get recording info**

- To list the information on a specific recording, you need to run the following command in your python shell or in your python script:

```python
from idun_guardian_client_beta.igeb_api import GuardianAPI

api = GuardianAPI()

# get single recording
api.get_recording_info_by_id(
    device_id = "XX-XX-XX-XX-XX-XX",
    recording_id = "xxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
)

```

### **5. Download recording**

- To download the data insert the `device_id` along with the `recording_id` and run the following command in your python shell or in your python script

```python
from idun_guardian_client_beta.igeb_api import GuardianAPI

api = GuardianAPI()

# download recording
api.download_recording_by_id(
    device_id = "XX-XX-XX-XX-XX-XX",
    recording_id = "xxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
)
# The info about th recording can be found in the log file
```
