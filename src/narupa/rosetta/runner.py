# Copyright (c) Tim Neary, University of Bristol. Github username: TENeary, contact: tn15550@bristol.ac.uk
# Licensed under the GPL. See License.txt in the project root for license information.

# Narupa Server and CommandService imports
from narupa.app import NarupaImdApplication
from narupa.app import NarupaImdClient
from narupa.state.state_service import DictionaryChange

# Rosetta required imports
from .rosetta_communicator import RosettaClient, DEFAULT_ROSETTA_ADDRESS, DEFAULT_ROSETTA_PORT, FormatError
from .command_util import ( RosettaCommand, EchoMessage, CloseServer,
                            SendPose, RequestPose, RequestPoseList,
                            SendAndParseXml )
from .trajectory import RosettaTrajectoryManager
from .xml_builder import RosettaScriptsBuilder
from time import sleep
from .pdb_util import convert_pdb_string_to_framedata

# For iMD client controls
from narupa.trajectory.frame_server import PLAY_COMMAND_KEY, RESET_COMMAND_KEY, STEP_COMMAND_KEY, PAUSE_COMMAND_KEY
from typing import Dict

# Other imports
from concurrent.futures import ThreadPoolExecutor
from threading import RLock

class RosettaRunner:
  """

  """
  def __init__(self,
               narupa_server_name : str = None,
               narupa_server_address : str = None,
               narupa_server_port : int = None,
               rosetta_server_address : str = DEFAULT_ROSETTA_ADDRESS,
               rosetta_server_port : int = DEFAULT_ROSETTA_PORT):

    self._app = NarupaImdApplication.basic_server( name=narupa_server_name, address=narupa_server_address, port=narupa_server_port )
    self._frame_publisher = self._app.frame_publisher   # For convenience
    self._server = self._app.server                     # For convenience
    # self._renderer = NarupaImdClient.connect_to_single_server( address=self._server.address, port=self._server.port )
    self._renderer = NarupaImdClient.autoconnect()
    self._rosetta = RosettaClient( rosetta_server_address=rosetta_server_address, rosetta_server_port=rosetta_server_port )
    self._rosetta.connect()
    self._trajectory = RosettaTrajectoryManager( frame_publisher=self._frame_publisher )
    self._xml_builder = RosettaScriptsBuilder( renderer=self._renderer )
    self._server._state_service.state_dictionary.content_updated.add_callback( self._xml_builder.new_residues )
    # self._app.imd._interaction_updated_callback = self._xml_builder.new_residues
    # self._pdb_converter = TODO pdb->framedata converter manager needs to keep track of proteins to see what needs to be rebuilt each frame

    self._ros_cmds = {}
    self._register_commands()

    # For concurrent playback and control
    self._lock = RLock()
    self._threads = ThreadPoolExecutor( max_workers=1 )
    self._script_in_progress = False


  def can_contact_rosetta(self) -> bool:
    """
    Tests whether RosettaRunner can contact Rosetta.

    :return bool: True if RosettaRunner receives a reply from the Rosetta server, else: False.
    """
    return self._rosetta.test_connection()

  def _register_commands(self):
    self._ros_cmds = { "ros/echo_message" : EchoMessage,
                       "ros/close_server" : CloseServer,
                       "ros/send_pose" : SendPose,
                       "ros/request_pose" : RequestPose,
                       "ros/request_pose_list" : RequestPoseList,
                       "ros/send_and_parse_xml" : SendAndParseXml }

    # Add commands specific to communicating with Rosetta
    self._server.register_command( "ros/echo_message", self.run_rosetta_command,
                                       { "ros_cmd" : "ros/echo_message", "msg" : "TEST" } )
    self._server.register_command( "ros/close_server", self.run_rosetta_command,
                                       { "ros_cmd": "ros/close_server" } )
    self._server.register_command( "ros/send_pose", self.run_rosetta_command,
                                       { "ros_cmd" : "ros/send_pose", "pose_name" : None, "pose_to_store" : None } )
    self._server.register_command( "ros/request_pose", self.request_pose, # For speed reasons getting a pdb will avoid dict look ups.
                                       { "pose_name" : None } )
    self._server.register_command( "ros/request_pose_list", self.run_rosetta_command,
                                       { "ros_cmd" : "ros/request_pose_list" } )
    self._server.register_command( "ros/send_and_parse_xml", self.run_rosetta_command,
                                       { "ros_cmd" : "ros/send_and_parse_xml", "pose_name" : None, "xml" : None } )
    self._server.register_command( "get_rosetta_args", self.get_rosetta_command_args,
                                       { "ros_cmd_name" : "ros/echo_message" } )
    # Compound commands to run a set of different rosetta commands together
    self._server.register_command( "ros/run_rosetta_script", self.run_rosetta_script,
                                   { "pdb" : None, "pdb_name" : None, "xml" : None,
                                     "num_frames" : 10000, "request_interval" : 0.01, "num_retries" : -1, "view_in_progress" : True } )

    # Add commands for manipulating in progress viewing with iMD VR client.
    # To do implement play back etc.
    self._server.register_command( PLAY_COMMAND_KEY, self._trajectory.play_saved )
    self._server.register_command( PAUSE_COMMAND_KEY, self._trajectory.pause )
    self._server.register_command( RESET_COMMAND_KEY, self._trajectory.reset )
    self._server.register_command( STEP_COMMAND_KEY, self._trajectory.step )

    # Add commands for NarupaIMD VR client
    self._server.register_command( "ros_build/setup_for_xml_builder", self.stop_collecting_and_setup_for_xml, {} )
    self._server.register_command( "ros_build/new_selection", self.new_residue_selector, {} )
    self._server.register_command( "ros_build/add_to_selection", self._xml_builder.set_add_new_res, {} )
    self._server.register_command( "ros_build/rm_from_selection", self._xml_builder.set_rm_new_res, {} )
    self._server.register_command( "ros_build/choose_selections", self.set_active_selectors , { "active_selectors" : {} } )
    self._server.register_command( "ros_build/add_movers", self._xml_builder.add_new_movers, { "selected_movers" : {} } )
    self._server.register_command( "ros_build/run_xml", self.get_xml_and_run, {} )

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
    with self._lock:
      if ros_cmd in self._ros_cmds.keys():
        return self._ros_cmds[ros_cmd].execute( client=self._rosetta, **kwargs )
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
    with self._lock:
      if not ros_cmd_name or not ros_cmd:
        raise ValueError( "Rosetta Command name cannot be None." )
      if ros_cmd_name in self._ros_cmds.keys():
        raise ValueError( "Rosetta command name already exists." )
      if ros_cmd_name.split("/")[0] != "ros":
        ros_cmd_name = "ros/" + ros_cmd_name

      # Check protected arguments (client and key) haven't been used
      if "client" in cmd_args.keys() or "key" in cmd_args.keys():
        raise KeyError( "\"client\" and \"key\" are protected arguments. These cannot be used in user defined RosettaCommand." )

      self._ros_cmds[ros_cmd_name] = ros_cmd.execute
      self._server.register_command( f"{ros_cmd_name}", self.run_rosetta_command, cmd_args )

  def get_rosetta_command_args(self,
                               ros_cmd_name : str) -> Dict[str, str]:
    """
    Gets the keyword arguments and default value parameters used for calling the specified RosettaCommand

    :param ros_cmd_name: Name of the RosettaCommand as stored when the command was registered.
    :return Dict { kw_arg : arg_type, ..., return : return_type } : Dictionary of keyword arguments and return names and types.
    """
    with self._lock:
      if ros_cmd_name in self._ros_cmds.keys():
        return_val = self._ros_cmds[ros_cmd_name]._execute.__annotations__
        for key in return_val.keys():
          return_val[key] = str(return_val[key])
        return return_val
      else:
        raise KeyError( "Command not recognised" )

  def run_rosetta_script( self,
                          pdb : str = None,
                          pdb_name : str = None,
                          xml : str = None,
                          num_frames : int = 10000, # TODO implement a way to continue past this threshold if desired
                          request_interval : float = 0.01,
                          num_retries : int = -1, # -1 will set to run until stopped
                          view_in_progress : bool = True ): # TODO implement proper saved viewing

    # In all cases want to always use Rosetta pdbs where possible. This also doubles as a check to see whether the pose actually exists
    if not pdb and not pdb_name:
      raise ValueError( "PDB file and pose name have not been specified, aborting." )
    elif not pdb and pdb_name:
      try:
        pose = self.request_pose( pdb_name )
      except FormatError:
        raise ValueError( f"Pdb_name {pdb_name} not recognised by Rosetta server. Request pose list to see server identifiers for poses." )
    else:
      pdb_name = self.run_rosetta_command( ros_cmd="ros/send_pose", pose_name=pdb_name, pose_to_store=pdb )
      pdb_name = pdb_name["pose_name"]
      pose = self.request_pose( pdb_name )

    # TODO look into why num_frames is converted to float
    num_frames = int(num_frames)
    num_retries = int(num_retries)

    if not xml:
      raise ValueError( "Cannot do anything without a valid RosettaScript" )
    with self._lock:
      if not self._script_in_progress:
        self._script_in_progress = True
        self._trajectory.clear_frames()
        self._trajectory.stored_frames.append( pose["pose_pdb"] )
      else:
        return

    if view_in_progress:
      self._threads.submit( self._run_rosetta_script_realtime, pdb_name, xml, request_interval, num_retries )

  def _run_rosetta_script_realtime( self,
                                    pdb_name : str,
                                    xml: str,
                                    request_interval : float,
                                    num_retries : int ):
    """"""
    self._trajectory.realtime_playback()
    self.run_rosetta_command( "ros/send_and_parse_xml", pose_name=pdb_name, xml=xml )
    num_tries = 0
    while num_tries <= num_retries or num_retries == -1:
      with self._lock:
        if not self._script_in_progress:
          break
      try:
        frame = self.request_pose(pdb_name)
        self._trajectory.update_frames( frame["pose_pdb"] )
        num_tries = 0
      except FormatError:
        num_tries += 1
      sleep( request_interval )
    with self._lock:
      self._script_in_progress = False
      self._trajectory.cancel_realtime()

  def stop_collecting_and_setup_for_xml( self ):
    """"""
    with self._lock:
      self._script_in_progress = False
      self._trajectory.cancel_realtime()
    self._trajectory.send_current_frame()
    self._xml_builder.add_pdb( self._trajectory.get_current_frame() )
    change = DictionaryChange( { **self._xml_builder.get_residue_selector_dict(),
                                 **self._xml_builder.get_movers_dict() }, [] )
    self._server.update_state( None, change )

  def get_xml_and_run( self ):
    xml_str = self._xml_builder.export_xml()
    self.set_active_selectors( {} )
    self.run_rosetta_script( pdb=self._trajectory.get_current_frame(), xml=xml_str )

  def new_residue_selector( self ):
    self._xml_builder.new_residue_selector()
    selectors = self._xml_builder.get_residue_selector_dict()
    change = DictionaryChange( selectors, [] )
    self._server.update_state( None, change )

  def set_active_selectors( self,
                            active_selectors : dict = None ):
    selectors = self._xml_builder.set_active_residue_selectors( active_selectors )
    change = DictionaryChange( selectors, [] )
    self._server.update_state( None, change )

  def close( self ):
    self._renderer.close()
    self._server.close()
    self._rosetta.close()



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