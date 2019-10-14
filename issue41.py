# python issue41.py -p 4443 -i 4445 -a 192.168.1.13

import sounddevice as sd
import numpy
import socket
import queue
import intercom
import struct

if __debug__:
    import sys

# Inheritance from the Intercom class in intercom.py
class issue41(intercom.Intercom):

    buffer_size = 4                                 # Size of the buffer that will store the data
    packet_number_to_play = -1                      # To keep track of the current packet to play
    packets_sent_counter = 0                        # To keep track of the amount of packets sent (for order purposes)
    
    packet_buffer = list(range(0, buffer_size))     # Here we will store the data recieved ordered by index

    struct_format = "!H{}h"                         # Template for the structure of the packets to be sent

    def init(self, args):
        intercom.Intercom.init(self, args)

        # We set the struct amount of integers
        self.struct_format = self.struct_format.format(self.samples_per_chunk * self.number_of_channels)

        # We set the buffer to zeros
        for i in range(self.buffer_size):
            self.packet_buffer[i] = numpy.zeros((self.samples_per_chunk, self.bytes_per_sample), self.dtype)

    # Overriding the run method
    def run(self):
        sending_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiving_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listening_endpoint = ("0.0.0.0", self.listening_port)
        receiving_sock.bind(listening_endpoint)

        def receive_and_buffer():
            recieved_data, source_address = receiving_sock.recvfrom(
                self.max_packet_size)

            # We obtain the struct sent in the packet 
            #   The first digit we recieve is the index of the packet
            #   The rest is the corresponding data
            chunk=[]
            chunk_number, *chunk = struct.unpack(self.struct_format, recieved_data)

            # We store the data in its corresponding position
            self.packet_buffer[chunk_number % self.buffer_size] = chunk

        def send(indata):
            # We interpret the data as an 1d numpy array
            recieved_data = numpy.frombuffer(
                    indata,
                    numpy.int16)

            # We create the packet with the correct structure
            packet_to_send = struct.pack(self.struct_format, self.packets_sent_counter, *recieved_data)

            # We increment the sent packet counter
            self.packets_sent_counter+=1

            # We send the data    
            sending_sock.sendto(
                packet_to_send,
                (self.destination_IP_addr, self.destination_port))

        def record_send_and_buffer(indata, outdata, frames, time, status):
            
            # We send the data to the receiver
            send(indata)

            # Structure to store the indexes of recieved packets
            received_packets=[]
            # Strcuture to show how silence or no data is represented for later comparison
            no_data = numpy.zeros((self.samples_per_chunk, self.bytes_per_sample),self.dtype)
            for index in range(self.buffer_size):
                # Checking if the current packet has data
                if numpy.array_equal(self.packet_buffer[index], no_data) == False:
                    received_packets.append(index)
            
            # If we have found data
            if len(received_packets) > 0:
                # If we have recieved packets that are separated by a distance bigger than half the size of the buffer
                #   we need to start playing to prevent loosing new information from the next packages
                if (max(received_packets) - min(received_packets)) > (self.buffer_size / 2):
                    # We will start playing from the oldest packet we have stored
                    self.packet_number_to_play = min(received_packets)

            if __debug__:
                sys.stderr.write("·"); sys.stderr.flush()

        def record_send_and_play(indata, outdata, frames, time, status):
            
            # We send the data to the receiver
            send(indata)

            # We get the packet to be played
            packet_to_play = self.packet_buffer[self.packet_number_to_play % self.buffer_size]

            # Increment the index where we are taking the packet to reproduce
            self.packet_number_to_play += 1

            # We sent the packet to be played reshaped to fit the number of channels
            outdata[:] = numpy.reshape(
                    packet_to_play,
                    (self.samples_per_chunk, self.number_of_channels))

            if __debug__:
                sys.stderr.write("."); sys.stderr.flush()

        with sd.Stream(
                samplerate=self.samples_per_second,
                blocksize=self.samples_per_chunk,
                dtype=self.dtype,
                channels=self.number_of_channels,
                callback=record_send_and_buffer):
            print('-=- Press <CTRL> + <C> to quit -=-')
            while self.packet_number_to_play < 0:
                receive_and_buffer()

        with sd.Stream(
                samplerate=self.samples_per_second,
                blocksize=self.samples_per_chunk,
                dtype=self.dtype,
                channels=self.number_of_channels,
                callback=record_send_and_play):
            print('-=- Press <CTRL> + <C> to quit -=-')
            while True:
                receive_and_buffer()

if __name__ == "__main__":

    issue = issue41()
    parser = issue.add_args()
    args = parser.parse_args()
    issue.init(args)
    issue.run()
