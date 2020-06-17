# Copyright (c) Tim Neary, University of Bristol. Github username: TENeary, contact: tn15550@bristol.ac.uk
# Licensed under the GPL. See License.txt in the project root for license information.

# Narupa Server and CommandService imports
from narupa.app import NarupaFrameApplication
from narupa.command.command_service import CommandService

# Rosetta required imports
from .rosetta_communicator import RosettaClient, DEFAULT_ROSETTA_ADDRESS, DEFAULT_ROSETTA_PORT
from .command_util import ( RosettaCommand, EchoMessage, CloseServer,
                            SendPose, RequestPose, RequestPoseList,
                            SendAndParseXml )

# For iMD client controls
from narupa.trajectory.frame_server import PLAY_COMMAND_KEY, RESET_COMMAND_KEY, STEP_COMMAND_KEY, PAUSE_COMMAND_KEY
from typing import Dict

class RosettaRunner:
  """

  """
  def __init__(self,
               narupa_server_name : str = None,
               narupa_server_address : str = None,
               narupa_server_port : int = None,
               rosetta_server_address : str = DEFAULT_ROSETTA_ADDRESS,
               rosetta_server_port : int = DEFAULT_ROSETTA_PORT):

    self._app = NarupaFrameApplication.basic_server( name=narupa_server_name, address=narupa_server_address, port=narupa_server_port )
    self._frame_publisher = self._app.frame_publisher   # For convenience
    self._server = self._app.server                     # For convenience
    self._rosetta = RosettaClient( rosetta_server_address=rosetta_server_address, rosetta_server_port=rosetta_server_port )
    self._rosetta.connect()
    # self._trajectory = TODO trajectory manager, i.e. play frames reset frames etc.
    # self._pdb_converter = TODO pdb->framedata converter manager needs to keep track of proteins to see what needs to be rebuilt each frame

    self._ros_cmds = {}
    self._register_commands()


  def can_contact_rosetta(self) -> bool:
    """
    Tests whether RosettaRunner can contact Rosetta.

    :return bool: True if RosettaRunner receives a reply from the Rosetta server, else: False.
    """
    return self._rosetta.test_connection()

  def _register_commands(self):
    self._ros_cmds = { "ros/echo_message" : EchoMessage.execute,
                       "ros/close_server" : CloseServer.execute,
                       "ros/send_pose" : SendPose.execute,
                       "ros/request_pose" : RequestPose.execute,
                       "ros/request_pose_list" : RequestPoseList.execute,
                       "ros/send_and_parse_xml" : SendAndParseXml.execute }

    # Add commands specific to communicating with Rosetta
    self._server.register_command( "ros/echo_message", self.run_rosetta_command,
                                       { "ros_cmd" : "ros/echo_message", "msg" : "TEST" } )
    self._server.register_command("ros/close_server", self.run_rosetta_command,
                                       { "ros_cmd": "ros/close_server" })
    self._server.register_command( "ros/send_pose", self.run_rosetta_command,
                                       { "ros_cmd" : "ros/send_pose", "pose_to_store" : None } )
    self._server.register_command( "ros/request_pose", self.request_pose, # For speed reasons getting a pdb will avoid dict look ups.
                                       { "pose_name" : None } )
    self._server.register_command( "ros/request_pose_list", self.run_rosetta_command,
                                       { "ros_cmd" : "ros/request_pose_list" } )
    self._server.register_command( "ros/send_and_parse_xml", self.run_rosetta_command,
                                       { "ros_cmd" : "ros/send_and_parse_xml", "xml" : None } )
    self._server.register_command( "get_rosetta_args", self.get_rosetta_command_args,
                                       { "ros_cmd_name" : "ros/echo_message" } )

    # Add commands for manipulating in progress viewing with iMD VR client.
    # To do implement play back etc.
    # self._server.register_command( PLAY_COMMAND_KEY )
    # self._server.register_command( PAUSE_COMMAND_KEY )
    # self._server.register_command( RESET_COMMAND_KEY )
    # self._server.register_command( STEP_COMMAND_KEY )

  def run_rosetta_command(self,
                          ros_cmd : str = "None",
                          **kwargs ) -> Dict[str, str]:
    """
    Runs arbitary rosetta command. Adds a reference to the RosettaClient object as the argument is parsed.

    :param ros_cmd: Name of the Rosetta command to be run. Must first be registered
    raises KeyError: If ros_cmd is not recognised.
    :param kwargs: Set of key work arguements and values accepted by the RosettaCommand being called.
    :return Dict: Returns dictionary result corresponding to the called RosettaCommand object. Call get_rosetta_command_args for more details.
    """
    if ros_cmd in self._ros_cmds.keys():
      return self._ros_cmds[ros_cmd]( client=self._rosetta, **kwargs )
    else:
      raise KeyError( "Rosetta command name not recognised. Stored commands include:\n"
                      f"{self._ros_cmds}" )

  def request_pose(self,
                   pose_name : str = "None") -> Dict[str, str]:
    """
    Specialist function to avoid dictionary lookup when requesting poses as speed is critical to ensure enough poses can be requested.

    :param pose_name: Name of a pose stored in the Rosetta server. Pose names cannot contain spaces.
    :raises FormatError: If the Rosetta server returns an error message. This most likely means the name is not recognised.
    :return Dict{ pose_pdb : pdb_string }: pdb_string corresponds to the PDB of the requested pose.
    """
    return RequestPose.execute( client=self._rosetta, pose_name=pose_name )

  def register_rosetta_command(self,
                               ros_cmd_name : str,
                               ros_cmd : RosettaCommand,
                               cmd_args : dict ):
    """
    Registers a new rosetta command, ensures it maintains the correct syntax for rosetta commands.
    This enables a reference to a RosettaClient object to be added when arguments are called as they cannot be added to protobuf structs.
    Will prepend ros_cmd_name with "ROS/" if it doesn't contain the prefix already.

    :param ros_cmd_name: Name the RosettaCommand will be registered under
    :param ros_cmd: Reference to the RosettaCommand object itself.
    :param cmd_args: Dictionary of keyword argument and default values needed for the function.
    :raises ValueError: If either ros_cmd_name or ros_cmd are None
    :raises ValueError: If ros_cmd_name has already been registered
    """
    # Check Rosetta command hasn't already been registered
    if not ros_cmd_name or not ros_cmd:
      raise ValueError( "Rosetta Command name cannot be None." )
    if ros_cmd_name is in self._ros_cmds:
      raise ValueError( "Rosetta command name already exists." )
    if ros_cmd_name.split("/")[0] != "ROS":
      ros_cmd_name = "ROS/" + ros_cmd_name

    # Check protected arguments (client and key) haven't been used
    if "client" in cmd_args.keys() or "key" in cmd_args.keys():
      raise KeyError( "\"client\" and \"key\" are protected arguments. These cannot be used in user defined RosettaCommand." )

    self._ros_cmds[ros_cmd_name] = ros_cmd.execute
    self._server.register_command( f"ROS/{ros_cmd_name}", self.run_rosetta_command, cmd_args )

  def get_rosetta_command_args(self,
                               ros_cmd_name : str) -> Dict[str, object]:
    """
    Gets the keyword arguments and default value parameters used for calling the specified RosettaCommand

    :param ros_cmd_name: Name of the RosettaCommand as stored when the command was registered.
    :return Dict { kw_arg : arg_type, ..., return : return_type } : Dictionary of keyword arguments and return names and types.
    """
    if ros_cmd_name in self._ros_cmds.keys():
      return self._ros_cmds[ros_cmd_name]._execute.__annotations__
    else:
      raise KeyError( "Command not recognised" )

if __name__ == "__main__":

  import argparse
  parser = argparse.ArgumentParser( description="Command lime implementation of RosettaRunner.\n"
                                                "This script takes a pdb and corresponding xml and uses Rosetta to apply one to the other.\n"
                                                "The resulting simulation data is gathered and can then run in VR using Narupa." )

  parser.add_argument( "-p", type=argparse.FileType("r"),
                       help="Location of the pdb containing the protein to be processed." )
  parser.add_argument( "-x", type=argparse.FileType("r"),
                       help="Location of the XML file containing the RosettaScripts style XML. This XML will be used to process the pdb." )
  # TODO add ability to change default addresses and ports for narupa/rosetta
  args = parser.parse_args()