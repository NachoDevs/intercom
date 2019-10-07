# python .\issue41.py -p 4443 -i 4445

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

    packets_sent_counter = 0                        # To keep track of the amount of packets sent (for order purposes)
    packets_recieved_counter = 0                    # To keep track of the amount of packets recieved (for order purposes)
    buffer_size = 4                                 # Size of the buffer that will store the data
    packet_buffer = list(range(0, buffer_size))     # Here we will store the data recieved ordered by index
    received_packets = list(range(0, buffer_size))  # Structure to store the recieved packets
    packet_number_to_play = -1                      # To keep track of the current packet to play

    struct_format = "!H{}h"

    # Overriding the run method
    def run(self):
        sending_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiving_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listening_endpoint = ("0.0.0.0", self.listening_port)
        receiving_sock.bind(listening_endpoint)

        # We set the struct amount of integers
        self.struct_format = self.struct_format.format(self.samples_per_chunk * self.bytes_per_sample)

        # We set the buffer to zeros
        for i in range(self.buffer_size):
            self.packet_buffer[i] = numpy.zeros(self.buffer_size)

        def receive_and_buffer():
            recieved_data, source_address = receiving_sock.recvfrom(
                self.max_packet_size)

            # We obtain the struct sent in the packet 
            #   The first digit we recieve is the index of the packet
            #   The rest is the corresponding data
            chunk_number, *chunk = struct.unpack(self.struct_format, recieved_data)

            # We interpret the binary data from the buffer as integers
            interpreted_chunk = numpy.frombuffer(chunk, numpy.int16)

            print(interpreted_chunk)
            self.packet_buffer[chunk_number % self.buffer_size] = interpreted_chunk
            self.received_packets.append(chunk_number)

        def record_send_and_play(indata, outdata, frames, time, status):
            # We add the data to be send the index of this packet
            recieved_data = numpy.frombuffer(
                    indata,
                    numpy.int16)

            packet_to_send = struct.pack(self.struct_format, self.packets_sent_counter, *recieved_data)

            # We increment the sent packet counter
            self.packets_sent_counter+=1

            # We send the data    
            sending_sock.sendto(
                packet_to_send,
                (self.destination_IP_addr, self.destination_port))

            # If we haven't started playing
            if self.packet_number_to_play < 0:
                # If we have recieved packets that are separated by a distance bigger than half the size of the buffer
                #   we need to start playing to prevent loosing new information from the next packages
                if max(self.received_packets) - min(self.received_packets) > self.buffer_size / 2:
                    self.packet_number_to_play = min(self.received_packets)
                packet_to_send = numpy.zeros((self.samples_per_chunk, self.bytes_per_sample), self.dtype)
            else:
                # We take the message corresponding with the next packet sent
                packet_to_send = self.packet_buffer[self.packet_number_to_play % self.buffer_size]
                # Now we reset this position since it has been send to be played
                self.packet_buffer[self.packet_number_to_play % self.buffer_size] = numpy.zeros(packet_to_send.size)
                
                self.packet_number_to_play += 1
            
            # We increment the ammount of packets recieved to keep track of the order
            self.packets_recieved_counter += 1


            print(type(packet_to_send))
            print(packet_to_send.shape)
            outdata = packet_to_send
            # outdata[:] = numpy.reshape(
            #         packet_to_send,
            #         (self.samples_per_chunk, self.number_of_channels))
            if __debug__:
                sys.stderr.write("."); sys.stderr.flush()

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
