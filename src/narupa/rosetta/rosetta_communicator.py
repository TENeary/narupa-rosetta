# Copyright (c) Tim Neary, University of Bristol. Github username: TENeary, contact: tn15550@bristol.ac.uk
# Licensed under the GPL. See License.txt in the project root for license information.

import zmq

DEFAULT_ROSETTA_ADDRESS = "localhost"
DEFAULT_ROSETTA_PORT = 43234

class ResponseTimeoutError(Exception):
  pass

class FormatError(Exception):
  pass


class RosettaClient:

  def __init__(self,
               rosetta_server_address : str = DEFAULT_ROSETTA_ADDRESS,
               rosetta_server_port : int = DEFAULT_ROSETTA_PORT):
    """
    Initialise RosettaClient class. Also initialised underlying zmq objects for communication

    :param rosetta_server_address:
    :param rosetta_server_port:
    """
    self._ros_server_address = rosetta_server_address
    self._ros_server_port = rosetta_server_port
    self._id = "RosettaClient|{}|{}".format(rosetta_server_address, rosetta_server_port)
    # ZeroMQ Context and Socket objects for communication with Rosetta
    self._context = zmq.Context()
    self._socket = self._context.socket(zmq.REQ)
    self._socket.identity = b"NarupaClient"
    self._socket.setsockopt(zmq.RCVTIMEO, 10000) # Wait a maximum of 10 seconds when receiving messages
    self._is_connected = False


  def connect(self) -> None:
    """
    Connects to rosetta_interactive server using:
      _ros_server_address and _ros_server_address
    """
    print(f"Connecting to Rosetta server at: tcp://{self._ros_server_address}:{self._ros_server_port}")
    self._socket.connect(f"tcp://{self._ros_server_address}:{self._ros_server_port}")
    self._is_connected = True


  def test_connection(self) -> bool:
    """
    Sends a simple echo requests to the server and waits for a response

    :return: :class: 'bool', Whether the server can be reached.
    """
    if self._is_connected:
      self.send_messages(["ECHO", "test message"])
      try:
        self.recv_messages()
        return True
      except zmq.Again:
        return False
    else: # Socket not connected to server
      self.connect()
      return self.test_connection()


  def send_messages(self,
                    message_data : list = []) -> None:
    """
    Sends a list of message data to Rosetta. Message data should be in the form:
    [MSG_KEY, MSG_DATA, ... MSG_DATA]

    :param message_data: List of message data including the message key.

    :raises TypeError: All elements of message_data object must be strings or convertible to strings
    """
    for ii, msg in enumerate(message_data, 1):
      if type(msg) != str:
        try:
          msg = str(msg)
        except:
          raise TypeError(f"{msg}\n Not convertible to string. All elements must either be or convertible to string.")
      if ii < len(message_data):
        self._socket.send(msg.encode("utf-8"), flags=zmq.SNDMORE)
      else: # if last message
        self._socket.send(msg.encode("utf-8"))


  def send_messages_sl(self,
                       message_key : str = "",
                       message_data : list = []) -> None:
    """
    Usability function splitting message key and data to separate paramaters

    :param message_key: Message key to be sent to Rosetta
    :param message_data: Message data to be sent to Rosetta
    """
    full_message = [message_key]
    full_message.extend(message_data)
    self.send_messages(full_message)


  def send_messages_ss(self,
                       message_key : str = "",
                       message_data : str = "") -> None:
    """
    Usability function where both the message key and data are single strings.

    :param message_key: Message key to be sent to Rosetta
    :param message_data: Message data to be sent to Rosetta
    """
    full_message = [message_key, message_data]
    self.send_messages(full_message)


  def recv_messages(self) -> list:
    """
    Function to receive messages from Rosetta. The first entry in the list will always be the return key sent from Rosetta.

    :return all_msgs: List containing the message key and message data. The return key will always be the first entry in the list.
    """
    all_msgs = [self._socket.recv().decode("utf-8")]
    while self._socket.getsockopt(zmq.RCVMORE):
      all_msgs.append(self._socket.recv().decode("utf-8"))
    return all_msgs

  def close(self) -> None:
    self._socket.close()
    self._context.term()