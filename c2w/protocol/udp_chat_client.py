# -*- coding: utf-8 -*-
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from c2w.main.lossy_transport import LossyTransport
from c2w.main.constants import ROOM_IDS
import logging
import struct

logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.udp_chat_client_protocol')


class c2wUdpChatClientProtocol(DatagramProtocol):

    def __init__(self, serverAddress, serverPort, clientProxy, lossPr):
        """
        :param serverAddress: The IP address (or the name) of the c2w server,
            given by the user.
        :param serverPort: The port number used by the c2w server,
            given by the user.
        :param clientProxy: The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.

        Class implementing the UDP version of the client protocol.

        .. note::
            You must write the implementation of this class.

        Each instance must have at least the following attributes:

        .. attribute:: serverAddress

            The IP address of the c2w server.

        .. attribute:: serverPort

            The port number of the c2w server.

        .. attribute:: clientProxy

            The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.

        .. attribute:: lossPr

            The packet loss probability for outgoing packets.  Do
            not modify this value!  (It is used by startProtocol.)

        .. note::
            You must add attributes and methods to this class in order
            to have a working and complete implementation of the c2w
            protocol.
        """

        #: The IP address of the c2w server.
        self.serverAddress = serverAddress
        #: The port number of the c2w server.
        self.serverPort = serverPort
        #: The clientProxy, which the protocol must use
        #: to interact with the Graphical User Interface.
        self.clientProxy = clientProxy
        self.lossPr = lossPr
        #: the serial number of the packet send by the client
        self.sequenceNumber = 0
        # : the instance of a client-server connection
        self.sessionToken_1 = 0
        self.sessionToken_2 = 0
        #: the name of  the client
        self.userName = ''
        #: the identifier of the client
        self.userIdentifier = 0
        #:the state of the client 0 - login in to the server; 1 - enter the main room
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
        #function callLater
        self.send= None
     
      
 
       
       
        
    
    def startProtocol(self):
        """
        DO NOT MODIFY THE FIRST TWO LINES OF THIS METHOD!!

        If in doubt, do not add anything to this method.  Just ignore it.
        It is used to randomly drop outgoing packets if the -l
        command line option is used.
        """
        self.transport = LossyTransport(self.transport, self.lossPr)
        DatagramProtocol.transport = self.transport
    
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

    
    def ackResponse(self, datagram):
        """
         When receiving a package from the server, respond to an ack to confirm the reception
         Here we need to unpack the received datagram, extract the sessionToken, Sequencenumber
         the payload here is a 0
        """
        version = 1
        typeMessage = 0
        sessionToken_1, = struct.unpack('>H', datagram[1:3])
        sessionToken_2, = struct.unpack('>B', datagram[3:4])
        sequenceNumber, = struct.unpack('>H', datagram[4:6])
        payloadSize = 0
        buf = struct.pack('>BHBHH' , version*16+typeMessage, sessionToken_1, sessionToken_2,
                          sequenceNumber, payloadSize)
        print('*********Send ACK**************')
        print("ack :", buf)
        
        self.transport.write(buf,(self.serverAddress,self.serverPort))


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
        
        self.transport.write(buf, (self.serverAddress,self.serverPort))
        #Store the serial number and type of the sent message
        self.sequencetotype[sequenceNumber]=[typeMessage]
        
        # Here we consider retransmitting this message after timing 1s without receiving ack response. 

        self.callCount += 1
        if self.callCount <= 3 :
            #function callLater
            self.send = reactor.callLater(1, self.sendLoginRequestOIE, userName)
     
        
#    def requestRoomState(self) :
#       #向服务器发送房间状态的请求
#        version = 1
#        typeMessage = 3
#        sequenceNumber = self.generateSequenceNumber()
#        payloadSize = 0
#        buf = struct.pack('>BHBHH' , version*16+typeMessage, self.sessionToken_1, self.sessionToken_2,
#                         sequenceNumber, payloadSize)
#        print("requestRoomSteat:" , buf)
#        self.transport.write(buf,(self.serverAddress,self.serverPort))
#    
    def unpackMovieroomdata(self,datagram):
        """
        unpack the data of the movie room
        """
        # to store the user data
        userList = []
        # to unpack the data in the movie room
        (roomIdentifier,roomNameLength) = struct.unpack('>HH', datagram[8:12])
        roomName, = struct.unpack('>%ds' %roomNameLength, datagram[12:12+roomNameLength])
        roomName =  roomName.decode()
        offset = 12+roomNameLength
        (movieIP,moviePort,userNumber) = struct.unpack('>IHH', datagram[offset:offset +8])
        movieIP = self.dec2addr(movieIP)
        offset +=8
        #circuler in order to unpack the data of the user
        if userNumber != 0:
                for i in range(userNumber) :
                    (userIdentifier,userNameLength) = struct.unpack('>HH', datagram[offset:offset +4])
                    offset += 4
                    userName ,= struct.unpack('>%ds' %userNameLength, datagram[offset:offset +userNameLength])
                    userName = userName.decode()
                    #to store the identifier and name of other client
                    self.idUser[userIdentifier]=[userName]
                    offset += userNameLength
                    # to add the user to userList
                    userList.append((userName, roomName))
                    
        return userList
        
        
     
    def unpackMainroomdata(self, datagram): 
        """
        unpack the data of the main room
        """
        
        # to store the user data
        userList = []
        #to store the movie data
        movieList=[]
        (roomIdentifier,roomNameLength) = struct.unpack('>HH', datagram[8:12])
        #the number of user in the main room
        offset = 18 + roomNameLength
        userNumber, = struct.unpack('>H', datagram[offset:offset +2])
        offset += 2
        #Recycling to unpacke the user data of the main room
        for i in range(userNumber) :
            (userIdentifier,userNameLength) = struct.unpack('>HH', datagram[offset:offset +4])
            offset += 4
            userName ,= struct.unpack('>%ds' %userNameLength, datagram[offset:offset +userNameLength])
            userName = userName.decode()
            #to store the identifier and name of other client
            self.idUser[userIdentifier]=[userName]
            offset += userNameLength
            userList.append((userName, ROOM_IDS.MAIN_ROOM))
        #unpack the number of movie room
        movieRoomNumber, = struct.unpack('>H', datagram[offset:offset +2])
        offset += 2
        #Recycling to unpacke the  data of the movie room
        for i in range(movieRoomNumber) :
            (movieId,movieNameLength)= struct.unpack('>HH', datagram[offset:offset +4])
            offset += 4
            movieName, = struct.unpack('>%ds' %movieNameLength, datagram[offset:offset +movieNameLength])
            movieName = movieName.decode()
            offset += movieNameLength
            (movieIP,moviePort,userNumber) = struct.unpack('>IHH', datagram[offset:offset +8])
            movieIP = self.dec2addr(movieIP)
            offset +=8
            # to add roomname and roomid to the dictionary
            self.roomId[movieName] = [movieId]
            # to add the movie data to movieList
            movieList.append((movieName, movieIP, moviePort))
            #Recycling to unpacke the  user data in the movie room
            if userNumber == 0:
                offset += 2
            else :
                for i in range(userNumber) :
                    (userIdentifier,userNameLength) = struct.unpack('>HH', datagram[offset:offset +4])
                    offset += 4
                    userName ,= struct.unpack('>%ds' %userNameLength, datagram[offset:offset +userNameLength])
                    userName = userName.decode()
                    #to store the identifier and name of other client
                    self.idUser[userIdentifier]=[userName]
                    offset += userNameLength
                    userList.append((userName,movieName))
                offset += 2
        return userList,movieList
    

   
        
        
        

    def sendChatMessageOIE(self, message):
        """
        :param message: The text of the chat message.
        :type message: string

        Called by the client proxy  when the user has decided to send
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
        
        self.transport.write(buf, (self.serverAddress,self.serverPort))
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
        
        self.transport.write(buf,(self.serverAddress,self.serverPort))
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
        
        self.transport.write(buf,(self.serverAddress,self.serverPort))
        #Store the serial number and type of the sent message
        self.sequencetotype[sequenceNumber]=[typeMessage]
        
        # Here we consider retransmitting this message after timing 1s without receiving ack response. 
      
        self.callCount += 1
        if self.callCount <=3 :
             self.send = reactor.callLater(1, self.sendLeaveSystemRequestOIE)
        

    


    def datagramReceived(self, datagram, host_port):
        """
        :param string datagram: the payload of the UDP packet.
        :param host_port: a touple containing the source IP address and port.

        Called **by Twisted** when the client has received a UDP
        packet.
        """
        
        # Here we extract the first byte of the received data, including 
        #the version and  type, where we tend to take out the type.
        buf,= struct.unpack('>B', datagram[0:1])
        typeMessage = buf % 16
        
        (sessionToken_1, sessionToken_2, sequenceNumber) = struct.unpack('>HBH', datagram[1:6])
        print('********Datagram Received***************')
        print("type :" ,typeMessage)
        print("sequence number",sequenceNumber)
        print("datagramReceived :" , datagram)
        
        # The first step we determine the type of information , if the type is ack, we need to
        # determine if the ack is received correctly, if the message is correctly，we cancel resend the packet
        if typeMessage == 0:
            
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
                    
        #if the type is not an ack, we should respond the server to confirm the reception of the packet           
#        elif typeMessage != 0 and sequenceNumber == self.receive :
#            self.receive = (self.receive + 1)%65535
        else:
            self.ackResponse(datagram)
            # typeMessage = 2 means the loginResponse.
            if typeMessage == 2:
                print("login response")
                #take out  the responseCode and determine if it is a successful login
                (responseCode,userIdentifier,userNameLength)= struct.unpack('>BHH',datagram[8:13])
                userName, = struct.unpack('>%ds' %userNameLength, datagram[13:13+userNameLength])
                userName = userName.decode()
                        
                #responseCode = 0, login successful
                if responseCode == 0:
                    
                    #to store the session token assigned by the server
                    (self.sessionToken_1, self.sessionToken_2)= struct.unpack('>HB', datagram[1:4])
                    self.userName = userName
                    self.userIdentifier = userIdentifier
                #otherwise the login is refused
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
                   
                    
            # type=6, the client receives the chatMessage by other client
            if typeMessage == 6 and sessionToken_1==self.sessionToken_1  and  sessionToken_2==self.sessionToken_2 :
                print("chat message")
                (userId, messageLength) = struct.unpack('>HH', datagram[8:12])
                message, = struct.unpack('>%ds' %messageLength, datagram[12:])
                self.clientProxy.chatMessageReceivedONE(self.idUser[userId][0],message.decode())
                        
        
            # type=4, the room state
            if typeMessage == 4 and sessionToken_1==self.sessionToken_1  and  sessionToken_2==self.sessionToken_2:
                print("room state")
                (roomIdentifier,roomNameLength) = struct.unpack('>HH', datagram[8:12])
                roomName, = struct.unpack('>%ds' %roomNameLength, datagram[12:12+roomNameLength])
                roomName = roomName.decode()
                
                #the room is Main ROOM
                if roomName == "Main Room" :
                    self.roomId[ROOM_IDS.MAIN_ROOM] = [roomIdentifier]
                    userList,movieList = self.unpackMainroomdata(datagram)
                    #if login successful,initial the room
                    if self.userState == 0 :
                        self.clientProxy.initCompleteONE(userList, movieList)
                        self.userState = 1
                    #update the user list
                    else:
                        self.clientProxy.setUserListONE(userList)
                #the room is movie room,update the user list
                else:
                    userList = self.unpackMovieroomdata(datagram)
                    self.clientProxy.setUserListONE(userList)
                                
                            
                    
                    
                    
                    
                
                
                
        
