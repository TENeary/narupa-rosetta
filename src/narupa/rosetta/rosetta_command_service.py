
# Licensed under the GPL. See License.txt in the project root for license information.

from typing import Callable, Optional, Dict

from narupa.command.command_service import CommandService
import grpc
from narupa.utilities.protobuf_utilities import dict_to_struct, struct_to_dict
from narupa.protocol.command import CommandReply

from narupa.core.narupa_server import NarupaServer
from narupa.state.state_service import StateService
from .rosetta_communicator import RosettaClient
from .command_util import *


  ################################################################
  #########  RosettaCommandService Class implementation  #########
  ################################################################

class RosettaCommandService(CommandService):
  """
  RosettaCommandService service containing specific functions to communicate with Rosetta.
  Ensures that correct communication between Narupa and Rosetta is maintained.
  Also contains some functions which will be commonly used.
  """
  def __init__(self,
               rosetta_server_address : str = "localhost",
               rosetta_server_port : int = 43234):
    super().__init__()
    self.name : str = "RosettaCommands"
    self.client = RosettaClient( rosetta_server_address, rosetta_server_port )
    self.client.connect()
    self._register_simple_rosetta_commands()


  def _register_simple_rosetta_commands(self):
    #todo help text
    self.register_rosetta_command( "ROS_echo_message", EchoMessage,
                                   { "msg" : "TEST "} )
    self.register_rosetta_command( "ROS_close_server", CloseServer,
                                   {} )
    self.register_rosetta_command( "ROS_send_pose", SendPose,
                                   { "pose_to_store" : None })
    self.register_rosetta_command( "ROS_request_pose", RequestPose,
                                   { "pose_name" : None })
    self.register_rosetta_command( "ROS_request_pose_list", RequestPoseList,
                                   {} )
    self.register_rosetta_command( "ROS_send_and_parse_xml", SendAndParseXml,
                                   { "xml" : None })

  def register_rosetta_command(self,
                               rosetta_command_name : str,
                               rosetta_command_obj : RosettaCommand,
                               execute_args : dict = None):
    #todo help text
    if "client" in execute_args.keys():
      raise KeyError( "\"client\" is a protected argument and therefore cannot be used." )
    # As it is a Rosetta command and we need access to the RosettaClient we will use a prefix to discriminate
    if rosetta_command_name.split("_")[0] != "ROS":
      rosetta_command_name = "ROS/" + rosetta_command_name
    self.register_command( rosetta_command_name, rosetta_command_obj.execute, execute_args )

  def RunCommand(self, request, context) -> CommandReply:
    #TODO help text
    name = request.name
    command = self._commands.get(name)
    if command is None:
      context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
      message = f'Unknown command: {command}'
      context.set_details(message)
      return
    args = command.info.arguments
    args.update(struct_to_dict(request.arguments))

    # Add the client to the list of arguments if it is a rosetta specific command
    if name.split("/")[0] == "ROS":
      if args is None:
        args = { "client" : self.client }
      else:
        args["client"] = self.client

    results = command.callback(**args)
    if results is not None:
      try:
        result_struct = dict_to_struct(results)
      except ValueError:
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        message = f'Command ({name}) generated results that cannot be serialised: {results}'
        context.set_details(message)
        return
      return CommandReply(result=result_struct)
    else:
      return CommandReply()


  ################################################################
  #############  RosettaServer Class implementation  #############
  ################################################################

class RosettaServer(NarupaServer):
  """
  Usability class containing modified NarupaServer.
  Functions indentically but now includes RosettaCommandService derived class
  """
  _command_service: RosettaCommandService
  _state_service: StateService

  def __init__(self,
               address : str,
               port : int,
               rosetta_address : str = "localhost",
               rosetta_port : int = 43234):
    self.rosetta_address = rosetta_address
    self.rosetta_port = rosetta_port
    super().__init__( address=address, port=port )


  def _setup_command_service(self):
    """
    Overloaded _setup_command_service method to initialise a RosettaCommandService
    instead of the default. Will allow for easier creation of new RosettaCommands
    """
    self._command_service = RosettaCommandService( rosetta_server_address=self.rosetta_address,
                                                   rosetta_server_port=self.rosetta_port )
    self.add_service( self._command_service )

  def register_rosetta_command(self, name: str,
                               rosetta_command_obj: RosettaCommand,
                               execute_args: dict = None):
    """
    Registers a rosetta command with the :class:`RosettaCommandService` running on this server.

    :param name: Name of the command to register
    :param rosetta_command_obj: Reference to a given RosettaCommand object.
    :param execute_args: A description of the arguments of the execute function and their default values.

    :raises ValueError: Raised when a command with the same name already exists.
    """
    self._command_service.register_rosetta_command(name, rosetta_command_obj, execute_args)
