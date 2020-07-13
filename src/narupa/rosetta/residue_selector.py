# Copyright (c) Tim Neary, University of Bristol. Github username: TENeary, contact: tn15550@bristol.ac.uk
# Licensed under the GPL. See License.txt in the project root for license information.

import xml.etree.ElementTree as xml
import numpy as np

ACCEPTED_RES_SELECTORS = [ "Index" ]

class ResidueSelector:
  """
  Container class for convience when building new residue selectors for RosettaScrips.
  Is used in the RosettaScripts builder when constructing new XMls
  """
  def __init__( self,
                name : str = None,
                sele_type : str = None,
                res_list : np.ndarray = None ):
    if name:
      self.name = name
    else:
      self.name = ""

    if sele_type in ACCEPTED_RES_SELECTORS and sele_type:
      self.type = sele_type
    elif not sele_type:
      self.type = "Index"
    else:
      raise ValueError( f"Residue selector type of {sele_type} is not accepted. See Rosetta documentation or ACCEPTED_RES_SELECTORS for the list of accepted types.")

    if res_list:
      self.residues = np.unique( res_list )
    else:
      self.residues = np.array( [], dtype=int )


  @property
  def is_empty( self ) -> bool:
    return len(self.residues) > 0

  def _validate( self ) -> bool:
    if self.type in ACCEPTED_RES_SELECTORS:
      return True
    else:
      raise ValueError( f"Residue selector type of {self.type} is not accepted. See Rosetta documentation or ACCEPTED_RES_SELECTORS for the list of accepted types.")

  def to_string( self ) -> str:
    self._validate()
    return ",".join( self.residues.astype(str) )

  def to_dict( self ) -> dict:
    self._validate()
    return { self.name : self.to_string() }

  def to_xml( self ) -> xml.Element:
    self._validate()
    return xml.Element( self.type,
                        name=self.name,
                        resnums=self.to_string(),
                        error_on_out_of_bounds_index="true",
                        reverse="false")

  def add_residues( self,
                    pdb_info : np.ndarray, # Expected to be [ atom_id, res_id, res_name ]
                    atom_selections : np.ndarray ):
    """
    Converts list of atom selectons to a unique set of residue ids.

    :param pdb_info: Numpy array of shape (N, 3) in the form [ atom_id, res_id, res_name ]
    :param atom_selections: list of atom ids for the selection.
    """
    idx, = np.where( np.isin( pdb_info[:, 0] == atom_selections ) )
    self.residues = np.unique( np.concatenate( self.residues, pdb_info[idx, 1] ) )

  def remove_residues( self,
                       pdb_info : np.ndarray,
                       atom_selections : np.ndarray ):
    """
    Converts a list of atom selections to a unique set of residue ids and removes those from the current list of residues

    :param pdb_info:
    :param atom_selections:
    """
    idx, = np.where( np.isin( pdb_info[:, 0] == atom_selections ) )
    self.residues = np.delete( self.residues, pdb_info[idx, 1] - 1 )