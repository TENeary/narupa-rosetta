# Copyright (c) Tim Neary, University of Bristol. Github username: TENeary, contact: tn15550@bristol.ac.uk
# Licensed under the GPL. See License.txt in the project root for license information.

from typing import Dict
from json import loads as jloads

from .rosetta_communicator import *


  ################################################################
  ##########  RosettaCommand base Class implementation  ##########
  ################################################################

class RosettaCommand:
  """
  Base Rosetta command, helpful to allow for implementation of new commands
  This class should be overwritten and the ._execute method overloaded
  Execute return values should be as a dict
  """
  def __init__(self,
               client : RosettaClient,
               key : str = None):
    self._msg_key = key
    self._client = client

  @classmethod
  def execute(cls,
              client : RosettaClient,
              **kwargs):
    """
    Intended method for initialisation and calling of RosettaCommand derived classes.
    It is not intended for derived classes to alter this method

    :param client: A RosettaClient object containing a zmq socket for communication with Rosetta.
    :param kwargs: Arguments to be passed to the _execute command
    :return return value of _execute command:
    """
    if client is None:
      raise ValueError( "Rosetta Client cannot be None" )
    cmd = cls(client)
    return cmd._execute( **kwargs )

  def _execute(self, **kwargs):
    """
    When implementing another RosettaCommand derived class, this function should be overloaded.
    Additional functions can be added as well.

    :param kwargs: The key word arguments needed for the derived class to operate.
    :raises NotImplementedError: If the derived class does not implement this method. It is expected to be overloaded
    :return: Any value as described by the derived class
    """
    raise NotImplementedError( f"Use of \"{self._msg_key}\" has not been implemented yet." )

  def _send_recv_request(self,
                         msg_data : list) -> list:
    """
    Implementation of a simple send/receive request using the RosettaClient

    :param msg_data: String of message data to be sent
    :raises ResponseTimeoutError: If the RosettaClient does not receive a reply within a specified timeout.
    :raises KeyError: If the response from teh Rosetta server indicates the Key supplied is not recognised.
    :raises FormatError: If the response from the Rosetta server is an error message, but the key is correctly parsed.
    :return response: A list containing the response received from the server. The first entry will always be the return key.
    """
    self._client.send_messages( [self._msg_key] + msg_data )
    response = self._client.recv_messages()
    if not response:
      raise ResponseTimeoutError( "Rosetta Server did not respond to message request in time." )
    elif response[0] == f"REP_{self._msg_key}":
      return response
    elif response[0] == "KEY_ERROR":
      raise KeyError( f"Rosetta Server did not recognise given key:\n{self._msg_key}" )
    elif response[0] == f"ERR_{self._msg_key}":
      raise FormatError( f"Message data not formatted correctly. The error data provided was:\n{response[1]}" )

  def _var_not_none(self, var):
    """
    Assesses whether a variable is None. Raises a ValueError when it is.

    :param var: Any variable to be assessed
    :raises ValueError: IF the variable specified by "var" is none
    """
    if not var:
      raise ValueError( f"In {self.__class__.__name__}: {var} is None... Aborting command call." )

  @classmethod
  def func_signature(cls) -> str:
    annot_str = f"Arguments:\n"
    for ak, av in cls._execute.__annotations__.items():
      annot_str += f"\t{ak} - {av}\n"
    annot_str += f"Returns:\n\t{cls._execute.__annotations__['return']}"
    return annot_str


  ################################################################
  ############  Common Derived Class implementations  ############
  ################################################################

class EchoMessage(RosettaCommand):
  """
  Allows for message to be echo'd to server
  """
  def __init__(self,
               client : RosettaClient):
    super().__init__( client=client, key="ECHO" )

  def _execute(self,
               msg : str = "TEST") -> Dict[str, str]:
    response = self._send_recv_request( [msg] )
    return { "response" : response[1] }

  ################################################################

class CloseServer(RosettaCommand):
  """
  Allows for message to be echo'd to server
  """
  def __init__(self,
               client : RosettaClient):
    super().__init__( client=client, key="EXIT" )

  def _execute(self):
    self._send_recv_request( [""] )
    return

  ################################################################

class SendPose(RosettaCommand):
  """
  Sends a pose to Rosetta, no error checking is made to ensure the Pose is
  properly formatted etc. This is the users responsibility
  Rosetta will reply with the identifier it has assigned to the Pose
  """
  def __init__(self,
               client : RosettaClient):
    super().__init__( client=client, key="STORE_POSE" )

  def _execute(self,
               pose_name : str,
               pose_to_store : str) -> Dict[str, str]:
    self._var_not_none( pose_to_store )
    response = self._send_recv_request( [pose_name, pose_to_store] )
    return {"pose_name" : response[1]}

  ################################################################

class RequestPose(RosettaCommand):
  """
  Requests a pose from Rosetta.
  Rosetta will reply with a pdb given as a string
  """
  def __init__(self,
               client : RosettaClient):
    super().__init__(client=client, key="SEND_POSE")

  def _execute(self,
               pose_name : str = "pose0") -> Dict[str, str]:
    self._var_not_none(pose_name)
    pose = self._send_recv_request([pose_name])
    return {"pose_pdb" : pose[1]}

  ################################################################

class RequestPoseInfo(RosettaCommand):
  """
  Requests the full pose information from Rosetta, this includes:
    atom_elements,
    atom_coords,
    atom_bonds
  This will be returned as Dict using the above strings as keys
  """
  def __init__(self,
               client : RosettaClient):
    super().__init__(client=client, key="SEND_POSE_INFO")

  def _execute(self,
               pose_name : str = "pose0") -> Dict[str, str]:
    self._var_not_none(pose_name)
    pose_info = self._send_recv_request( [pose_name] )
    # Recieves a serialised json containing the following fields:
    #   atom_coords, atom_elements, atom_bonds
    return jloads(pose_info[1])

  ################################################################

class RequestPoseList(RosettaCommand):
  """
  Requests a list of the stored poses
  Rosetta will reply with a space delimited series of identifiers of poses
  stored in memory by the server
  """
  def __init__(self,
               client : RosettaClient):
    super().__init__( client=client, key="SEND_POSE_LIST" )

  def _execute(self) -> Dict[str, list]:
    pose_list = self._send_recv_request( [""] )
    pose_list = pose_list[1].split()
    return { "pose_list" : pose_list }

  ################################################################

class SendAndParseXml(RosettaCommand):
  """
  Sends an XML script to be parsed and executed by Rosetta.
  Rosetta will reply with "Protocol parsed successfully" if the XML script is acceptable
  """
  def __init__(self,
               client : RosettaClient):
    super().__init__( client=client, key="PARSE_AND_RUN_XML" )

  def _execute(self,
               pose_name : str,
               xml : str):
    self._var_not_none( pose_name )
    self._var_not_none( xml )
    self._send_recv_request( [pose_name, xml] )
    return

