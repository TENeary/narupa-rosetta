Rosetta server implementation for Narupa
========================================

This server allows for visualisation of Rosetta simulations.

External requirements:
----------------------

This repository requires both Narupa and Rosetta to be installed separately.

Narupa can be clones from the following repository:
    https://gitlab.com/intangiblerealities/narupa-protocol

To install Rosetta see:
    https://www.rosettacommons.org/software
This python module communicates to Rosetta through using the rosetta_interactive server.
To correctly compile and run this application rosetta must be compiled using the cxxthreads and zeromq extra options.
The following is an example command line for compiling Rosetta with these extras:
```bash
./scons.py mode=release -j4 bin extras=cxx11thread,zeromq
```

Communicating with Rosetta
--------------------------

This repository contains a set of commands derived from a common base class (RosettaCommand) which can be used for communication with a running Rosetta server.
These commands can found in command_utils.py and contain, in addition to the base class, the most basic of commands needed for communication and running Rosetta simulations.
All commands require a reference to a RosettaClient and return a dictionary containing the response message from the Rosetta Server.
An example of a potential interaction follows:

```python
from narupa.rosetta.command_util import EchoMessage
from narupa.rosetta.rosetta_communicator import RosettaClient

client = RosettaClient( rosetta_server_address="localhost", rosetta_server_port="43234" )
client.connect()

echo = EchoMessage.execute( client=client, msg="Echo" )
print( echo )
```

NB: All new RosettaCommands which contact the server must be a member of a given (key, value) pair accepted by the server.

Using the outputs from Rosetta
------------------------------

To visualise the Rosetta simulations it is recommended you use the RosettaRunner class.
This class can be invoked using both the command line and within a python environment, see below:

TODO