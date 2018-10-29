# -*- coding: utf-8 -*-
from twisted.internet.protocol import Protocol
from twisted.internet import reactor
from c2w.main.constants import ROOM_IDS
import logging
import struct
import re
import random

logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.tcp_chat_server_protocol')


class c2wTcpChatServerProtocol(Protocol):
    #{host_port : sesion}
    usersession = {}
    #{host_port : sequenceNumber, type} the server to the client
    usersequenceNumber = {}
    usercount ={}
    #{host_port : flag} to store the sequence of message received
    userflag={}
    #function callLater
    send= {}
    # {host_port : 0/1}1- leave the systeme 0- non
    leave={}
    loginpacket={}

    def __init__(self, serverProxy, clientAddress, clientPort):
        """
        :param serverProxy: The serverProxy, which the protocol must use
            to interact with the user and movie store (i.e., the list of users
            and movies) in the server.
        :param clientAddress: The IP address (or the name) of the c2w server,
            given by the user.
        :param clientPort: The port number used by the c2w server,
            given by the user.

        Class implementing the TCP version of the client protocol.

        .. note::
            You must write the implementation of this class.

        Each instance must have at least the following attribute:

        .. attribute:: serverProxy

            The serverProxy, which the protocol must use
            to interact with the user and movie store in the server.

        .. attribute:: clientAddress

            The IP address of the client corresponding to this 
            protocol instance.

        .. attribute:: clientPort

            The port number used by the client corresponding to this 
            protocol instance.

        .. note::
            You must add attributes and methods to this class in order
            to have a working and complete implementation of the c2w
            protocol.

        .. note::
            The IP address and port number of the client are provided
            only for the sake of completeness, you do not need to use
            them, as a TCP connection is already associated with only
            one client.
        """
        #: The IP address of the client corresponding to this 
        #: protocol instance.
        self.clientAddress = clientAddress
        #: The port number used by the client corresponding to this 
        #: protocol instance.
        self.clientPort = clientPort
        #: The serverProxy, which the protocol must use
        #: to interact with the user and movie store in the server.
        self.serverProxy = serverProxy
        self.host_port = (self.clientAddress,self.clientPort)
        self.userName = ''
        
        self.buffer = b''
        #to determine if the login is successful
        self.response = 0
        
       
        self.roomID = [1]
        for movie in self.serverProxy.getMovieList():
            self.roomID.append(movie.movieId)
       
        
    
    
#    def generateSequenceNumber(self,userName):
#        """
#        for every client
#        the sequence number incremented by one for each new packet 
#        the sequence number after 65535 is 0 
#        """
#        self.usersequenceNumber[userName][0] +=1
#        self.usersequenceNumber[userName][0] = self.usersequenceNumber[userName][0] % 65535
#        return self.usersequenceNumber[userName][0]
    
    def addr2dec(self, addr):
        """
        Convert  ip address to hexadecimal
        """
        items = [int(x) for x in addr.split(".")]
        return sum([items[i] << [24, 16, 8, 0][i] for i in range(4)])
    
    def ackResponse(self, data):
        """
         When receiving a package from the server, respond to an ack to confirm the reception
         Here we need to unpack the received datagram, extract the sessionToken, Sequencenumber
         the payload here is a 0
        """
        version = 1
        typeMessage = 0
        sessionToken_1, = struct.unpack('>H', data[1:3])
        sessionToken_2, = struct.unpack('>B', data[3:4])
        sequenceNumber, = struct.unpack('>H', data[4:6])
        payloadSize = 0
        buf = struct.pack('>BHBHH' , version*16+typeMessage, sessionToken_1, sessionToken_2,
                          sequenceNumber, payloadSize)
        print('********Send ACK**************')
        print("ack :" ,buf)
     
        self.transport.write(buf)
    
    
    def loginResponse(self, data):
        """
        when receiving the login request sent by the client, the server sent the login response
        """
        version = 1
        typeMessage = 2
        userLength, = struct.unpack('>H', data[10:12])
        userName, = struct.unpack('>%ds' %userLength, data[12:12+userLength])
        userName = userName.decode()
        self.userName = userName
        # Here we determine the loginRequest, we use responseCode (1 byte) to determine
        # The first case is Invalid User, which means that the user name has illegal characters. 
        # Here we use regular expressions. Need to introduce re library.
         # if login successful：
        if self.usercount[self.host_port][0] !=0 :
            buf = self.loginpacket[self.host_port][0]
        else :
             # Here we determine the loginRequest, we use responseCode (1 byte) to determine
            # The first case is Invalid User, which means that the user name has illegal characters. 
            #Here we use regular expressions. Need to introduce re library.
            try:
                if re.search(u'[^a-zA-Z0-9_.éèàçî]', userName):
                    responseCode = 1

                # The second case is that the username is too long (len(userName) > 100).
                elif userLength > 100:
                    responseCode = 2

                # The third situation is user name existed
                elif self.serverProxy.userExists(userName) :
                    responseCode = 3

                # The fourth situation is Service not available
                elif  len(self.serverProxy.getUserList()) > 65535:
                    responseCode = 4
                else:
                    responseCode = 0
            #Catching anomalies
            except userName:
                responseCode = 255
            # if login successful：    
            if responseCode == 0:
            
                userIdentifier = self.serverProxy.addUser(userName, ROOM_IDS.MAIN_ROOM, self,self.host_port)
                sequenceNumber = 0
                #Randomly generated 24bits binaire
                sessionToken = random.getrandbits(24)
                print("sessionToken :" , sessionToken)
                sessionToken_1 = sessionToken // 256
                sessionToken_2 = sessionToken % 256
                payloadSize = 5 + userLength
                buf = struct.pack('>BHBHHBHH%ds' %userLength, version*16+typeMessage, sessionToken_1, sessionToken_2,
                                  sequenceNumber, payloadSize, responseCode, userIdentifier, userLength, userName.encode('utf-8'))
       
           
               # if login is failed
            else:
                 # sessionToken = 0
                 sessionToken = 0
                 sessionToken_1 = sessionToken // 256
                 sessionToken_2 = sessionToken % 256
                 sequenceNumber = 0
                 userIdentifier = 0
                 payloadSize = 5 + userLength
                 buf = struct.pack('>BHBHHBHH%ds' %userLength, version*16+typeMessage, sessionToken_1, sessionToken_2,
                                   sequenceNumber, payloadSize, responseCode, userIdentifier, userLength, userName.encode('utf-8'))
            self.usersession[self.host_port] = [sessionToken_1,sessionToken_2]
            self.usersequenceNumber[self.host_port] = [0,2]
            self.loginpacket[self.host_port]=[buf]
            self.response = responseCode
        
        
        # Stop sending more than three times
        if self.usercount[self.host_port][0] ==3:
             print("Connection Lost")
             if self.leave[self.host_port] == 0 and self.response == 0: 
                 self.serverProxy.removeUser(self.userName)
                 self.leave[self.host_port] = 1
                 for user in self.serverProxy.getUserList() :
                     if user.userChatRoom == ROOM_IDS.MAIN_ROOM :
                         self.roomState(user)
            
        else:
            print('********Send LoginResponse***************')
            print("loginresponse :" , buf)
      
            self.transport.write(buf)
            
            # Here we consider retransmitting this message after timing 1s without receiving ack response. 
            # Stop sending more than three times
            self.usercount[self.host_port][0] +=1
            if self.usercount[self.host_port][0] <= 3:
                self.send[self.host_port]= [reactor.callLater(1, self.loginResponse, data)]
      
        
    
    def joinRoom(self,data):
        """
        when receiving the request of the join room, we need to unpack the message
        and change the user chatroom
        """
        roomId, = struct.unpack('>H', data[8 : 10])
        usernow = self.serverProxy.getUserByName(self.userName)
       
        # room id is wrong
        if roomId not in self.roomID:
            self.roomState(usernow)
        else:   
            #the client joins to main room
            if roomId == 1 :
                self.serverProxy.stopStreamingMovie(usernow.userChatRoom)
                userPastroom = usernow.userChatRoom
                self.serverProxy.updateUserChatroom(usernow.userName, ROOM_IDS.MAIN_ROOM)
                for user in self.serverProxy.getUserList():
                    if (user.userChatRoom == ROOM_IDS.MAIN_ROOM or user.userChatRoom == userPastroom):
                        self.roomState(user)
           #the client joins to movie room
            else :
                for movie in self.serverProxy.getMovieList() :
                    if movie.movieId == roomId :
                        self.serverProxy.startStreamingMovie(movie.movieTitle)
                        self.serverProxy.updateUserChatroom(usernow.userName, movie.movieTitle)
                        for user in self.serverProxy.getUserList():
                            if (user.userChatRoom == movie.movieTitle or user.userChatRoom == ROOM_IDS.MAIN_ROOM): 
                                self.roomState(user)
    
    
    def sendMessage(self, data):
        """
        The server now receives the message from the client. The next server will forward this 
        message to all users in the same room. So we will now consider extracting the user's ID 
        and then looking up his current room by ID.
        Traverse all users in this room and send this message to each user.
        """
        userID,= struct.unpack('>H', data[8:10])
        messageLength,= struct.unpack('>H', data[10:12])
        message, = struct.unpack('>%ds' %messageLength, data[12:])
        alluserList = self.serverProxy.getUserList()
        for user in alluserList :
            if user.userId== userID:
                userRoom = user.userChatRoom
                userName = user.userName
        # to send the message to other users who are in the same room with the sender
        for user in alluserList :
            if user.userChatRoom == userRoom  and user.userName != userName:
                version = 1
                typeMessage = 6
                sessionToken_1 = self.usersession[user.userAddress][0]
                sessionToken_2 = self.usersession[user.userAddress][1]
                payloadSize = 4+messageLength
               
                sequenceNumber = self.usersequenceNumber[user.userAddress][0]
                self.usersequenceNumber[user.userAddress][1] = 6
                buf = struct.pack('>BHBHHHH%ds' %messageLength, version*16+typeMessage, sessionToken_1,sessionToken_2,
                                              sequenceNumber, payloadSize, userID,messageLength, message)
                if self.usercount[user.userAddress][0] ==3:
                    print("Connection Lost")
                    if self.leave[user.userAddress] == 0:
                        self.serverProxy.removeUser(user.userName)
                        self.leave[user.userAddress] = 1
                        for user in self.serverProxy.getUserList() :
                            if (user.userChatRoom == ROOM_IDS.MAIN_ROOM or user.userChatRoom == userRoom):
                                self.roomState(user)
                    
                else :
                    #send the packet
                    print('*********Send Message**************')
                    print("message :", buf)
#                    print('***********************')
                    user.userChatInstance.transport.write(buf)
                
                    # Here we consider retransmitting this message after timing 1s without receiving ack response. 
                    # Stop sending more than three times
                    self.usercount[user.userAddress][0] +=1
                    if self.usercount[user.userAddress][0] <= 3:
                        self.send[user.userAddress]= [reactor.callLater(1, self.sendMessage, data)]
                
                
                
    def leaveSystem(self):    
        """
        when receiving the request of leave systeme, we need to remove the user and send the 
        room state to other user
        """
        self.serverProxy.removeUser(self.userName)
        for user in self.serverProxy.getUserList():
            if user.userChatRoom ==ROOM_IDS.MAIN_ROOM:
                self.roomState(user)
    
    def messageMainroom(self):
        """
        pack the data of the mainroom
        """
        #Create a new user list in the main room
        userMainList = []
       #Extract all users
        alluserList = self.serverProxy.getUserList()
        #Find the user in the main room in the list and add it to userMainList
        for user in alluserList :
            if user.userChatRoom == ROOM_IDS.MAIN_ROOM :
                userMainList.append((user.userName, user.userId))
      
        #to pack the data of the mainroom
        roomIdentifier = 1
        roomName = "Main Room"
        movieIP = 0
        moviePort = 0
        userNumber = len(userMainList)
        buf= struct.pack('>HH%dsIHH' %len(roomName.encode('utf-8')), roomIdentifier, len(roomName.encode('utf-8')),
                                     roomName.encode('utf-8'), movieIP, moviePort, userNumber)
        for i in range(userNumber) :
            userName = userMainList[i][0]
            userLength = len(userName.encode('utf-8'))
            userIdentifier = userMainList[i][1]
            buf = buf + struct.pack('>HH%ds' %userLength, userIdentifier, userLength, userName.encode('utf-8'))
            #print("mainroom", buf)
        return buf
    
    def messageMovieroom(self, movieTitle):
        """
         pack the data of the movie room
        """
        #Create a new user list in the movie room
        userMovieList =[]
        #Extract all users
        alluserList = self.serverProxy.getUserList()
        #Extract all movies
        allmovieList = self.serverProxy.getMovieList()
       
       #to find the user in the movie room
        for user in alluserList :
            if user.userChatRoom == movieTitle :
                userMovieList.append((user.userName, user.userId))
       
        
         #to pack the data in the movie room
        
        for movie in allmovieList :
            if movie.movieTitle == movieTitle :
                roomIdentifier = movie.movieId
                roomName = movieTitle
                movieIP = self.addr2dec(movie.movieIpAddress)
                #print("ip :", movieIP)
                moviePort = movie.moviePort
                userNumber = len(userMovieList)
                buf= struct.pack('>HH%dsIHH' %len(roomName.encode('utf-8')), roomIdentifier, len(roomName.encode('utf-8')),
                                             roomName.encode('utf-8'), movieIP, moviePort, userNumber) 
                for i in range(userNumber):
                    userName = userMovieList[i][0]
                    userLength = len(userName.encode('utf-8'))
                    userIdentifier = userMovieList[i][1]
                    buf = buf + struct.pack('>HH%ds' %userLength, userIdentifier, userLength, userName.encode('utf-8'))
                roomList = 0
                buf = buf +struct.pack('>H', roomList) 
        #print("movieroom" , buf)
        return buf

    def roomState(self, user):
        """
        to send the room state
        """
       

        version = 1
        typeMessage = 4
       
        #to get the room of the client
        sessionToken_1 = self.usersession[user.userAddress][0]
        sessionToken_2 = self.usersession[user.userAddress][1]
        
        sequenceNumber = self.usersequenceNumber[user.userAddress][0]
        self.usersequenceNumber[user.userAddress][1] = 4
        room = user.userChatRoom
      
        
        if room == ROOM_IDS.MAIN_ROOM :
            
            #if the client in the main room , call the function messageMainroom()
            mainbuf = self.messageMainroom()
            roomListLength = len(self.serverProxy.getMovieList())
            #to get the data of the movie room
            roomListbuf = struct.pack('>H', roomListLength)
            for movie in self.serverProxy.getMovieList():
                roomListbuf  = roomListbuf  + self.messageMovieroom(movie.movieTitle)
            payloadSize = len(mainbuf) + len(roomListbuf)
            #pack the header
            headbuf = struct.pack('>BHBHH', version*16+typeMessage, sessionToken_1, sessionToken_2,
                          sequenceNumber, payloadSize)
            #the whole packet
            buf = headbuf +mainbuf +roomListbuf
           
        #if the client in the movie room
        else :
            #to call the function messageMovieroom(room)
            moviebuf = self.messageMovieroom(room)
            payloadSize = len(moviebuf) 
            #the header
            headbuf = struct.pack('>BHBHH', version*16+typeMessage, sessionToken_1, sessionToken_2,
                          sequenceNumber, payloadSize)
            #the whole packet
            buf = headbuf +moviebuf
         
        # Stop sending more than three times
        if self.usercount[user.userAddress][0] ==3:
             print("Connection Lost")
             if self.leave[user.userAddress] == 0:
                 self.serverProxy.removeUser(user.userName)
                 self.leave[user.userAddress] = 1
                 for user in self.serverProxy.getUserList() :
                     if (user.userChatRoom == ROOM_IDS.MAIN_ROOM or user.userChatRoom == room):
                         self.roomState(user)
             
        else:
            #send the packet
            print('********Send RoomState***************')
            print("roomState :", buf)
#            print('***********************')
            user.userChatInstance.transport.write(buf)
            # Here we consider retransmitting this message after timing 1s without receiving ack response. 
            # Stop sending more than three times
            self.usercount[user.userAddress][0] +=1
            if self.usercount[user.userAddress][0] <= 3:
                self.send[user.userAddress] = [reactor.callLater(1, self.roomState, user)]
    
    def hello(self, sequenceNumber):
        """
        to check the client connection is still alive
        """ 
        
#        print("***************************************")
#        print("now number",self.userflag[userName][0])
#        print("past number",sequenceNumber)
        #the sequence number received change
        if sequenceNumber == self.userflag[self.host_port][0] :
            
        
            #more than three consecutive HEL without receiving an ack ,remove the user
            if self.usercount[self.host_port][0] ==3:
                print("Connection Lost")
                print('***********************')
                if self.leave[self.host_port] == 0:
                    user = self.serverProxy.getUserByAddress(self.host_port)
                    room = user.userChatRoom
                    self.serverProxy.removeUser(self.userName)
                    self.leave[self.host_port] = 1
                    for user in self.serverProxy.getUserList() :
                        if (user.userChatRoom == ROOM_IDS.MAIN_ROOM or user.userChatRoom == room):
                            self.roomState(user)
            else:
            
                version = 1
                typeMessage = 8
                sessionToken_1 = self.usersession[self.host_port][0]
                sessionToken_2 = self.usersession[self.host_port][1]
                
                sequence = self.usersequenceNumber[self.host_port][0]
                self.usersequenceNumber[self.host_port][1]=8
                payloadSize = 0
                buf = struct.pack('>BHBHH' , version*16+typeMessage, sessionToken_1, sessionToken_2,
                                  sequence, payloadSize)
                #send the packet
                print('********Send Hello***************')        
                print("hello :" ,buf)
#               print('***********************')
                self.transport.write(buf)
                # Here we consider retransmitting this message after timing 1s without receiving ack response. 
                # Stop sending more than three times
                self.usercount[self.host_port][0] +=1
                if self.usercount[self.host_port][0] <= 3:
                    self.send[self.host_port] = [reactor.callLater(1, self.hello,sequenceNumber)]
         
    def dataReceived(self, data):
        """
        :param data: The data received from the client (not necessarily
                     an entire message!)

        Twisted calls this method whenever new data is received on this
        connection.
        """
        # Here we store the received data  
        self.buffer = self.buffer + data
        while True:
            #if the length of the buffer is more than 8 bytes,we extract the payloadsize to determine
            #if the data received is complete
            if len(self.buffer) >= 8:
                payloadsize, = struct.unpack(">H", self.buffer[6:8])
                #if the length of the buffer is more than (8+payloadsize) bytes, we begin to unpack the 
                #data then get rid of the data which is proccessed
                if len(self.buffer) >= payloadsize + 8:
                    
                    #the version and  type, where we tend to take out the type.
                    buf,= struct.unpack('>B', self.buffer[0:1])
                    typeMessage = buf % 16
                    
                    (sessionToken_1, sessionToken_2, sequenceNumber) = struct.unpack('>HBH', self.buffer[1:6])
                    self.userflag[self.host_port]=[sequenceNumber]
                    print('********Datagram Received**************')
                    print("type",typeMessage)
                    print("sequence number",sequenceNumber)
                    print("data receive",self.buffer[:payloadsize + 8])
#                    print('***********************')
                    #f type is 0 --ack
                    if typeMessage== 0:
                        
                                 
                        if sequenceNumber == self.usersequenceNumber[self.host_port][0] and sessionToken_1==self.usersession[self.host_port][0]  and  sessionToken_2==self.usersession[self.host_port][1] :
#                            print("ACK Received")
#                            print('***********************')
                            print("*******ACK Received******")
                            self.send[self.host_port][0].cancel()
                            self.usercount[self.host_port]=[0]
                            self.usersequenceNumber[self.host_port][0] = (self.usersequenceNumber[self.host_port][0]+1) % 65535
                            if sequenceNumber== 0 and self.usersequenceNumber[self.host_port][1] == 2 and self.response == 0:
                                for user in self.serverProxy.getUserList() :
                                    if user.userChatRoom ==ROOM_IDS.MAIN_ROOM:
                                        self.roomState(user)
                    #if not, we need to send an ack to server in order to ensure the reception of the data
                    else:
#                    elif  typeMessage != 0 and sequenceNumber == self.receive :
#                        self.receive = (self.receive + 1)%65535
                        self.ackResponse(self.buffer[:payloadsize + 8])
                        # type = 1 --- login request
                        if typeMessage == 1:
                            print("login request")
                            self.leave[self.host_port] = 0
                            self.usercount[self.host_port]=[0]
                            self.loginResponse(self.buffer[:payloadsize + 8])
                        #type = 5--join room
                        elif typeMessage == 5 and sessionToken_1==self.usersession[self.host_port][0]  and  sessionToken_2==self.usersession[self.host_port][1]:
                            print("join room")
                            self.joinRoom(self.buffer[:payloadsize + 8])
                        #type = 6-- send message
                        elif typeMessage == 6 and sessionToken_1==self.usersession[self.host_port][0]  and  sessionToken_2==self.usersession[self.host_port][1]:
                            print("chat message")
                            self.sendMessage(self.buffer[:payloadsize + 8])
                        #type = 7 -- leave systeme
                        elif typeMessage == 7 and sessionToken_1==self.usersession[self.host_port][0]  and  sessionToken_2==self.usersession[self.host_port][1]:
                            print("leave system")
                            self.leaveSystem()
                            self.leave[self.host_port] = 1
                    #to get rid of the data proccessed
                    self.buffer = self.buffer[(payloadsize + 8):]
                    if  self.leave[self.host_port] == 0 and self.response == 0 :  
                        
                        #call the function hello , if no message receiving during 10s
                        reactor.callLater(10,self.hello, sequenceNumber)
 
                else:
                    break;
            else:
                break;
      
