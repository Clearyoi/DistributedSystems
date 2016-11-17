import socket
import sys
import threading
import time
import errno
import Queue


class Member(object):
    def __init__(self, name, joinId, socket):
        self.name = name
        self.joinId = joinId
        self.socket = socket

    def getName(self):
        return self.name

    def getJoinId(self):
        return self.joinId

    def __cmp__(self, other):
        return self.joinId == other.joinId

    def __str__(self):
        return str(self.joinId)


class Room(object):
    def __init__(self, name, member, ref):
        self.name = name
        self.members = [member]
        self.ref = ref

    def addMember(self, member):
        if member not in self.members:
            self.members.append(member)
            print "member added"
        else:
            print "member already"

    def removeMember(self, member):
        if member in self.members:
            self.members.remove(member)
            print "member removed"
        else:
            print "not a member"

    def getName(self):
        return self.name

    def getRef(self):
        return self.ref

    def __cmp__(self, other):
        return self.ref == other.ref


class ThreadedServer(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.ip = "10.62.0.234"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.numWorkers = 3
        self.q = Queue.Queue(maxsize=1)
        self.rooms = []
        self.joinIdSeedLock = threading.Lock()
        self.joinIdSeed = 1
        self.roomRefSeedLock = threading.Lock()
        self.roomRefSeed = 1

    def listen(self):
        for i in range(self.numWorkers):
            thread = threading.Thread(target=self.listenToClient)
            thread.setDaemon(True)
            thread.start()
        self.sock.listen(5)
        while True:
            client, address = self.sock.accept()
            client.settimeout(15)
            self.q.put((client, address), True)

    def listenToClient(self):
        while True:
            client, address = self.q.get()
            print "Connected"
            while True:
                inputMessage = self.recvWithTimeout(client, 10)
                if inputMessage.startswith("HELO"):
                    print "HELO message received"
                    inputMessage = inputMessage[:-1]
                    client.sendall(inputMessage + "\nIP:"+self.ip +
                                   "\nPort:"+str(self.port)+"\nStudentID:13325102")
                elif inputMessage == "KILL_SERVICE\n":
                    print "kill service recieved job ended"
                    client.close()
                    self.q.task_done()
                    break
                elif inputMessage.startswith("JOIN_CHATROOM"):
                    print "Join message received"
                    self.join(inputMessage, client)
                elif inputMessage.startswith("LEAVE_CHATROOM:"):
                    print "Leave message recieved"
                    self.leave(inputMessage, client)
                elif inputMessage.startswith("CHAT:"):
                    print "chat message received"
                    self.chat(inputMessage, client)
                else:
                    print inputMessage
                    # self.serverError(1, client)
                    time.sleep(1)

    def chat(self, inputMessage, client):
        message = inputMessage.split("\n", 3)
        ref = message[0][5:]
        joinId = message[1][8:]
        name = message[2][12:]
        sendableMessage = message[3][8:]
        print "name -" + name
        print "ref -" + ref
        print "join id -" + joinId
        print "message -" + sendableMessage
        for x in self.rooms:
            if str(x.getRef()) == ref:
                print "room found"
                if Member(name, joinId, client) in x.members:
                    for m in x.members:
                        print "message sent"
                        m.socket.sendall("CHAT:" + ref + "\nCLIENT_NAME:" +
                                         name + "\nMESSAGE:" + sendableMessage)
                # else:
                #     serverError()

    def leave(self, inputMessage, client):
        message = inputMessage.split("\n")
        ref = message[0][15:]
        joinId = message[1][8:]
        name = message[2][12:]
        # print "ref -" + ref
        # print "id -" + joinId
        # print "name -" + name
        for x in self.rooms:
            if str(x.getRef()) == ref:
                x.removeMember(Member(name, joinId, client))
                break
        client.sendall("LEFT_CHATROOM:" + ref + "\nJOIN_ID:" + joinId)

    def join(self, inputMessage, client):
        message = inputMessage.split("\n")
        roomName = message[0][14:]
        clientName = message[3][12:]
        print "Room Name -" + roomName
        print "Client Name -" + clientName
        self.joinIdSeedLock.acquire()
        try:
            joinId = self.joinIdSeed
            self.joinIdSeed += 1
        finally:
            self.joinIdSeedLock.release()
        member = Member(clientName, joinId, client)
        added = False
        ref = 0
        for x in self.rooms:
            if x.getName() == roomName:
                print "room found"
                x.addMember(member)
                added = True
                ref = x.getRef()
                break
        if not added:
            print "room not found"
            self.roomRefSeedLock.acquire()
            try:
                ref = self.roomRefSeed
                self.roomRefSeed += 1
            finally:
                self.roomRefSeedLock.release()
            if ref:
                self.rooms.append(Room(roomName, member, ref))
                print "room created"
        client.sendall("JOINED_CHATROOM:"+roomName+"\nSERVER_IP:"+self.ip+"\nPORT:"+str(self.port) +
                       "\nROOM_REF:" + str(ref) + "\nJOIN_ID:" + str(joinId))

    def serverError(self, errornum, client):
        if errornum == 1:
            client.sendall("ERROR_CODE:1\nERROR_DESCRIPTION:Invalid message received\n\n")
        else:
            client.sendall("ERROR_CODE:0\nERROR_DESCRIPTION:Unknown error\n\n")

    def recvWithTimeout(self, client, timeout):
        totalData = []
        client.setblocking(False)
        begin = time.time()
        while True:
            # if you got some data, then break after timeout
            if totalData and time.time()-begin > timeout:
                break
            # if you got no data at all, wait a little longer, twice the timeout
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
                    print sys.exc_info()[0]
                    print e
                    print "closing connection"
                    client.close()
                    return ""
            except:
                print sys.exc_info()[0]
                print "closing connection"
                client.close()
                return ""
        finalData = "".join(totalData)
        return finalData

if __name__ == "__main__":
    port_num = int(sys.argv[1])
    ThreadedServer('0.0.0.0', port_num).listen()
