import sounddevice as sd
import numpy as np
import struct
from intercom_binaural import Intercom_binaural

if __debug__:
    import sys

class issue44(Intercom_binaural):

    def init(self, args):
        Intercom_binaural.init(self, args)
        self.packet_format = f"!HBB{self.frames_per_chunk//8}B" # Chunk index; Column index; Bitplanes to send; Data
        self.bitplanes_to_send = self.number_of_channels * 16
        self.received_bitplanes = 0

    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom_binaural.MAX_MESSAGE_SIZE)
        chunk_number, bitplane_number, self.bitplanes_to_send, *bitplane = struct.unpack(self.packet_format, message)
        bitplane = np.asarray(bitplane, dtype=np.uint8)
        bitplane = np.unpackbits(bitplane)
        bitplane = bitplane.astype(np.int16)
        self.received_bitplanes += 1
        self._buffer[chunk_number % self.cells_in_buffer][:, bitplane_number%self.number_of_channels] |= (bitplane << bitplane_number//self.number_of_channels)
        return chunk_number

    def record_send_and_play_stereo(self, indata, outdata, frames, time, status):        
        indata[:, 0] -= indata[:, 1] 
        self.send(indata)
        
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        chunk[:, 0] += chunk[:, 1]

        self.bitplanes_to_send = self.received_bitplanes
        self.received_bitplanes = 0  
        print(self.bitplanes_to_send)
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        outdata[:] = chunk
        if __debug__:
            sys.stderr.write("."); sys.stderr.flush()

    def send(self, indata):
        for bitplane_number in range(self.bitplanes_to_send - 1, -1, -1):
            bitplane = (indata[:, bitplane_number%self.number_of_channels] >> bitplane_number//self.number_of_channels) & 1
            bitplane = bitplane.astype(np.uint8)
            bitplane = np.packbits(bitplane)
            message = struct.pack(self.packet_format, self.recorded_chunk_number, bitplane_number, self.bitplanes_to_send, *bitplane)
            self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))

if __name__ == "__main__":
    issue44 = issue44()
    parser = issue44.add_args()
    args = parser.parse_args()
    issue44.init(args)
    issue44.run()