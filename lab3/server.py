import socket
import sys
import threading
import time
import errno
import Queue


receivedMessageStart = "########## received message start ##########\n"
sentMessageStart = "########## sent message start ##########\n"
messageEnd = "\n########## message end ##########"


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
        return self.socket == other.socket

    def __eq__(self, other):
        return self.socket == other.socket

    def __str__(self):
        return str(self.joinId) + self.name


class Room(object):
    def __init__(self, name, member, ref):
        self.name = name
        self.members = []
        self.members.append(member)
        self.ref = ref

    def isEmpty(self):
        return not self.members

    def addMember(self, memberToAdd):
        # if memberToAdd not in self.members:
        self.members.append(memberToAdd)
        print "member added"
        print "members:"
    # else:
    #     print "member already"
        for m in self.members:
            print m

    def removeMember(self, memberToRemove):
        removed = False
        print "members before removal:"
        for m in self.members:
                print m
        for member in self.members:
            if member.socket == memberToRemove:
                print "removing:" + str(member)
                self.members.remove(member)
                print "members after removal:"
                for m in self.members:
                    print m
                removed = True
        if not removed:
            print "Not a member"

    def getName(self):
        return self.name

    def getRef(self):
        return self.ref

    def __cmp__(self, other):
        return self.ref == other.ref

    def __eq__(self, other):
        return self.ref == other.ref


class ThreadedServer(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.ip = "10.62.0.234"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.numWorkers = 15
        self.q = Queue.Queue(maxsize=1)
        self.roomsLock = threading.Lock()
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
                inputMessage = self.recvWithTimeout(client, 2)
                if inputMessage:
                    print receivedMessageStart + inputMessage + messageEnd
                if inputMessage.startswith("HELO"):
                    print "HELO message received"
                    inputMessage = inputMessage[:-1]
                    messageToBeSent = inputMessage + "\nIP:"+self.ip +\
                        "\nPort:"+str(self.port)+"\nStudentID:13325102\n"
                    print sentMessageStart + messageToBeSent + messageEnd
                    client.sendall(messageToBeSent)
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
                    # print inputMessage
                    # self.serverError(1, client)
                    time.sleep(1)

    def chat(self, inputMessage, client):
        message = inputMessage.split("\n", 3)
        ref = message[0][6:]
        joinId = message[1][9:]
        name = message[2][13:]
        sendableMessage = message[3][9:]
        print "name -" + name
        print "ref -" + ref
        print "join id -" + joinId
        print "message -" + sendableMessage
        self.roomsLock.acquire()
        try:
            for x in self.rooms:
                if str(x.getRef()) == ref:
                    print "room found"
                    if Member(name, joinId, client) in x.members:
                        for m in x.members:
                            print "sending message to " + str(m)
                            messageToBeSent = "CHAT:" + ref + "\nCLIENT_NAME:" +\
                                name + "\nMESSAGE:" + sendableMessage
                            print sentMessageStart + messageToBeSent + messageEnd
                            m.socket.sendall(messageToBeSent)
                    # else:
                    #     serverError()
        finally:
            self.roomsLock.release()

    def leave(self, inputMessage, client):
        message = inputMessage.split("\n")
        ref = message[0][16:]
        joinId = message[1][9:]
        name = message[2][13:]
        room = None
        self.roomsLock.acquire()
        try:
            for x in self.rooms:
                if str(x.getRef()) == ref:
                    messageToBeSent = "LEFT_CHATROOM:" + str(ref) + "\nJOIN_ID:" + joinId + "\n"
                    print sentMessageStart + messageToBeSent + messageEnd
                    client.sendall(messageToBeSent)
                    messageToBeSent = "CHAT:" + str(ref) + "\nCLIENT_NAME:" + name +\
                        "\nMESSAGE:" + name + " has left this chatroom.\n"
                    for m in x.members:
                        print sentMessageStart + messageToBeSent + messageEnd
                        m.socket.sendall(messageToBeSent)
                    x.removeMember(client)
                    if(x.isEmpty()):
                        self.rooms.remove(x)
                        print "room empty, deleting"
                    break
        finally:
            self.roomsLock.release()

    def join(self, inputMessage, client):
        message = inputMessage.split("\n")
        roomName = message[0][15:]
        clientName = message[3][13:]
        print "Room Name -" + roomName
        print "Client Name -" + clientName
        self.joinIdSeedLock.acquire()
        try:
            joinId = self.joinIdSeed
            self.joinIdSeed += 1
        finally:
            self.joinIdSeedLock.release()
        print "member joining with id -" + str(joinId)
        member = Member(clientName, joinId, client)
        ref = 0
        room = None
        self.roomsLock.acquire()
        try:
            for x in self.rooms:
                if x.getName() == roomName:
                    print "room found"
                    x.addMember(member)
                    added = True
                    ref = x.getRef()
                    room = x
                    break
            if room is None:
                print "room not found"
                self.roomRefSeedLock.acquire()
                try:
                    ref = self.roomRefSeed
                    self.roomRefSeed += 1
                finally:
                    self.roomRefSeedLock.release()
                if ref:
                    room = Room(roomName, member, ref)
                    self.rooms.append(room)
                    print "room created"
            messageToBeSent = "JOINED_CHATROOM:"+roomName+"\nSERVER_IP:"+self.ip+"\nPORT:"+str(self.port) +\
                "\nROOM_REF:" + str(ref) + "\nJOIN_ID:" + str(joinId) + "\n"
            print sentMessageStart + messageToBeSent + messageEnd
            client.sendall(messageToBeSent)
            for m in room.members:
                messageToBeSent = "CHAT:" + str(ref) + "\nCLIENT_NAME:" + clientName +\
                    "\nMESSAGE:" + clientName + " has joined this chatroom.\n"
                print sentMessageStart + messageToBeSent + messageEnd
                print "message sent to " + m.name
                m.socket.sendall(messageToBeSent)
        finally:
            self.roomsLock.release()

    def serverError(self, errornum, client):
        print "Some error occured"
        if errornum == 1:
            print
            client.sendall("ERROR_CODE:1\nERROR_DESCRIPTION:Invalid message received\n")
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
                elif err == 104:
                    "Client closed connection"
                    return ""
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
