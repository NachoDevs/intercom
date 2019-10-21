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


            data = [[9, 10],[15, 13]]

            bitplanes = np.zeros( (16, 2) )

            for frame_index in range(4):
                print("Numero 1 a introducir: " + str(data[0][frame_index]))
                print("Numero 2 a introducir: " + str(data[0][frame_index + 1]))
                for bitplane_index in range(1):
                    bitplanes[frame_index][0] = (data[frame_index][bitplane_index] >> (frame_index)) & 1

                    bitplanes[frame_index][1] = (data[frame_index + 1][bitplane_index + 1] >> (frame_index + 4)) & 1

                    print(bitplane_index)
                    bitplane_index += 1
                    print(bitplane_index)
                    print("iteracion")

                    # if(bitplane_index % 2 == 0):
                    #     bitplanes[bitplane_index][frame_index] = (data[0][frame_index] >> bitplane_index) & 1
                    #     print("Plano:" + str(bitplane_index) + ", en posicion: " + str(frame_index) + \
                    #             ", introducimos:" + str((data[0][frame_index] >> bitplane_index) & 1))
                    # else:
                    #     bitplanes[bitplane_index][frame_index] = (data[0][frame_index + 1] >> bitplane_index) & 1
                    #     print("Plano:" + str(bitplane_index) + ", en posicion: " + str(frame_index) + \
                    #             ", introducimos:" + str((data[0][frame_index + 1] >> bitplane_index) & 1))


                    # bitplanes[bitplane_index][frame_index] = indata[- ((bitplane_index % 2) - 1)][frame_index] >> bitplane_index & 1 

                    # bitplane_index += 2

            for i in range(8):
                for j in range(2):
                    print(bitplanes[i][j])

            # Seleccionar bitplanes

            # Intercom_buffer.run(self).record_send_and_play(indata, outdata, frames, time, status)

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