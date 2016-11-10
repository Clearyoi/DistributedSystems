import socket
import sys
import threading
import time
import errno
from multiprocessing import Pool, TimeoutError

class ThreadedServer(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.pool = Pool(processes=4) 

    def listen(self):
        self.sock.listen(5)
        while True:
            client, address = self.sock.accept()
            client.settimeout(15)
            # print "starting thread"
            # res = self.pool.apply_async(self.listenToClient, (client,address))
            # print res.get(timeout = 10)
            threading.Thread(target = self.listenToClient,args = (client,address)).start()

    def listenToClient(self, client, address):
        print "thread started"
        while True:
            input = self.recvWithTimeout(client,10)
            if input.startswith("HELO"):
                client.sendall(input + "\nIP:37.228.254.66\nPort:8000\nStudentID:13325102\n")
            elif input == "KILL_SERVICE\n":
                print "thread ended"
                client.close()
                return False
            elif input == "":
                print "no data recived thread ended"
                client.close()
                return False
            else:
                time.sleep(1)
        
        

    def recvWithTimeout(self, client, timeout):
        totalData = []
        client.setblocking(False)
        begin = time.time()
        while True:
            #if you got some data, then break after timeout
            if totalData and time.time()-begin > timeout:
                break
         
            #if you got no data at all, wait a little longer, twice the timeout
            elif time.time()-begin > timeout*2:
                break

            try:
                data = client.recv(10)
                if data:
                    totalData.append(data)
                    begin = time.time()
                else:
                    time.sleep(0.1)
            except socket.error, e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    time.sleep(1)
                    continue
                else:
                    # a "real" error occurred
                    print e
                    sys.exit(1)
            except:
                print sys.exc_info()[0]
                print "closing connection"
                client.close()
                return ""
        finalData =  "".join(totalData)
        return finalData

if __name__ == "__main__":
    # port_num = sys.argv[1]
    # print port_num
    port_num = 8000
    ThreadedServer('',port_num).listen()