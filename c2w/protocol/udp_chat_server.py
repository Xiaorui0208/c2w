# -*- coding: utf-8 -*-
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from c2w.main.lossy_transport import LossyTransport
from c2w.main.constants import ROOM_IDS
import logging
import struct
import re
import random

logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.udp_chat_server_protocol')


class c2wUdpChatServerProtocol(DatagramProtocol):

    def __init__(self, serverProxy, lossPr):
        """
        :param serverProxy: The serverProxy, which the protocol must use
            to interact with the user and movie store (i.e., the list of users
            and movies) in the server.
        :param lossPr: The packet loss probability for outgoing packets.  Do
            not modify this value!

        Class implementing the UDP version of the client protocol.

        .. note::
            You must write the implementation of this class.

        Each instance must have at least the following attribute:

        .. attribute:: serverProxy

            The serverProxy, which the protocol must use
            to interact with the user and movie store in the server.

        .. attribute:: lossPr

            The packet loss probability for outgoing packets.  Do
            not modify this value!  (It is used by startProtocol.)

        .. note::
            You must add attributes and methods to this class in order
            to have a working and complete implementation of the c2w
            protocol.
        """
        #: The serverProxy, which the protocol must use
        #: to interact with the server (to access the movie list and to 
        #: access and modify the user list).
        self.serverProxy = serverProxy
        self.lossPr = lossPr
        #{host_port: sequenceNumbersent,type} the server to the client
        self.usersequenceNumber = {}
       
        #{host_port : sesion}
        self.usersession = {}
        #{host_port : count}
        self.usercount ={}
#        #{useraddress, user name}
#        self.addresstouser={}
      
        #{host_port : flag} to store the sequence of message received
        self.userflag={}
        #function callLater
        self.send= {}
        self.loginpacket={}
        #to determine if the login is successful
        self.response={}
        # 1- leave the systeme 0- non
        self.leave={}
#        #{host_port : sequence received without ack}
#        self.receive={}
        #to store the room id
        self.roomID = [1]
        for movie in self.serverProxy.getMovieList():
            self.roomID.append(movie.movieId)
       
        
        
        
        

    def startProtocol(self):
        """
        DO NOT MODIFY THE FIRST TWO LINES OF THIS METHOD!!

        If in doubt, do not add anything to this method.  Just ignore it.
        It is used to randomly drop outgoing packets if the -l
        command line option is used.
        """
        self.transport = LossyTransport(self.transport, self.lossPr)
        DatagramProtocol.transport = self.transport
   
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

    def ackResponse(self, datagram, host_port):
        """
         When receiving a package from the server, respond to an ack to confirm the reception
         Here we need to unpack the received datagram, extract the sessionToken, Sequencenumber
         the payload here is a 0
        """

        version = 1
        # the type of the ACK message is 0
        typeMessage = 0
        # Then we use the method called struct to finish the process of packing package and of unpacking package.
        # Specifilly, we use struct.pack and struct.unpack.
        # we have to divide the session(3 bits) into 2 parts of which the first part counts 2 bits,
        sessionToken_1, = struct.unpack('>H', datagram[1:3])
        # and the second part counts 1 bit.
        sessionToken_2, = struct.unpack('>B', datagram[3:4])
        sequenceNumber, = struct.unpack('>H', datagram[4:6])
        # the payloadSize is null due to the specification
        payloadSize = 0
        buf = struct.pack('>BHBHH' , version*16+typeMessage, sessionToken_1, sessionToken_2,
                          sequenceNumber, payloadSize)
        print('********Send ACK**************')
        print("ack :" ,buf)
       
        self.transport.write(buf,(host_port))

    def sendChatMessageONE(self, datagram, host_port):
        """
        The server now receives the message from the client. The next server will forward this 
        message to all users in the same room. So we will now consider extracting the user's ID 
        and then looking up his current room by ID.
        Traverse all users in this room and send this message to each user.
        """

        # By checking the specification, we know that the userID's position inside the package is [8,10]
        # and messageLength is [10,12]

        userID,= struct.unpack('>H', datagram[8:10])
        
        messageLength,= struct.unpack('>H', datagram[10:12])
        message, = struct.unpack('>%ds' %messageLength, datagram[12:])
        # Here we call the method which is implented by our prof,
        # it calls getUserList() who belongs to serverProxy.
        alluserList = self.serverProxy.getUserList()

        # Then we find all the users in the userList, we expect to find the userRoom by using the userName.
        for user in alluserList :
            if user.userId == userID :
                userRoom = user.userChatRoom
                userName = user.userName
        for user in alluserList :
            if user.userChatRoom == userRoom  and user.userName != userName:
                version = 1
                typeMessage = 6
                sessionToken_1 = self.usersession[user.userAddress][0]
                sessionToken_2 = self.usersession[user.userAddress][1]

                # the userID(2 bits) and messageLength(2 bits), so here we add 4 bits with the messageLength.
                payloadSize = 4+messageLength
                
                sequenceNumber = self.usersequenceNumber[user.userAddress][0]
                self.usersequenceNumber[user.userAddress][1] = 6
                # Stop sending more than three times
                buf = struct.pack('>BHBHHHH%ds' %messageLength, version*16+typeMessage, sessionToken_1,sessionToken_2,
                                              sequenceNumber, payloadSize, userID,messageLength, message)

                # the limit times for transferring  messages is 3 times.
                # if the we reach the limit, we suppose that this user is out of line.(we call removeUser())
                if self.usercount[user.userAddress][0] ==3:
                    print("Connection Lost")
                    if self.leave[user.userAddress]==0 :
                        self.serverProxy.removeUser(user.userName)
                        self.leave[user.userAddress]=1
                        for user in self.serverProxy.getUserList():
                            if user.userChatRoom == ROOM_IDS.MAIN_ROOM or user.userChatRoom== userRoom :
                                self.roomState(user.userAddress)
                    
                    
                else :
                    #send the packet
                    print('*********Send Message**************')
                    print("message :", buf)  
#                    print('***********************')
                    self.transport.write(buf,user.userAddress)
                
                    # Here we consider retransmitting this message after timing 1s without receiving ack response. 
                    # Stop sending more than three times
                    # To realize this fonction, we call a method in reactor called callLater()
                    self.usercount[user.userAddress][0] +=1
                    if self.usercount[user.userAddress][0] <= 3:
                        self.send[user.userAddress]= [reactor.callLater(1, self.sendChatMessageONE, datagram, host_port)]
                
                




    def loginResponse(self, datagram, host_port):
        """
        when receiving the login request sent by the client, the server sent the login response
        """
        version = 1
        typeMessage = 2
        userLength, = struct.unpack('>H', datagram[10:12])
        userName, = struct.unpack('>%ds' %userLength, datagram[12:12+userLength])
        userName = userName.decode()
        print(userName)
        
        
#        #to store the address of the client
#        self.addresstouser[host_port]=[userName]
     
       
            
        # if login successful：
        if self.usercount[host_port][0] !=0 :
            buf = self.loginpacket[host_port][0]
        else :
             # Here we determine the loginRequest, we use responseCode (1 byte) to determine
            # The first case is Invalid User, which means that the user name has illegal characters. 
            #Here we use regular expressions. Need to introduce re library.
            try:
                # we use the concept Regular Expression to solve this part 
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
            
                userIdentifier = self.serverProxy.addUser(userName, ROOM_IDS.MAIN_ROOM, None, host_port)
             
                sequenceNumber = 0
                #Randomly generated 24bits binaire
                sessionToken = random.getrandbits(24)
                print("sessionToken :" , sessionToken)
                sessionToken_1 = sessionToken // 256
                sessionToken_2 = sessionToken % 256

                # Here we get a response code, so here we add 5 instead of 4
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
            
            self.usersession[host_port] = [sessionToken_1,sessionToken_2]
            self.usersequenceNumber[host_port] = [0,2]
            self.loginpacket[host_port]=[buf]
            self.response[host_port]=[responseCode]
        
        
        # Stop sending more than three times
        if self.usercount[host_port][0] ==3:
             print("Connection Lost")
             if self.leave[host_port]==0 and self.response[host_port][0]== 0 :
                 self.serverProxy.removeUser(userName)
                 self.leave[host_port]=1
                 for user in self.serverProxy.getUserList():
                     if user.userChatRoom == ROOM_IDS.MAIN_ROOM :
                         self.roomState(user.userAddress)
          
                 
            
        else:
            print('********Send LoginResponse***************')
            print("loginresponse :" , buf)
#            print('***********************')
            self.transport.write(buf, (host_port))
            
            # Here we consider retransmitting this message after timing 1s without receiving ack response. 
            # Stop sending more than three times
            self.usercount[host_port][0] +=1
            if self.usercount[host_port][0] <= 3:
                self.send[host_port]= [reactor.callLater(1, self.loginResponse, datagram, host_port)]
      
        
        
            
    
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

    
 
    def roomState(self, host_port):
        """
        to send the room state
        """
       

        version = 1
        typeMessage = 4
       
        #to get the room of the client
        user = self.serverProxy.getUserByAddress(host_port)
        sessionToken_1 = self.usersession[host_port][0]
        sessionToken_2 = self.usersession[host_port][1]
        room = user.userChatRoom
        
        sequenceNumber = self.usersequenceNumber[host_port][0]
        self.usersequenceNumber[host_port][1] = 4
      
        
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
        if self.usercount[host_port][0] ==3:
             print("Connection Lost")
             if self.leave[host_port]==0 :
                 self.serverProxy.removeUser(user.userName)
                 self.leave[host_port]=1
                 for user in self.serverProxy.getUserList():
                     if (user.userChatRoom == ROOM_IDS.MAIN_ROOM or user.userChatRoom == room):
                         self.roomState(user.userAddress)
        
        else:
            #send the packet
            print('********Send RoomState***************')
            print("roomState :", buf)
#            print('***********************')
            self.transport.write(buf, (host_port))
            # Here we consider retransmitting this message after timing 1s without receiving ack response. 
            # Stop sending more than three times
            self.usercount[host_port][0] +=1
            if self.usercount[host_port][0] <= 3:
                self.send[host_port] = [reactor.callLater(1, self.roomState, host_port)]

    
    def hello(self, sequenceNumber,host_port):
        """
        to check the client connection is still alive
        """ 
        
#        print("***************************************")
#        print("now number",self.userflag[userName][0])
#        print("past number",sequenceNumber)
        
       
        #the sequence number received no change
        if sequenceNumber == self.userflag[host_port][0]:
      
            #more than three consecutive HEL without receiving an ack ,remove the user
            if self.usercount[host_port][0] ==3:
                print("Connection Lost")
                if self.leave[host_port]==0 :
                    user = self.serverProxy.getUserByAddress(host_port)
                    room = user.userChatRoom
                    self.serverProxy.removeUser(user.userName)
                    self.leave[host_port]=1
                    for user in self.serverProxy.getUserList():
                        if (user.userChatRoom == ROOM_IDS.MAIN_ROOM or user.userChatRoom == room):
                            self.roomState(user.userAddress)
             
            else:
            
                #send the packet
                version = 1
                typeMessage = 8
                sessionToken_1 = self.usersession[host_port][0]
                sessionToken_2 = self.usersession[host_port][1]
               
                sequence = self.usersequenceNumber[host_port][0]
                self.usersequenceNumber[host_port][1] = 8
                payloadSize = 0
                buf = struct.pack('>BHBHH' , version*16+typeMessage, sessionToken_1, sessionToken_2,
                                  sequence, payloadSize)
                print('********Send Hello***************')           
                print("hello :" ,buf)
#               print('***********************')
                self.transport.write(buf,(host_port))
                # Here we consider retransmitting this message after timing 1s without receiving ack response. 
                # Stop sending more than three times
                self.usercount[host_port][0] +=1
                if self.usercount[host_port][0] <= 3:
                    self.send[host_port] = [reactor.callLater(1, self.hello, sequenceNumber,host_port)]
        
        
        
    def datagramReceived(self, datagram, host_port):
        """
        :param string datagram: the payload of the UDP packet.
        :param host_port: a touple containing the source IP address and port.
        
        Twisted calls this method when the server has received a UDP
        packet.  You cannot change the signature of this method.
        """
        
        
#        print(host_port)
        # Here we extract the first byte of the received data, including 
        #the version and  type, where we tend to take out the type.
        buf,= struct.unpack('>B', datagram[0:1])
        typeMessage = buf % 16
        
        (sessionToken_1, sessionToken_2, sequenceNumber) = struct.unpack('>HBH', datagram[1:6])
        self.userflag[host_port]=[sequenceNumber]
        print('********Datagram Received**************')
        print("type :" ,typeMessage)
        print("sequence number",sequenceNumber)
        print("datagramReceived :" , datagram)
#        print('***********************')
        # The first step we determine the type of information , if the type is ack, we need to
        # determine if the ack is received correctly, if the message is correctly，we cancel resend the packet
        if typeMessage == 0 :
         
           
            
            if sequenceNumber == self.usersequenceNumber[host_port][0] and sessionToken_1==self.usersession[host_port][0]  and  sessionToken_2==self.usersession[host_port][1] :
                 print("*******ACK Received******")
                 self.send[host_port][0].cancel()
                 self.usercount[host_port]=[0]
                 self.usersequenceNumber[host_port][0] = (self.usersequenceNumber[host_port][0]+1) % 65535
                 if sequenceNumber == 0 and self.usersequenceNumber[host_port][1] == 2 and self.response[host_port][0] == 0:
                    for user in self.serverProxy.getUserList() :
                        if user.userChatRoom ==ROOM_IDS.MAIN_ROOM:
                            self.roomState(user.userAddress)

         #if the type is not an ack, we should respond the server to confirm the reception of the packet                
        else :
            self.ackResponse(datagram,host_port)
            
            # typeMessage = 1 means request login;we call the function loginResponse
            if typeMessage == 1 :
                
                print("login request")
                #the first sequncenumber is 0
                
                self.leave[host_port]=0
                self.usercount[host_port]=[0]
                self.loginResponse(datagram, host_port)
                
                  
            #typeMessage =5 :request join room ;
            elif typeMessage == 5 and sessionToken_1==self.usersession[host_port][0] and sessionToken_2==self.usersession[host_port][1] :
                
                print("join room")
                usernow = self.serverProxy.getUserByAddress(host_port)
                roomId, = struct.unpack('>H', datagram[8 : 10])
                # room id is wrong
                if roomId not in self.roomID:
                    self.roomState(host_port)
                    
                    
                else:   
                    #the client joins to main room
                    if roomId == 1 :
                        self.serverProxy.stopStreamingMovie(usernow.userChatRoom)
                        userPastroom = usernow.userChatRoom
                        self.serverProxy.updateUserChatroom(usernow.userName, ROOM_IDS.MAIN_ROOM)
                        for user in self.serverProxy.getUserList():
                            if (user.userChatRoom == ROOM_IDS.MAIN_ROOM or user.userChatRoom == userPastroom):
                                self.roomState(user.userAddress)
                      
                    #the client joins to movie room
                    else :
                        for movie in self.serverProxy.getMovieList() :
                            if movie.movieId == roomId :
                                self.serverProxy.updateUserChatroom(usernow.userName, movie.movieTitle)
                                self.serverProxy.startStreamingMovie(movie.movieTitle)
                                for user in self.serverProxy.getUserList():
                                    if (user.userChatRoom == movie.movieTitle or user.userChatRoom == ROOM_IDS.MAIN_ROOM): 
                                        self.roomState(user.userAddress)
                                     
            #typeMessage =7 : leave system
            elif typeMessage == 7 and sessionToken_1==self.usersession[host_port][0] and sessionToken_2==self.usersession[host_port][1]:
                
                print("leave system")
                
                usernow = self.serverProxy.getUserByAddress(host_port)
                self.serverProxy.removeUser(usernow.userName)
                self.leave[host_port] = 1
                for user in self.serverProxy.getUserList():
                    if user.userChatRoom ==ROOM_IDS.MAIN_ROOM:
                        self.roomState(user.userAddress)
           #typeMessage =7 : send message
            elif typeMessage == 6 and sessionToken_1==self.usersession[host_port][0]  and  sessionToken_2==self.usersession[host_port][1]:
                
                print("chat message")
                self.sendChatMessageONE(datagram, host_port)
#            #sequence number received add 1
#            self.receive[host_port] = (self.receive[host_port]+1) % 65535
        if self.leave[host_port]==0 and self.response[host_port][0] == 0 :  
            #call the function hello , if no message receiving during 10s
            reactor.callLater(10,self.hello, sequenceNumber,host_port)
 
       
                             
                    
                    
                
            
            
                    

        
        


