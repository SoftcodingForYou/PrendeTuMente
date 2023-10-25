import scipy.signal
from numpy                          import abs, zeros, pad


class Processing():

    def __init__(self):
		
		# These must be same as set in backend.py
        self.sample_rate    = 200
        self.buffer_length  = 5 * self.sample_rate

        #Signal processing
        self.filter_order   = 3 #scalar
        self.frequency_bands= {
            'Workshop':     (0.4,     2),
            'LineNoise':    (46,    54)}
        
        self.prepare_filters()


    def prepare_filters(self):

        # Bandpass filters
        # -----------------------------------------------------------------
        self.b_workshop, self.a_workshop        = scipy.signal.butter(
            self.filter_order, self.frequency_bands["Workshop"][0],
            btype='highpass', fs=self.sample_rate)
        self.b_notch, self.a_notch              = scipy.signal.butter(
            self.filter_order, self.frequency_bands["LineNoise"],
            btype='bandstop', fs=self.sample_rate)

        # Determine padding length for signal filtering
        # -----------------------------------------------------------------
        default_pad     = 3 * max(len(self.a_workshop), 
            len(self.b_workshop))
        if default_pad > self.buffer_length * self.sample_rate/10-1:
            self.padlen = int(default_pad) # Scipy expects int
        else:
            self.padlen = int(self.buffer_length*self.sample_rate/10-1) # Scipy expects int


    def filter_signal(self, signal, b, a):
        # =================================================================
        # Input:
        #   signal              Numpy 1D array [samples]
        # Output:
        #   signal_filtered[0]  1D numpy array of filtered signal where 
        #                       first sample is 0
        # =================================================================
        padded_signal   = pad(signal, (self.padlen, 0), 'symmetric')
        init_state      = scipy.signal.lfilter_zi(b, a) # 1st sample --> 0
        signal_filtered = scipy.signal.lfilter(b, a, padded_signal, 
            zi=init_state*padded_signal[0])
        signal_filtered = signal_filtered[0][self.padlen:]
        return signal_filtered


    def extract_envelope(self, signal):
        hilbert         = signal
        for iChan in range(signal.shape[0]):
            # padded_signal   = np.pad(signal[iChan,], (self.padlen, self.padlen), 'symmetric')
            # hilbert[iChan,] = np.abs(scipy.signal.hilbert(padded_signal))[self.padlen:-self.padlen]
            hilbert[iChan,] = abs(scipy.signal.hilbert(signal[iChan,]))
        return hilbert


    def downsample(self, buffer, s_down):
        # =================================================================
        # Input:
        #   buffer              Numpy array [channels x samples]
        # Output:
        #   downsamples_buffer  Numpy array of downsampled signal, same  
        #                       dimensions as input buffer
        # =================================================================
        numchans            = buffer.shape[0]
        downsampled_signal  = zeros((numchans, int(buffer.shape[1]/s_down)))
        idx_retain = range(0, buffer.shape[1], s_down)
        for iChan in range(numchans):
            # downsampled_signal[iChan,] = scipy.signal.decimate(buffer[iChan,], s_down)
            downsampled_signal[iChan,] = buffer[iChan,idx_retain]

        return downsampled_signal


    def prepare_buffer(self, buffer, bSB, aSB, bPB, aPB):
        # =================================================================
        # Input:
        #   buffer              Numpy array [channels x samples]
        #   bSB, aSB            Filter coefficients as put out by 
        #                       scipy.signal.butter (Stopband)
        #   bPB, aPB            Filter coefficients as put out by 
        #                       scipy.signal.butter (Passband)
        # Output:
        #   filtered_buffer     Numpy array of filtered signal, same  
        #                       dimensions as input buffer
        # =================================================================
        buffer_shape        = buffer.shape
        noise_free_signal   = zeros(buffer_shape)
        filtered_buffer     = zeros(buffer_shape)
        for iChan in range(buffer_shape[0]):

            # Reject ambiant electrical noise (at 50 Hz)
            # -------------------------------------------------------------
            if all(bSB != None):
                noise_free_signal[iChan,] = self.filter_signal(
                    buffer[iChan,], bSB, aSB)
            else:
                noise_free_signal[iChan,] = buffer[iChan,]

            # Extract useful frequency range
            # -------------------------------------------------------------
            if all(bPB != None):
                filtered_buffer[iChan,] = self.filter_signal(
                    noise_free_signal[iChan,], bPB, aPB)
            else:
                filtered_buffer[iChan,] = noise_free_signal[iChan,]

        return filtered_buffer
