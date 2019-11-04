import sounddevice as sd
import numpy as np
import struct
from issue42 import issue42

if __debug__:
    import sys

class issue45(issue42):

    def init(self, args):
        issue42.init(self, args)

    # Overriding receive_and_buffer method from parent
    def run(self):

        self.recorded_chunk_number = 0
        self.played_chunk_number = 0

        # Overriding receive_and_buffer method from parent
        def receive_and_buffer():
            message, source_address = self.receiving_sock.recvfrom(issue42.MAX_MESSAGE_SIZE)
            chunk_number, bitplane_index, *bp = struct.unpack(self.packet_format, message)

            unpacked_bp = np.unpackbits(np.asarray(bp, np.uint8))

            to_reproduce = unpacked_bp.astype(np.int16)

            self._buffer[chunk_number % self.cells_in_buffer][:, bitplane_index % self.number_of_channels] |= (to_reproduce << (bitplane_index // 2))

            return chunk_number

        # Overriding recond_send_and_play method from parent
        def record_send_and_play(indata, outdata, frames, time, status):

            data = np.frombuffer(indata, np.int16).reshape(self.frames_per_chunk, self.number_of_channels)

            data[:, 0] -= data[:, 1] 

            bitplane_index = (self.bits_per_number * self.number_of_channels) - 1
            while bitplane_index >= 0:
                bp = data[:, bitplane_index % self.number_of_channels] >> (bitplane_index // 2) & 1

                packed_bp = np.packbits(bp.astype(np.uint8))

                to_send = struct.pack(self.packet_format, self.recorded_chunk_number, bitplane_index, *(packed_bp))

                self.sending_sock.sendto(to_send, (self.destination_IP_addr, self.destination_port))

                bitplane_index -= 1

            self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER

            chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
            
            chunk[:, 0] += chunk[:, 1]

            self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
            self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
            outdata[:] = chunk
            if __debug__:
                sys.stderr.write("."); sys.stderr.flush()


        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=np.int16, channels=self.number_of_channels, callback=record_send_and_play):
            print("-=- Press CTRL + c to quit -=-")
            first_received_chunk_number = receive_and_buffer()
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            while True:
                receive_and_buffer()

if __name__ == "__main__":
    issue45 = issue45()
    parser = issue45.add_args()
    args = parser.parse_args()
    issue45.init(args)
    issue45.run()
