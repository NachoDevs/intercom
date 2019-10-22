import sounddevice as sd
import numpy as np
import struct
from intercom_buffer import Intercom_buffer

if __debug__:
    import sys

class issue42(Intercom_buffer):

    def init(self, args):
        Intercom_buffer.init(self, args)
        
    # Overriding receive_and_buffer method from parent
    def run(self):
        # Overriding receive_and_buffer method from parent
        def receive_and_buffer():
            message, source_address = self.receiving_sock.recvfrom(Intercom_buffer.MAX_MESSAGE_SIZE)
            chunk_number, *chunk = struct.unpack(self.packet_format, message)
            
            # Reconstruimos el paquete

            self._buffer[chunk_number % self.cells_in_buffer] = np.asarray(chunk).reshape(self.frames_per_chunk, self.number_of_channels)
            return chunk_number

        # Overriding recond_send_and_play method from parent
        def record_send_and_play(indata, outdata, frames, time, status):

            # Dividir indata en una secuencia de 16 bitplanes

            bits_per_number = 16

            bitplanes = np.zeros( (bits_per_number * 2, self.frames_per_chunk) )

            i = 0
            while i < self.frames_per_chunk:
                j = bits_per_number - 1
                aux = 0
                while j >= bits_per_number:
                    bitplanes[aux][i] = (indata[i][0] >> j) & 1
                    bitplanes[aux + 1][i] = (indata[i][1] >> j) & 1

                    j -= 1
                    aux += 2
                i += 1

            # print(np.matrix(bitplanes))

            # print("---------")

            # Seleccionar bitplanes

            Intercom_buffer.run(self).record_send_and_play(indata, outdata, frames, time, status)

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