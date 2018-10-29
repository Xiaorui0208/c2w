# -*- coding: utf-8 -*-
from twisted.internet.protocol import Protocol
from twisted.internet import reactor
from c2w.main.constants import ROOM_IDS
import logging
import struct


logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.tcp_chat_client_protocol')


class c2wTcpChatClientProtocol(Protocol):

    def __init__(self, clientProxy, serverAddress, serverPort):
        """
        :param clientProxy: The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.
        :param serverAddress: The IP address (or the name) of the c2w server,
            given by the user.
        :param serverPort: The port number used by the c2w server,
            given by the user.

        Class implementing the UDP version of the client protocol.

        .. note::
            You must write the implementation of this class.

        Each instance must have at least the following attribute:

        .. attribute:: clientProxy

            The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.

        .. attribute:: serverAddress

            The IP address of the c2w server.

        .. attribute:: serverPort

            The port number used by the c2w server.

        .. note::
            You must add attributes and methods to this class in order
            to have a working and complete implementation of the c2w
            protocol.
        """

        #: The IP address of the c2w server.
        self.serverAddress = serverAddress
        #: The port number used by the c2w server.
        self.serverPort = serverPort
        #: The clientProxy, which the protocol must use
        #: to interact with the Graphical User Interface.
        self.clientProxy = clientProxy
        #: the serial number of the packet send by the client
        self.sequenceNumber = 0
        # : the instance of a client-server connection
        self.sessionToken_1 = 0
        self.sessionToken_2 = 0
        #: the name of  the client
        self.userName = ''
        #: the identifier of the client
        self.userIdentifier = 0
        #:the state of the client
        self.userState = 0 
        #:{roomname: roomid}
        self.roomId={}
        #:{userid : username}
        self.idUser={}
        #:{sequenceNumber:typeMessage}
        self.sequencetotype={}
        #: the number of times the same packet was sent
        self.callCount = 0
        #: to store the room name which the client wants to join
        self.roomName=''
#        #sequence received without ack
#        self.receive=0
        #function callLater
        self.send= None
        self.buffer=b''
      
#    def generateSequenceNumber(self):
#        """
#        the sequence number incremented by one for each new packet
#        the sequence number after 65535 is 0 
#        """
#        self.sequenceNumber+=1
#        self.sequenceNumber = self.sequenceNumber % 65535
#        return self.sequenceNumber
    
    def dec2addr(self,dec):
        """
        Convert  hexadecimal to  ip address 
        """
        return ".".join([str(dec >> x & 0xff) for x in [24,16,8,0]])

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
        print('*********Send ACK**************')
        print("ack :", buf)
#        print('***********************')
        self.transport.write(buf)
    
    def loginResponse(self, data):
        """
        to process login response
        """
        #take out  the responseCode and determine if it is a successful login
        (responseCode,userIdentifier,userNameLength)= struct.unpack('>BHH',data[8:13])
        userName, = struct.unpack('>%ds' %userNameLength, data[13:13+userNameLength])
        userName = userName.decode()
        #responseCode = 0, login successful
        if responseCode == 0:
#            print("Log in Successful")
            #to store the session token assigned by the server
            (self.sessionToken_1, self.sessionToken_2)= struct.unpack('>HB', data[1:4])
            self.userName = userName
            self.userIdentifier = userIdentifier
        #sinon, the login is refused
        elif responseCode == 1:
            self.clientProxy.connectionRejectedONE("Invalide User") 
        elif responseCode == 2:
            self.clientProxy.connectionRejectedONE("Username too long") 
        elif responseCode == 3:
            self.clientProxy.connectionRejectedONE("Username not available") 
        elif responseCode == 4:
            self.clientProxy.connectionRejectedONE("Service not available")    
        elif responseCode == 255:
            self.clientProxy.connectionRejectedONE("Unknown Error")

    def unpackMovieroomdata(self,data):
        """
        unpack the data of the movie room
        """
        # to store the user data
        userList = []
        (roomIdentifier,roomNameLength) = struct.unpack('>HH', data[8:12])
        roomName, = struct.unpack('>%ds' %roomNameLength, data[12:12+roomNameLength])
        roomName =  roomName.decode()
        offset = 12+roomNameLength
        (movieIP,moviePort,userNumber) = struct.unpack('>IHH', data[offset:offset +8])
        movieIP = self.dec2addr(movieIP)
        offset +=8
        #Recycling to unpacke the user data of the movie room
        if userNumber != 0:
                for i in range(userNumber) :
                    (userIdentifier,userNameLength) = struct.unpack('>HH', data[offset:offset +4])
                    offset += 4
                    userName ,= struct.unpack('>%ds' %userNameLength, data[offset:offset +userNameLength])
                    userName = userName.decode()
                    #to store the identifier and name of other client
                    self.idUser[userIdentifier]=[userName]
                    offset += userNameLength
                    userList.append((userName, roomName))
                    
        return userList
        
        
     
    def unpackMainroomdata(self, data): 
        """
        unpack the data of the main room
        """
        
        # to store the user data
        userList = []
        #to store the movie data
        movieList=[]
        (roomIdentifier,roomNameLength) = struct.unpack('>HH', data[8:12])
        #the number of user in the main room
        offset = 18 + roomNameLength
        userNumber, = struct.unpack('>H', data[offset:offset +2])
        offset += 2
        #Recycling to unpacke the user data of the main room
        for i in range(userNumber) :
            (userIdentifier,userNameLength) = struct.unpack('>HH', data[offset:offset +4])
            offset += 4
            userName ,= struct.unpack('>%ds' %userNameLength, data[offset:offset +userNameLength])
            userName = userName.decode()
            #to store the identifier and name of other client
            self.idUser[userIdentifier]=[userName]
            offset += userNameLength
            userList.append((userName, ROOM_IDS.MAIN_ROOM))
        #unpack the number of movie room
        movieRoomNumber, = struct.unpack('>H', data[offset:offset +2])
        offset += 2
        #Recycling to unpacke the  data of the movie room
        for i in range(movieRoomNumber) :
            (movieId,movieNameLength)= struct.unpack('>HH', data[offset:offset +4])
            offset += 4
            movieName, = struct.unpack('>%ds' %movieNameLength, data[offset:offset +movieNameLength])
            movieName = movieName.decode()
            offset += movieNameLength
            (movieIP,moviePort,userNumber) = struct.unpack('>IHH', data[offset:offset +8])
            movieIP = self.dec2addr(movieIP)
            offset +=8
            self.roomId[movieName] = [movieId]
            movieList.append((movieName, movieIP, moviePort))
            #Recycling to unpacke the  user data in the movie room
            if userNumber == 0:
                offset += 2
            else :
                for i in range(userNumber) :
                    (userIdentifier,userNameLength) = struct.unpack('>HH', data[offset:offset +4])
                    offset += 4
                    userName ,= struct.unpack('>%ds' %userNameLength, data[offset:offset +userNameLength])
                    userName = userName.decode()
                    #to store the identifier and name of other client
                    self.idUser[userIdentifier]=[userName]
                    offset += userNameLength
                    userList.append((userName,movieName))
                offset += 2
        return userList,movieList
    
    def roomState(self,data):
        (roomIdentifier,roomNameLength) = struct.unpack('>HH', data[8:12])
        roomName, = struct.unpack('>%ds' %roomNameLength, data[12:12+roomNameLength])
        roomName = roomName.decode()
#        print("roomName",roomName)
        #the room is Main ROOM
        if roomName == "Main Room" :
            self.roomId[ROOM_IDS.MAIN_ROOM] = [roomIdentifier]
            userList,movieList = self.unpackMainroomdata(data)
            #if login successful,initial the room
            if self.userState == 0 :
                self.clientProxy.initCompleteONE(userList, movieList)
                self.userState = 1
            #update the user list
            else:
                self.clientProxy.setUserListONE(userList)
        #the room is movie room,update the user list
        else:
            userList = self.unpackMovieroomdata(data)
            self.clientProxy.setUserListONE(userList)
    
    def displayMessage(self,data):
        """
        when receiving the message , we need to display the message
        """
        (userId, messageLength) = struct.unpack('>HH', data[8:12])
        message, = struct.unpack('>%ds' %messageLength, data[12:])
        self.clientProxy.chatMessageReceivedONE(self.idUser[userId][0],message.decode())
                        
    def sendLoginRequestOIE(self, userName):
        """
        :param string userName: The user name that the user has typed.

        The client proxy calls this function when the user clicks on
        the login button.
        """
        moduleLogger.debug('loginRequest called with username=%s', userName)
        # Stop sending more than three times
        if self.callCount == 3 :
            self.clientProxy.connectionRejectedONE("Connection Lost")
           
        version = 1
        typeMessage = 1
        sessionToken = 0
        sessionToken_1 = sessionToken // 256
        sessionToken_2 = sessionToken % 256
        sequenceNumber = 0
        userIdentifier = 0
        userLength = len(userName.encode('utf-8'))
        payloadSize = 4+len(userName.encode('utf-8'))

       # Here we create a buffer to store data, buffer is the standard data type after pack.
        buf = struct.pack('>BHBHHHH%ds' %userLength, version*16+typeMessage, sessionToken_1, sessionToken_2,
                          sequenceNumber, payloadSize, userIdentifier, userLength, userName.encode('utf-8'))
        print('********Send LoginRequest***************')
        print("sendLoginRequest :", buf)
#        print('***********************')
        self.transport.write(buf)
        #Store the serial number and type of the sent message
        self.sequencetotype[sequenceNumber]=[typeMessage]
        # Here we consider retransmitting this message after timing 1s without receiving ack response. 
        self.callCount += 1
        if self.callCount <= 3 :
            #function callLater
            self.send = reactor.callLater(1, self.sendLoginRequestOIE, userName)
    
    def sendChatMessageOIE(self, message):
        """
        :param message: The text of the chat message.
        :type message: string

        Called by the client proxy when the user has decided to send
        a chat message

        .. note::
           This is the only function handling chat messages, irrespective
           of the room where the user is.  Therefore it is up to the
           c2wChatClientProctocol or to the server to make sure that this
           message is handled properly, i.e., it is shown only by the
           client(s) who are in the same room.
        """
        # Stop sending more than three times
        if self.callCount == 3 :
            self.clientProxy.connectionRejectedONE("Connection Lost")
           
        version = 1
        typeMessage = 6
        
        sequenceNumber = self.sequenceNumber
        payloadSize = 4+len(message.encode('utf-8'))
        #pack the whole message
        buf = struct.pack('>BHBHHHH%ds' %len(message.encode('utf-8')), version*16+typeMessage, self.sessionToken_1, self.sessionToken_2,
                                      sequenceNumber, payloadSize, self.userIdentifier,len(message.encode('utf-8')), message.encode('utf-8'))
        print('********Send Message***************')
        print("send message:",buf)
#        print('***********************')
        self.transport.write(buf)
        #Store the serial number and type of the sent message
        self.sequencetotype[sequenceNumber]=[typeMessage]
        
        # Here we consider retransmitting this message after timing 1s without receiving ack response. 
        
        self.callCount += 1
        if self.callCount <= 3 :
             self.send = reactor.callLater(1, self.sendChatMessageOIE, message)
        

    def sendJoinRoomRequestOIE(self, roomName):
        """
        :param roomName: The room name (or movie title.)

        Called by the client proxy  when the user
        has clicked on the watch button or the leave button,
        indicating that she/he wants to change room.

        .. warning:
            The controller sets roomName to
            c2w.main.constants.ROOM_IDS.MAIN_ROOM when the user
            wants to go back to the main room.
        """
        # Stop sending more than three times
        if self.callCount == 3 :
            self.clientProxy.connectionRejectedONE("Connection Lost")
            
        self.roomName = roomName
        version = 1
        typeMessage = 5
       
        sequenceNumber = self.sequenceNumber
        payloadSize = 2
        buf = struct.pack('>BHBHHH' , version*16+typeMessage, self.sessionToken_1, self.sessionToken_2,
                          sequenceNumber, payloadSize,self.roomId[roomName][0])
        print('********Send Join Room Request***************')
        print("JoinRoomRequest:" , buf)
       
        self.transport.write(buf)
        #Store the serial number and type of the sent message
        self.sequencetotype[sequenceNumber]=[typeMessage]
        
        # Here we consider retransmitting this message after timing 1s without receiving ack response. 

        self.callCount += 1
        if self.callCount <=3 :
             self.send = reactor.callLater(1, self.sendJoinRoomRequestOIE, roomName)
 
        
    def sendLeaveSystemRequestOIE(self):
        """
        Called by the client proxy  when the user
        has clicked on the leave button in the main room.
        """
        # Stop sending more than three times
        if self.callCount == 3 :
            self.clientProxy.connectionRejectedONE("Connection Lost")
            
        version = 1
        typeMessage = 7
       
        sequenceNumber = self.sequenceNumber
        payloadSize = 0
        buf = struct.pack('>BHBHH' , version*16+typeMessage, self.sessionToken_1, self.sessionToken_2,
                                      sequenceNumber, payloadSize)
        print('*********Send Leave System Request**************')
        print("LeaveSystemRequest:" , buf)
      
        self.transport.write(buf)
        #Store the serial number and type of the sent message
        self.sequencetotype[sequenceNumber]=[typeMessage]
        
        # Here we consider retransmitting this message after timing 1s without receiving ack response. 
      
        self.callCount += 1
        if self.callCount <=3 :
             self.send = reactor.callLater(1, self.sendLeaveSystemRequestOIE)
       

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
                    print('********Datagram Received***************')
                    print("type",typeMessage)
                    print("sequence number",sequenceNumber)
                    print("data receive",self.buffer[:payloadsize + 8])
                    
                    #if type is 0 --ack
                    if typeMessage== 0:
                        if sequenceNumber == self.sequenceNumber and sessionToken_1==self.sessionToken_1  and  sessionToken_2==self.sessionToken_2:
                             print("*******ACK Received******")
                             self.send.cancel()
                             self.callCount = 0
                             self.sequenceNumber = (self.sequenceNumber + 1)%65535
                             # If the type is 7, it means the server has received the request to leave the system, then the customer leaves
                             if self.sequencetotype[sequenceNumber][0]==7:
                                 self.clientProxy.userUpdateReceivedONE(self.userName, ROOM_IDS.OUT_OF_THE_SYSTEM_ROOM)
                                 self.clientProxy.leaveSystemOKONE()
                            # If the type is 5, it means the server has received the request to join the room.
                             if self.sequencetotype[sequenceNumber][0]==5:
                                 self.clientProxy.userUpdateReceivedONE(self.userName, self.roomName)
                                 self.clientProxy.joinRoomOKONE()
                    #if not, we need to send an ack to server in order to ensure the reception of the data
                    else:
#                    elif  typeMessage != 0 and sequenceNumber == self.receive :
#                        self.receive = (self.receive + 1)%65535
                        self.ackResponse(self.buffer[:payloadsize + 8])
                        #type =2 --- login response
                        if typeMessage== 2:
                            print("login response")
                            self.loginResponse(self.buffer[:payloadsize + 8])
                        #type =4 ---room state
                        elif typeMessage== 4 and sessionToken_1==self.sessionToken_1  and  sessionToken_2==self.sessionToken_2: 
                            print("room state")
                            self.roomState(self.buffer[:payloadsize + 8])
                        #type = 6 -- display message
                        elif typeMessage == 6 and sessionToken_1==self.sessionToken_1  and  sessionToken_2==self.sessionToken_2: 
                            print("chat message")
                            self.displayMessage(self.buffer[:payloadsize + 8])
                    #to get rid of the data proccessed
                    self.buffer = self.buffer[(payloadsize + 8):]
                    
                else:
                    break;
            else:
                break;
      
      
