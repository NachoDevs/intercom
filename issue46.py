# Don't send empty bitplanes.
#
# The sender adds to the number of received bitplanes the number of
# skipped (zero) bitplanes of the chunk sent.

# The receiver computes the first received
# bitplane (apart from the bitplane with the signs) and report a
# number of bitplanes received equal to the real number of received
# bitplanes plus the number of skipped bitplanes.

import struct
import numpy as np
from intercom import Intercom
from intercom_dfc import Intercom_DFC

if __debug__:
    import sys

class Intercom_empty(Intercom_DFC):

    def init(self, args):
        Intercom_DFC.init(self, args)
        self.received_bitplanes_per_chunk=[0]*self.cells_in_buffer
        #Counter of bitplanes that are 0's in the previous message sent
        self.counter=0
        
        #Override method from Intercom_DFC
    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
        received_chunk_number, received_bitplane_number, self.NORB, *bitplane = struct.unpack(self.packet_format, message)
        bitplane = np.asarray(bitplane, dtype=np.uint8)
        bitplane = np.unpackbits(bitplane)
        bitplane = bitplane.astype(np.uint16)
        self._buffer[received_chunk_number % self.cells_in_buffer][:, received_bitplane_number%self.number_of_channels] |= (bitplane << received_bitplane_number//self.number_of_channels)
        self.received_bitplanes_per_chunk[received_chunk_number % self.cells_in_buffer] += 1
        return received_chunk_number
    
        ##Override method from Intercom_DFC
    def send(self, indata):
        signs = indata & 0x8000
        magnitudes = abs(indata)
        indata = signs | magnitudes
        
        self.NOBPTS = int(0.75*self.NOBPTS + 0.25*self.NORB)
        self.NOBPTS += 1
        if self.NOBPTS > self.max_NOBPTS:
            self.NOBPTS = self.max_NOBPTS
        #Here we can know the number of 0 that were in the previous send
        self.counter = self.received_bitplanes_per_chunk[self.played_chunk_number % self.cells_in_buffer]
        #So, know we have to delete the number of bitplanes that are 0's, because they do not have information
        last_BPTS = self.max_NOBPTS - self.NOBPTS - 1 - self.counter
        self.send_bitplane(indata, self.max_NOBPTS-1)
        self.send_bitplane(indata, self.max_NOBPTS-2)
        for bitplane_number in range(self.max_NOBPTS-3, last_BPTS, -1):
            #Here we check if there are bitplanes that are 0's
            if np.any(indata) == True:
                #If there are not empty bitplanes, we can send the message
               self.send_bitplane(indata, bitplane_number)
            else:
                #If there are 0's, we can not send the message and we add 1 to the actual counter  
                self.received_bitplanes_per_chunk[self.played_chunk_number % self.cells_in_buffer] += 1
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER

if __name__ == "__main__":
    intercom = Intercom_empty()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()