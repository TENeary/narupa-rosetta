# Copyright (c) Tim Neary, University of Bristol. Github username: TENeary, contact: tn15550@bristol.ac.uk
# Licensed under the GPL. See License.txt in the project root for license information.

from typing import Tuple, Optional

from narupa.app import NarupaFrameApplication
from .rosetta_command_service import RosettaServer
from narupa.core import DEFAULT_SERVE_ADDRESS
from narupa.essd import DiscoveryServer
from .rosetta_communicator import DEFAULT_ROSETTA_ADDRESS, DEFAULT_ROSETTA_PORT

DEFAULT_NARUPA_PORT = 38801
MULTIPLAYER_SERVICE_NAME = "multiplayer"

def start_rosetta_server_and_discovery(address : Optional[str] = None,
                                       port : Optional[int] = None,
                                       rosetta_address : str = None,
                                       rosetta_port : int = None) -> Tuple[RosettaServer, DiscoveryServer]:
    # TODO add help text
    # Assign address and ports
    address = address or DEFAULT_SERVE_ADDRESS
    port = port or DEFAULT_NARUPA_PORT
    rosetta_address = rosetta_address or DEFAULT_ROSETTA_ADDRESS
    rosetta_port = rosetta_port or DEFAULT_ROSETTA_PORT

    try:
      server = RosettaServer( address=address, port=port, rosetta_address=rosetta_address, rosetta_port=rosetta_port )
    except IOError:
      if port == DEFAULT_NARUPA_PORT:
        raise IOError(f'Could not start a server at the default port ({port}). Is another Narupa server running? '
                      f'Use port=0 to let the OS find a free port')
      raise
    discovery = DiscoveryServer()
    return server, discovery



class RosettaApplicationServer(NarupaFrameApplication):
  """
  Usability class, derives from base NarupaApplicationServer but initialises Rosetta based command service
  """
  def __init__(self,
               server: RosettaServer,
               discovery: Optional[DiscoveryServer] = None,
               name: Optional[str] = None):
    super().__init__( server, discovery, name )

  @classmethod
  def basic_server(cls,
                   name : str = None,
                   address : str = None,
                   port : int = None,
                   rosetta_address : str = None,
                   rosetta_port : int = None):
    # TODO add help text
    server, discovery = start_rosetta_server_and_discovery( address=address, port=port,
                                                            rosetta_address=rosetta_address, rosetta_port=rosetta_port )
    return cls(server, discovery, name)