# Copyright (c) Tim Neary, University of Bristol. Github username: TENeary, contact: tn15550@bristol.ac.uk
# Licensed under the GPL. See License.txt in the project root for license information.

from narupa.rosetta.runner import RosettaRunner
from narupa.rosetta.rosetta_communicator import DEFAULT_ROSETTA_ADDRESS, DEFAULT_ROSETTA_PORT
from narupa.core import DEFAULT_SERVE_ADDRESS
from narupa.app.app_server import DEFAULT_NARUPA_PORT

from os.path import isfile

from typing import Dict
from argparse import Namespace


def main(args : Namespace) -> RosettaRunner:
    if not isfile(args.pdb_file):
        raise FileNotFoundError(f"Could not find the PDB file: {args.pdb_file}")

    with open(args.pdb_file, "r") as r:
        pdb = r.read()

    runner = RosettaRunner(
        narupa_server_address=args.npa_add,
        narupa_server_port=args.npa_prt,
        rosetta_server_address=args.ros_add,
        rosetta_server_port=args.ros_prt)

    # Test connection to RosettaExchange
    if not runner.can_contact_rosetta():
        raise ConnectionError(f"Cannot connect to RosettaExchange server at address: {args.ros_add} | port: {args.ros_prt}.\n"
                              f"Please check the address and port have been inputted correctly.")

    # Send the pose to RosettaExchange then recieve a copy of the structure from Rosetta.
    pose_name = runner.run_rosetta_command("ros/send_pose", pose_name="basic_setup_pose", pose_to_store=pdb)["pose_name"]
    # pose_info = runner.request_pose_info(pose_name=pose_name)
    runner._trajectory.stored_frames = [runner.request_pose(pose_name=pose_name)["pose_pdb"]]
    runner._trajectory.send_current_frame()

    return runner


def _get_user_input():
    return input("Enter [y] to close the RosettaRunner... | ")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simple script to setup and run a RosettaRunner with the relevant provided "
                                                 "configuration. Will enable a user to do simple design protocols on a given PDB.")
    parser.add_argument("--ros_add", type=str, default=DEFAULT_ROSETTA_ADDRESS,
                        help="Address of the computer running the RosettaExchange to connect to.")
    parser.add_argument("--ros_prt", type=int, default=DEFAULT_ROSETTA_PORT,
                        help="Port of the RosettaExchange server to connect to.")
    parser.add_argument("--npa_add", type=str, default=None,#default=DEFAULT_SERVE_ADDRESS,
                        help="Address to use when creating the NarupaServer.")
    parser.add_argument("--npa_prt", type=int, default=None,#default=DEFAULT_NARUPA_PORT,
                        help="Port on which to open the NarupaServer on.")

    parser.add_argument("pdb_file", type=str,
                        help="Name of a PDB file to design.")

    args = parser.parse_args()

    runner = main(args)
    input_ = _get_user_input()
    while input_.lower() != "y":
        input_ = _get_user_input()
    runner.close()
