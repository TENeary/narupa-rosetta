# Copyright (c) Tim Neary, University of Bristol. Github username: TENeary, contact: tn15550@bristol.ac.uk
# Licensed under the GPL. See License.txt in the project root for license information.

import numpy as np
from os.path import isfile
from narupa.trajectory import FrameData
from .pdb_consts import ATOM_IDS, RES_LINKAGES, RES3_INFO


def get_residues_from_pdb_list( pdb : list ) -> np.array:
  """"""
  if not pdb:
    return None
  atom_res_index = np.empty( (len(pdb), 3), dtype=object ) # [ atom_id, res_id, res_name ]
  count = 0

  for line in pdb:
    if line[0:6] == "ATOM  " or line[0:6] == "HETATM": # If atom entry:
      atom_res_index[count] = np.array( [line[6:11], line[22:26], line[17:20]], dtype=str )
      count += 1

  atom_res_index = atom_res_index[:count, :]
  return atom_res_index


def get_residues_from_pdb_string( pdb : str,
                              delimiter : str = "\n" ) -> np.array:
  """"""
  return get_residues_from_pdb_list( pdb.split(delimiter) )


def convert_pdb_list_to_framedata( pdb : list ) -> FrameData:
  """
  Method to quickly build a FrameData object from a pdb list.
  Each entry in the list should correspond to a line in the pdb file.
  Only minor error checking is performed on the pdb and only coordinate entries are processed
  Coordinate lines are only processed correctly when formatted as specified by the official documentation
  See: http://www.wwpdb.org/documentation/file-format

  This function uses constants from pdb_consts.py, where assumptions are made that all pdbs parsed are outputs from Rosetta

  :param pdb: String corresponding to the contents of a pdb file.
  :return frame: FrameData object corresponding to the given PDB
  """
  num_lines = len(pdb)
  atom_coords = np.zeros( (num_lines, 3), dtype=float )
  atom_links = np.zeros( (num_lines ** 2, 2), dtype=int )
  atom_ids = np.zeros( (num_lines,), dtype=int )
  res_list = [""] * num_lines
  atom_res = np.zeros( (num_lines,), dtype=int )
  count = 0
  for ii, line in enumerate(pdb):
    if line[0:6] == "ATOM  " or line[0:6] == "HETATM":
      # Only care about atom coordinate entries
      atom_coords[count] = np.array([line[30:38], line[38:46], line[46:54]])
      atom_ids[count] = ATOM_IDS[line[76:78].strip()]
      atom_res[count] = int(line[22:26])

      if res_list[atom_res[count] - 1] == "": # TODO consider multichain proteins, as this current implementation doesnt work properly
        # If we haven't recorded the entry before then get the next res
        # Will eventually use these entries to build atom linkages.
        res_list[atom_res[count] - 1] = line[17:20]
      count += 1
  atom_coords = atom_coords[:count]
  atom_ids = atom_ids[:count]
  atom_res = atom_res[:count]

  res_list = [ res for res in res_list if res != "" ]
  count, atom_count = 0, 0
  for ii, res in enumerate(res_list):
    if ii == 0:
      continue
    if ii == len(res_list) - 1:
      continue # TODO figure out how to deal with termini cases, for now ignore them
    atom_links[count : count + len(RES_LINKAGES[res])] = np.asarray(RES_LINKAGES[res], dtype=int) + atom_count
    count += len(RES_LINKAGES[res])
    atom_count += RES3_INFO[res][0]
  atom_count = 0
  for ii in range( 2, len(res_list) - 1 ): # Now add all links between residues
    # TODO consider termini
    atom_links[count] = np.asarray([RES3_INFO[res_list[ii - 1]][2] + atom_count,
                                    RES3_INFO[res_list[ii]][1] + atom_count + RES3_INFO[res_list[ii - 1]][0]], dtype=int)
    atom_count += RES3_INFO[res_list[ii - 1]][0]
    count += 1
  atom_links += ( 2 + RES3_INFO[res_list[0]][0] ) # Need to account for additional 2 H atoms at N terminus

  atom_links = atom_links[:count]
  frame = FrameData()
  frame.arrays["particle.positions"] = atom_coords.flatten() / 10 # As PDB is in Angstroms but Narupa uses nm
  frame.arrays["bond.pairs"] = atom_links.flatten()
  frame.arrays["particle.elements"] = atom_ids
  frame.arrays["particle.residues"] = atom_res
  frame.residue_count = len(res_list)
  frame.particle_count = len(atom_ids)
  frame.chain_count = 1 # TODO consider multiple chains
  return frame


def convert_pdb_file_to_framedata( pdb_file : str ):
  """
  Converts a pdb file into a FrameData object.
  Parses the file and then passes the resulting list to the
  convert_pdb_list_to_framedata method.

  :param pdb_file: A string corresponding the location of the pdb file to be converted.
  :raises FileNotFoundError: If the designated file cannot be located.
  :return frame: Return value from convert_pdb_list_to_framedata method.
  """
  if isfile( pdb_file ):
    with open( pdb_file, "r" ) as r:
      pdb_lines = r.readlines()
  else:
    raise FileNotFoundError( f"The given file ({pdb_file}) was not found..")
  return convert_pdb_list_to_framedata( pdb_lines )


def convert_pdb_string_to_framedata( pdb_string : str ):
  """
  Splits a pdb string using the given delimiter character.
  The delimiter should be used only at the end of each new line.
  No additional process is made to the string and the resulting list is
  passed to the convert_pdb_list_to_framedata method.

  :param pdb_string: PDB string to be split.
  :param delim: Delimiter to use to split the pdb string with. The delimiter should only be used to split new lines
  :return frame: FrameData object returned by the convert_pdb_list_to_framedata method.
  """
  pdb_list = pdb_string.split("\n")
  return convert_pdb_list_to_framedata( pdb_list )