import numpy as np
import socket
import json
import time
from threading import Thread

class Backend:

    def __init__(self):
        # =================================================================
        # Initialize receiver
        # -----------------------------------------------------------------
        # - Connect to socket
        # - Initialize zero buffer: self.buffer
        # - Initialize time stamps array of zeros: self.time_stamps
        # =================================================================

        # Set streaming parameters
        self.ip             = '127.0.0.1' # Localhost, requires Neuri GUI running
        self.port           = 12344
        self.sample_rate    = 200 # Hz

        # Set buffer parameters
        self.buffer_length  = 5 # s
        self.buffer_add     = 4 # s
        self.num_channels   = 2 # Neuri boards V1.0
        self.downsampling   = 5 # Downsampling factor (int)
        self.yrange         = [-200.0, +200.0] # float!

        # Stop recording
        self.stop           = False
        
        # Initialize zeros buffer and time stamps
        self.buffer         = self.prep_buffer(self.num_channels, self.buffer_length * self.sample_rate)
        self.time_stamps    = self.prep_time_stamps(self.buffer_length)
        self.start_time     = round(time.perf_counter() * 1000, 0)

        
    def prep_buffer(self, num_channels, length):
        # This functions creates the buffer structure
        # that will be filled with eeg datasamples
        return np.zeros((num_channels, length))


    def prep_time_stamps(self, length):
        return np.zeros(length)
    

    def prepare_socket(self, ip, port):
        
        # Setup UDP protocol: connect to the UDP EEG streamer
        receiver_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver_sock.bind((ip, int(port)))

        return receiver_sock


    def get_sample(self, readin_connection):

        valid_eeg = False
        # Get eeg samples from the UDP streamer
        raw_message, _  = readin_connection.recvfrom(1024)

        try:
            eeg_dict    = json.loads(raw_message)  # Vector with length self.num_channel
            eeg_data    = np.array([float(eeg_dict["c1"]), float(eeg_dict["c2"])])
            eeg_data    = np.expand_dims(eeg_data, 1)
            valid_eeg   = True
        except:
            eeg_data    = np.array([0.0, 0.0])
            print("Skipped message")
        
        return eeg_data, valid_eeg


    def get_time_stamp(self):
        return round(time.perf_counter() * 1000 - self.start_time, 4)


    def fill_buffer(self, sending_pipe, conn_socket):
        # This functions fills the buffer in self.buffer
        # that later can be accesed to perfom the real time analysis
        
        for _ in range(500):
            emptying_message, _  = conn_socket.recvfrom(1024)

        while not self.stop:
                
            # Get samples
            sample, valid       = self.get_sample(conn_socket)
            time_stamp          = self.get_time_stamp()

            if not valid:
                continue

            # Concatenate vector
            update_buffer = np.concatenate((self.buffer, sample), axis=1)

            # save to new buffer
            self.buffer = update_buffer[:, 1:]

            # Save time_stamp
            self.time_stamps = np.append(self.time_stamps, time_stamp)
            self.time_stamps = self.time_stamps[1:]

            # Push to frontend
            sending_pipe.send((self.buffer, time_stamp))

                
        self.receiver_sock.close()
        return


    def start_receiver(self, output_dir, subject_info):
        # Define thread for receiving
        self.receiver_thread = Thread(
            target=self.fill_buffer,
            name='receiver_thread',
            daemon=False)
        # Set start time
        self.start_time = time.perf_counter() * 1000  # Get recording start time
        # start thread
        self.receiver_thread.start()


    def stop_receiver(self, readin_connection):
        # Change the status of self.stop to stop the recording
        self.stop = True
        readin_connection.close()
        time.sleep(2)  # Wait two seconds to stop de recording to be sure that everything stopped
