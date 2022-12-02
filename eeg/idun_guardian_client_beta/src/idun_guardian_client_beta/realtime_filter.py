import logging
from collections import deque
import numpy as np
from scipy import signal
from scipy.fftpack import fft


logger = logging.getLogger()


class RealtimePreprocess:  # pylint: disable=too-many-instance-attributes
    """
    The realtime preprocessing class is used for preprocessing the data in realtime.
    It provides realtime FFT as well as band-pass filtering. Furthermore it provides
    realtime frequency bar plots. The functions in this class uses samples and
    handles the buffering of the data. The two main functions are: calculate_fft
    and band_pass_static_filter. The calculate_fft function calculates the fft of the
    data and the band_pass_static_filter function calculates the band_pass filtered data.

    ...

    Attributes
    ----------
    sample_rate : int
        The sampling rate of the data.
    BUFFER_LENGTH : int
        The length of the buffer for the FFT calculation in seconds. This will
        determine the initial delay before FFT data is provided.
    min_freq : float
        The minimum frequency of the band-pass filter as well as FFT.
    max_freq : float
        The maximum frequency of the band-pass filter as well as FFT.
    data_buffer_length : int
        The length of the buffer for the FFT calculation in number of samples.
    data_buffer : deque
        The buffer for the FFT calculation.
    NOMINATOR : int
        The nominator of the FFT calculation.
    DENOMINATOR : int
        The denominator of the FFT calculation.
    NUM_CHANNELS : int
        The number of channels in the data.
    NUM_SAMPLES : int
        The number of samples in the data.
    zi : array
        The zi array for the filter. Which is tha actual filter
    filter_state : float
        The initial state of the filter.
    self.sample_counter : int
        The counter for the samples that goes through either the FFT
        or the band-pass filter calculation in order to keep
        track of the data.

    Methods
    -------
    calculate_fft(sample) : array
        This function calculates the fft of the data. It takes the sample as input
        and returns the fft data. The fft data is returned as an array with the
        frequencies and the amplitudes.
    band_pass_filter_epoch_based(sample) : array
        This function calculates the band-pass filtered data. It takes the sample as input
        and returns the band-pass filtered sample. The band-pass filtered sample is returned as a
        float. This filter has a delay of 1 second and a latency of 0.4 seconds.
    band_pass_filter_sample_based(sample) : array
        This function calculates the band-pass filtered data. It takes the sample as input
        and returns the band-pass filtered sample. The band-pass filtered sample is returned as a
        float. This filter has a delay of 3 second and a latency of 1.5 seconds.
    next_pow_two(x) : int
        This function returns the next power of 2 of the input.
    compute_psd(dataset) : array
        This function calculates the psd of the eeg data. It takes the eeg data as input
        and returns the psd data. The psd data is returned as an array with the
        frequencies and the amplitudes.
    additional_smoothing(freq_amplitude,indow_length,poly_order) : array
        This function smoothens the data. It takes the freq_amplitude as input and returns the
        smoothed data. The smoothed data is returned as a smoothed freq_amplitude array.
    extract_frequency_limits(freq_array, fft_array) : array
        This function extracts the frequency limits from the fft_array. It takes the freq_array
        and the fft_array as input and returns the cut data between the frequency limits. The
        frequency limits are determined by the initial low and high frequencies of the class.
    """

    def __init__(self, sample_rate=250, low_freq=1.0, high_freq=35.0):
        """
        This is the constructor of the class. It sets the sampling frequency.
        The low and high frequency are used to determine the frequency limits of the
        band-pass filter.

        """
        # FFT parameters
        self.sample_rate = sample_rate
        # This buffer will hold last n seconds of data and be used for
        # calculations
        self.buffer_length_seconds = 3
        # minimum and maximum frequencies
        self.min_freq = low_freq
        self.max_freq = high_freq
        self.data_buffer_length = self.buffer_length_seconds * self.sample_rate
        self.data_buffer = deque(maxlen=self.data_buffer_length)

        # band power buffer
        self.band_power_buffer_len_sec = 5
        self.band_power_buffer_len = self.band_power_buffer_len_sec * self.sample_rate
        self.band_power_buffer = deque(maxlen=self.band_power_buffer_len)

        # Filtering parameters
        self.nominator_filter = [1.0]
        self.num_channels_filter = 1
        self.num_samples_expect = 1

        self.sample_counter = 0

        # static filter
        self.lowpass_b, self.lowpass_a = create_filter_coefficients(
            high_freq, self.sample_rate, "lowpass", "butter"
        )

        self.highpass_b, self.highpass_a = create_filter_coefficients(
            low_freq, self.sample_rate, "highpass", "butter"
        )

        self.filter_buffer_length_seconds = 1
        self.extract_position_buffer = -100
        self.filter_data_buffer_length = (
            self.filter_buffer_length_seconds * self.sample_rate
        )
        self.filter_data_buffer = deque(maxlen=self.filter_data_buffer_length)

        self.delta_range = [1, 4]
        self.theta_range = [4, 8]
        self.alpha_range = [8, 12]
        self.beta_range = [12, 30]
        self.gamma_range = [30, 45]

    def compute_psd(self, dataset: np.ndarray) -> tuple:
        """Extract the features (band powers) from the EEG.

        Args:
            dataset (numpy.ndarray): array of dimension [number of samples,
                    number of channels

        Returns:
            (numpy.ndarray): feature matrix of shape [number of feature points,
                number of different features]
        """
        # 1. Compute the PSD
        win_sample_length = len(dataset)
        # Apply Hamming window
        ham_win = np.hamming(win_sample_length)
        data_win_centered = dataset - np.mean(dataset, axis=0)  # Remove offset
        data_win_centered_ham = (data_win_centered.T * ham_win).T
        next_power_two = next_pow_two(win_sample_length)
        fft_amplitude_arr = (
            np.fft.fft(data_win_centered_ham, n=next_power_two, axis=0)
            / win_sample_length
        )
        fft_array = 2 * np.abs(fft_amplitude_arr[0 : int(next_power_two / 2)])
        freq_array = np.array(
            self.sample_rate / 2 * np.linspace(0, 1, int(next_power_two / 2))
        )
        return freq_array, fft_array

    def extract_frequency_limits(
        self, freq_array: np.ndarray, fft_array: np.ndarray
    ) -> tuple:
        """
        This function receives the FFT data and extracts the frequency limits
        of the data.

        Args:
            freq_array (np.array): array of frequencies
            fft_array (np.array): array of FFT amplitudes

        Returns:
            cut_freq_array (np.array): array of frequencies within the
                frequency limits
            cut_fft_array (np.array): array of FFT amplitudes within the
                frequency limits
        """
        start_position = np.where(freq_array > self.min_freq)[0][0]
        end_position = np.where(freq_array > self.max_freq)[0][0]
        cut_freq_array = np.array(freq_array[start_position:end_position])
        cut_fft_array = np.array(fft_array[start_position:end_position])
        return cut_freq_array, cut_fft_array

    def create_fft_sample_based(self, sample: float) -> tuple:
        """
        This function receives samples and returns the frequency and amplitudes
        for the FFT. In the start it will return empty arrays until the buffer
        is full and then it will calculate the FFT and return the frequency and
        amplitudes values.

        Args:
            sample (float): sample of the EEG data

        Returns:
            freq_array (np.array): array of frequencies
            fft_array (np.array): array of FFT amplitudes
        """
        self.data_buffer.append(sample)
        freq_array = np.array([])
        fft_array = np.array([])
        if len(self.data_buffer) >= self.data_buffer_length:
            # compute fft
            epoch_array = np.array(self.data_buffer)
            temp_freq_arr, psd_arr = self.compute_psd(epoch_array)
            freq_array, fft_array = self.extract_frequency_limits(
                temp_freq_arr, psd_arr.flatten()
            )
            fft_array = do_additional_smoothing(fft_array)
            self.data_buffer.popleft()
        return freq_array, fft_array

    def band_pass_filter_sample_buffer_based(self, sample: float):
        """
        This function band-passes the entire dataset based on the initialized filter.
        A buffer is used and the data is removed at extract_position. This filter has a delay
        of 1 second and a latency of 0.4 seconds.

        Returns:
            filtered_dataset (np.array): filtered dataset of the EEG data
        """
        self.sample_counter += 1
        seconds_count = self.sample_counter / self.sample_rate
        self.filter_data_buffer.append(sample)
        filtered_sample = 0.0
        if len(self.filter_data_buffer) >= self.filter_data_buffer_length:
            epoch = np.array(self.filter_data_buffer)
            high_passed_epoch = signal.filtfilt(
                b=self.highpass_b,
                a=self.highpass_a,
                x=epoch,
                padtype=None,  # type: ignore
            )
            filtered_epoch = signal.filtfilt(
                b=self.lowpass_b,
                a=self.lowpass_a,
                x=high_passed_epoch,
                padtype=None,  # type: ignore
            )
            filtered_sample = filtered_epoch[-self.extract_position_buffer]
            self.filter_data_buffer.popleft()
        return seconds_count, filtered_sample

    def calculate_band_powers(self, sample: float) -> tuple:
        """
        This function receives samples and returns the time in seconds
        and the frequency band powers for the FFT. In the start it will return empty arrays until
        the buffer is full and then it will calculate the FFT band powers and update the buffer
        and calculation for each sample

        Args:
            sample (float): sample of the EEG data

        Returns:
            seconds_count (float): The current time for plotting
            delta_power (float): delta power of the EEG data
            theta_power (float): theta power of the EEG data
            alpha_power (float): alpha power of the EEG data
            beta_power (float): beta power of the EEG data
            gamma_power (float): gamma power of the EEG data
        """
        self.band_power_buffer.append(sample)
        self.sample_counter += 1
        seconds_count = self.sample_counter / self.sample_rate
        delta_power = 0.0
        theta_power = 0.0
        alpha_power = 0.0
        beta_power = 0.0
        gamma_power = 0.0
        if len(self.band_power_buffer) >= self.band_power_buffer_len:
            dataset_arr = np.array(self.band_power_buffer)
            delta_power = calculate_frequency_power(dataset_arr, self.delta_range)
            theta_power = calculate_frequency_power(dataset_arr, self.theta_range)
            alpha_power = calculate_frequency_power(dataset_arr, self.alpha_range)
            beta_power = calculate_frequency_power(dataset_arr, self.beta_range)
            gamma_power = calculate_frequency_power(dataset_arr, self.gamma_range)
            self.band_power_buffer.popleft()
        return (
            seconds_count,
            delta_power,
            theta_power,
            alpha_power,
            beta_power,
            gamma_power,
        )

def calculate_frequency_power(dataset, freq_range, power=2, sample_rate=250):
    """
    This function calculates the frequency power for a certain frequency band/s (^3)
    based on the eeg_bands dictionary.
    Parameters:
        dataset (int array) : label epochs
        eeg_bands (dictionary) : dictionary with band titles and ranges in Hz
    Returns:
        frequency_powers (float array) : array with fft power values based on ranges
    """
    # FFT
    dataset = np.array(dataset)
    fft_amplitude = abs(np.array(fft(dataset)) / int(len(dataset)))
    fft_amplitude_scaled = (2) * fft_amplitude
    fft_power = fft_amplitude_scaled**power
    # Frequency array
    time_len = len(dataset)
    time_end = time_len / sample_rate
    time_array = np.arange(0, time_end, 1 / sample_rate)
    freq_array = np.arange(0, sample_rate, (sample_rate) / len(time_array))
    # New frequency calculation
    low_freq_pos = np.where(freq_array > freq_range[0])[0][0]
    high_freq_pos = np.where(freq_array > freq_range[1])[0][0]
    power_band = fft_power[low_freq_pos:high_freq_pos]
    avg_power_band = float(np.mean(power_band))
    return avg_power_band

def create_filter_coefficients(
    frequency: float, sample_rate: int, band_type="highpass", filter_type="butter"
) -> tuple:
    """
    This function creates the filter coefficients.
    Parameters:
        frequency (int) : frequency of the filter
        sample_rate (int) : sampling frequency of the filter
        band_type (string) : type of the filter, either highpass or lowpass
        filter_type (string) : type of the filter, either butter or cheby1
    Returns:
        denom (numpy array) : numerator coefficients of the filter
        nom (numpy array) : denominator coefficients of the filter
    """

    denom, nom = signal.iirfilter(
        int(3),
        frequency,
        btype=band_type,
        ftype=filter_type,
        fs=float(sample_rate),
        output="ba",
    )
    return denom, nom

def next_pow_two(i):
    """
    Find the next power of 2 for number i
    """
    pwr_num = 1
    while pwr_num < i:
        pwr_num *= 2
    return pwr_num


def do_additional_smoothing(
    freq_amplitude: np.ndarray, window_length=11, poly_order=3
) -> np.ndarray:
    """
    This function receives the FFT data and smoothens by taking data in
    the window length and fitting a polynomial to it.
    Args:
        freq_amplitude (np.array): array of FFT amplitudes
        window_length (int): length of the window (must be an odd number)
        poly_order (int): order of the polynomial
    Returns:
        freq_amplitude (np.array): array of FFT amplitudes smoothed
    """
    # ensure that window_length is odd
    if window_length % 2 == 0:
        window_length += 1
    freq_amplitude = np.array(signal.savgol_filter(freq_amplitude, window_length, poly_order))
    return freq_amplitude
