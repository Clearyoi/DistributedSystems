import socket
import sys
import threading
import time
import errno
from multiprocessing import Pool, TimeoutError
import Queue

class ThreadedServer(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.ip = "37.228.254.66"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.numWorkers = 3
        self.q = Queue.Queue(maxsize=1)

    def listen(self):
        for i in range(self.numWorkers):
            threading.Thread(target = self.listenToClient).start()
        self.sock.listen(5)
        while True:
            client, address = self.sock.accept()
            client.settimeout(15)
            self.q.put((client,address),True)

    def listenToClient(self):
        while True:
            client, address = self.q.get()
            while True:
                input = self.recvWithTimeout(client,10)
                if input.startswith("HELO"):
                    client.sendall(input + "\nIP:"+self.ip+"\nPort:"+str(self.port)+"\nStudentID:13325102\n")
                elif input == "KILL_SERVICE\n":
                    print "kill service recieved job ended"
                    client.close()
                    self.q.task_done()
                    break
                elif input == "":
                    print "no data recived job ended"
                    client.close()
                    self.q.task_done()
                    break
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
    port_num = int(sys.argv[1])
    ThreadedServer('0.0.0.0',port_num).listen()