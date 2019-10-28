import sounddevice as sd
import numpy as np
import struct
from intercom_buffer import Intercom_buffer

if __debug__:
    import sys

class issue42(Intercom_buffer):

    def init(self, args):
        self.bits_per_number = 16

        Intercom_buffer.init(self, args)

        self.packet_format = f"!HB{self.frames_per_chunk}h" # Indice del chunk; indice de la columna;info
        
    # Overriding receive_and_buffer method from parent
    def run(self):

        self.recorded_chunk_number = 0
        self.played_chunk_number = 0

        # Overriding receive_and_buffer method from parent
        def receive_and_buffer():
            message, source_address = self.receiving_sock.recvfrom(Intercom_buffer.MAX_MESSAGE_SIZE)
            chunk_number, column_index, *bp = struct.unpack(self.packet_format, message)

            to_reproduce = np.asarray(bp, np.int16)

            self._buffer[chunk_number % self.cells_in_buffer][:, column_index % 2] |= (to_reproduce << column_index//2)

            print(column_index)

            # self.recieved_column_number %= (self.bits_per_number * self.number_of_channels)

            return chunk_number

        # Overriding recond_send_and_play method from parent
        def record_send_and_play(indata, outdata, frames, time, status):

            data = np.frombuffer(indata, np.int16).reshape(self.frames_per_chunk, self.number_of_channels)
            
            print("Antes de enviar:")
            print(data)

            channel_index = 0
            for channel_index in range(self.number_of_channels):
                column_index = self.bits_per_number - 1
                while column_index >= 0:
                    bp = data[:, channel_index] >> column_index & 1
                    #packbits
                    to_send = struct.pack(self.packet_format, self.recorded_chunk_number, column_index, *(bp))
                    column_index -= 1

                    self.sending_sock.sendto(to_send, (self.destination_IP_addr, self.destination_port))

            self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER

            chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]

            print("Tras recibir:")
            print(chunk)

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
    issue42 = issue42()
    parser = issue42.add_args()
    args = parser.parse_args()
    issue42.init(args)
    issue42.run()