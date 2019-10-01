import sounddevice as sd
import numpy
import socket
import queue
import intercom

if __debug__:
    import sys

# Inheritance from the Intercom class in intercom.py
class issue41(intercom.Intercom):

    packets_sent_counter = 0                        # To keep track of the amount of packets sent (for order purposes)
    packets_recieved_counter = 0                    # To keep track of the amount of packets recieved (for order purposes)
    buffer_size = 4                                 # Size of the buffer that will store the data
    packet_buffer = list(range(1, buffer_size))     # Here we will store the data recieved ordered by index
    received_packets = list(range(1, buffer_size))  # Structure to store the recieved packets
    packet_number_to_play = -1                      # To keep track of the current packet to play

    # Overriding the run method
    def run(self):
        sending_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiving_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listening_endpoint = ("0.0.0.0", self.listening_port)
        receiving_sock.bind(listening_endpoint)

        # We set the buffer to zeros
        for i in range(self.buffer_size):
            self.packet_buffer[i] = numpy.zeros(buffer_size)

        def receive_and_buffer():
            recieved_data, source_address = receiving_sock.recvfrom(
                intercom.Intercom.max_packet_size)

            # We interpret the binary data from the buffer as integers
            interpreted_data = numpy.frombuffer(recieved_data, numpy.int16)

            # The first digit we recieve is the index of the packet
            chunk_number = interpreted_data[0]
            # The rest is the corresponding data
            chunk = numpy.delete(interpreted_data, 0)

            self.packet_buffer[chunk_number] = chunk
            self.received_packets.append(chunk_number)

        def record_send_and_play(indata, outdata, frames, time, status):
            # We add the data to be send the index of this packet
            data_to_send = numpy.insert(
                numpy.frombuffer(
                    indata,
                    numpy.int16),
                0,
                self.packets_sent_counter)
            
            # We increment the sent packet counter
            self.packets_sent_counter+=1

            # print(data_to_send)
            
            # We send the data    
            sending_sock.sendto(
                data_to_send,
                (self.destination_IP_addr, self.destination_port))

            # If we haven't started playing
            if self.packet_number_to_play < 0:
                # If we have recieved packets that are separated by a distance bigger than half the size of the buffer
                #   we need to start playing to prevent loosing new information from the next packages
                if max(self.received_packets) - min(self.received_packets) > self.buffer_size / 2:
                    self.packet_number_to_play = min(self.received_packets)
            else:
                # We take the message corresponding with the next packet sent
                packet_to_send = self.packet_buffer[self.packet_number_to_play % self.buffer_size]
                # Now we reset this position since it has been send to be played
                self.packet_buffer[self.packet_number_to_play % self.buffer_size] = numpy.zeros(self.buffer_size)
                
                self.packet_number_to_play += 1
            
            # We increment the ammount of packets recieved to keep track of the order
            self.packets_recieved_counter += 1

            outdata[:] = numpy.reshape(
                    packet_to_send,
                    (self.samples_per_chunk, self.number_of_channels))
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
    args = issue.parse_args()
    issue.init(args)
    issue.run()
