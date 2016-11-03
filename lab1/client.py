import socket
import sys
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('localhost', 8000)
print >> sys.stderr,'connecting to %s port %s' % server_address
sock.connect(server_address)
CRLF = "\r\n\r\n"
try:
    
    # Send data
    message = "enter message here"
    message = message.replace(" ","+")
    connectString = "GET /echo.php?message=%s HTTP/1.0%s" % (message,CRLF)
    print >> sys.stderr,'sending "%s"' % message
    sock.sendall(connectString)

    # Look for the response
    str = ""    
    while True:
        data = sock.recv(10000)
        if data == "": break
        str += data

finally:
    str = str.replace("HTTP/1.0 200 OK","")
    str = str.replace("X-Powered-By: PHP/5.5.38","")
    str = str.replace("Content-type: text/html","")
    str = str.replace("Connection: close","")
    str = str.replace(CRLF,"")
    print str
    sock.close()