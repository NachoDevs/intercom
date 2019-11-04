import sounddevice as sd
import numpy as np
import struct
from issue42 import issue42

if __debug__:
    import sys

class issue44(issue42):

    def init(self, args):
        issue42.init(self, args)

if __name__ == "__main__":
    issue44 = issue44()
    parser = issue44.add_args()
    args = parser.parse_args()
    issue44.init(args)
    issue44.run()
