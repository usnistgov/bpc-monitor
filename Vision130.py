#! /usr/bin/env python

import socket # for socket
import struct
from numpy import NaN

# message format: <STX><CC><ADDRESS><LENGTH><CRC><ETX>
# <STX>: /, <CC>: command code, <CRC>: checksum, <ETX>: end transmission character
# message = b'/00ID' # Get ID
# message = b'/00RC' # Get TIME
# message = b'/00RW0000FF'  # Read all int addresses
# message = b'/00RNF000001' # Read single float address at address 0
class Vision130Driver:
    
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self._connect()

    def _connect(self,):
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.settimeout(1)
            print ("Socket successfully created")
        except Exception as err:
            print ("socket creation failed with error %s" %(err))
        self.eol = b'\r'
        try:
            self.s.connect((self.host, int(self.port)))
        except Exception as e:
            self.s.close()
            print ("Could not connect with socket-server (host/port error): %s" % e)
        except socket.error as e:
            self.s.close()
            print ("Connection error: %s" % e)

    def get_id(self,):
        header= [0xd7, 0x73, 0x65, 0x00, 0x08, 0x00]
        header = bytes(header)
        message = b'/00ID' # Get ID
        cs = self._calc_checksum(message)
        data = self._socket_comm(header + message + bytes(cs, 'utf-8') + self.eol)
    
    def get_time(self,):
        header= [0xd8, 0x73, 0x65, 0x00, 0x08, 0x00]
        header = bytes(header)
        message = b'/00RC'
        cs = self._calc_checksum(message)
        data = self._socket_comm(header + message + bytes(cs, 'utf-8') + self.eol)

    def get_all_float(self,):
        try:
            header= [0xd6, 0x73, 0x65, 0x00, 0x08, 0x00]
            header = bytes(header)
            message = b'/00RNF000018'
            cs = self._calc_checksum(message)
            data = self._socket_comm(header + message + bytes(cs, 'utf-8') + self.eol)
            
            all_my_data = data.split('RN')
            my_input = all_my_data[1]
            # print(len(my_input))
            dd = []
            for i in range(0, len(my_input), 4):
                dd.append(my_input[i:i+4])
            # print (dd)
            dd.pop(-1)
            ee = []
            for i, j in zip(dd[0::2], dd[1::2]):
                ee.append(j+i) 
            ff = []
            for i in ee:
                ff.append(struct.unpack('!f', bytes.fromhex(i))[0])
            return(ff)
        except:
            # try to reconnect
            self.close_comm()
            self._connect()
            return [NaN]*24

    def _calc_checksum(self, message):
        msg_list = [*message]
        mysum = 0
        for i in (msg_list[1:]):
            mysum = mysum + i
        return hex(mysum % 256)[2:].upper()    
    
    def _socket_comm(self, command):
        self.s.send(command)
        data = self.s.recv(1024)
        all_data = str(data.decode('unicode_escape'))
        return (all_data)
    
    def close_comm(self,):
        try:
            self.s.close()
        except Exception as err:
            print (str(err))
            pass

if __name__ == '__main__':
    print("I am main!")