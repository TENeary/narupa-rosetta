# Copyright (c) Tim Neary, University of Bristol. Github username: TENeary, contact: tn15550@bristol.ac.uk
# Licensed under the GPL. See License.txt in the project root for license information.

import xml.etree.ElementTree as xml
import numpy as np
from narupa.state.state_dictionary import DictionaryChange
from .pdb_util import get_residues_from_pdb_list
from .residue_selector import ResidueSelector

SHARED_DICT_KEY_RES_SELE = "ros/residue_selectors"
SHARED_DICT_KEY_MOVER = "ros/movers"

# Consts to allow for quicker change if names or syntax change
ROSETTASCRIPTS = "ROSETTASCRIPTS"
SCOREFXNS = "SCOREFXNS"
RESIDUE_SELECTORS = "RESIDUE_SELECTORS"
TASKOPERATIONS = "TASKOPERATIONS"
SIMPLE_METRICS = "SIMPLE_METRICS"
FILTERS = "FILTERS"
MOVERS = "MOVERS"
PROTOCOLS = "PROTOCOLS"
OUTPUT = "OUTPUT" # Technically should be obsolete in RosettaScripts now

class RosettaScriptsBuilder:
  """
  Takes selections from Narupa to build Rosetta scripts.
  Currently the builder is limited to a subset of commands available to RosettaScripts
  """
  def __init__( self,
                pdb : str = None,
                delimiter : str = None,
                pdb_list : list = None ):
    """"""
    self._pdb = None
    self.add_pdb( pdb, delimiter, pdb_list )
    self._pdb_info = get_residues_from_pdb_list( self._pdb ) # [ atom_id, res_id, res_name ]

    self.residue_selectors = [ ResidueSelector( name="Total Protein", sele_type="Index", res_list=self._pdb_info[:, 1] ) ]
    self._active_residue_selectors = []
    self._add_res_to_sele = True

    self._available_movers = { "FastDesign" : self.add_fastdesign_mover,
                               "FastRelax" : self.add_fastrelax_mover,
                               "PackRotamers" : self.add_pack_mover,
                               "Minimise" : self.add_minimise_mover }
    # TODO move mover constructor as objects

    self._build_default_rosetta_script()


  def add_pdb( self,
               pdb : str = None,
               delimiter : str = None,
               pdb_list : list = None ):
    if pdb:
      self._pdb = pdb.split(delimiter)
    elif pdb_list:
      self._pdb = pdb_list
    else:
      self._pdb = None
    self._pdb_info = get_residues_from_pdb_list( self._pdb )

  def _build_default_rosetta_script( self ):
    """
    Builds default RosettaScript XML format.
    It will be assumed that each first level SubElement is never duplicated.
    """
    self._xml = xml.Element(ROSETTASCRIPTS)
    self._xml.append( xml.Element(SCOREFXNS) )
    self._xml.append( xml.Element(RESIDUE_SELECTORS) )
    self._xml.append( xml.Element(TASKOPERATIONS) )
    self._xml.append( xml.Element(SIMPLE_METRICS) )
    self._xml.append( xml.Element(FILTERS) )
    self._xml.append( xml.Element(MOVERS) )
    self._xml.append( xml.Element(PROTOCOLS) )
    self._xml.append( xml.Element(OUTPUT) )

  def rebuild_xml( self ):
    """
    Recreates the stored XML in the form of the default RosettaScript format.
    """
    self._build_default_rosetta_script()

  def clear( self ):
    """
    Clears all stored information, including pdb, xml and atom and residue information.
    """
    self._pdb = None
    self._pdb_info = None
    self._build_default_rosetta_script()

  def get_residue_selector_dict( self ) -> dict:
    """"""
    shared_dict_key = { SHARED_DICT_KEY_RES_SELE : [] }
    for res_sele in self.residue_selectors:
      if res_sele.name in self._active_residue_selectors:
        active = True
      else:
        active = False
      shared_dict_key[SHARED_DICT_KEY_RES_SELE].append( [res_sele.name, active] )
    return shared_dict_key

  def get_movers_dict( self ):
    """"""
    shared_dict_key = { SHARED_DICT_KEY_MOVER : [] }
    for mover in self._available_movers.keys():
      shared_dict_key[SHARED_DICT_KEY_MOVER].append( [mover, False] )
    return shared_dict_key

  def new_residue_selector( self ):
    self.residue_selectors.append( ResidueSelector( name="selector" + str(len(self.residue_selectors)), sele_type="Index" ) )

  def _entry_exists( self,
                     entry_name : str,
                     entry_type : str,
                     first_level_field : str ) -> bool:
    """"""
    try:
      selectors = list(self._xml.find(first_level_field).findall(entry_type))
    except:
      raise KeyError( f"Given keys do not exist: Could not find {first_level_field} in top levels fields or {entry_type} in sub-fields.")
    return any( [ ele.get("name") == entry_name for ele in selectors ] )

  def _get_unique_name( self,
                        first_level_field : str,
                        entry_type : str,
                        curr_name: str = None,
                        prefix : str = None ) -> str:
    """"""
    if prefix:
      new_name = prefix
    else:
      new_name = curr_name

    if not curr_name:
      new_name += str(len(list(self._xml.find(first_level_field))))
    elif self._entry_exists(curr_name, entry_type, first_level_field):
      new_name += str(len(list(self._xml.find(first_level_field))))
    else:
      new_name = curr_name

    return new_name

  def add_index_residue_selector( self,
                                  residue_selector : ResidueSelector = None,
                                  selector_name : str = None,
                                  atom_selections : np.ndarray = None ) -> str:
    """"""
    sele_type = "Index"
    selector_name = self._get_unique_name(RESIDUE_SELECTORS, sele_type, selector_name)
    if residue_selector:
      if residue_selector.type != "Index":
        residue_selector.name = selector_name
        selector = residue_selector.to_xml()
      else:
        raise ValueError( f"Only residue selectors of type {residue_selector.type} should be added with this method" )
    else:
      selector = ResidueSelector( name=selector_name, sele_type="Index", res_list=atom_selections )
    self._xml.find(RESIDUE_SELECTORS).append( selector.to_xml() )
    return selector_name

  def _add_new_res( self,
                    res_list : list ):
    """"""
    return

  def _rm_new_res( self,
                   res_list : list ):
    """"""
    return

  def new_residues( self,
                    res_list : list ):
    """"""
    if self._add_res_to_sele:
      self._add_new_res( res_list )
    else:
      self._rm_new_res( res_list )

  def set_add_new_res( self ):
    self._add_res_to_sele = True

  def set_rm_new_res( self ):
    self._add_res_to_sele = False

  def set_active_residue_selectors( self,
                                    active_selectors : dict = {} ):
    """"""
    if active_selectors == {}:
      self._active_residue_selectors = []
    else:
      active_selectors = []
      for selector, active in active_selectors.values():
        if active:
          active_selectors.append( selector )

  def add_pack_mover( self, # TODO implement way to add all available args to RosettaScripts
                      mover_name : str = None,
                      residue_selectors: list = None,
                      task_operations : str = None ):
    """"""
    mover_type  = "PackRotamersMover" # TODO add task operations
    mover_name = self._get_unique_name( MOVERS, mover_type, mover_name )
    mover = xml.Element( mover_type,
                         name=mover_name,
                         # task_operations="",
                         )
    self._xml.find(MOVERS).append( mover )
    return mover_name

  def add_minimise_mover( self,
                          residue_selectors: list = None,
                          mover_name : str = None ):
    """"""
    mover_type = "MinMover"
    mover_name = self._get_unique_name(MOVERS, mover_type, mover_name)
    mover = xml.Element( mover_type,
                         name=mover_name,
                         chi="true",
                         bb="true",
                         jump="0",
                         tolerance="0.1",
                         max_iter="1000" )
    self._xml.find(RESIDUE_SELECTORS).append( mover )
    return mover

  def add_fastdesign_mover( self,
                            mover_name : str = None,
                            residue_selectors : list = None,
                            task_operations : list = None ):
    """"""
    mover_type = "FastDesign" # TODO add task operations
    mover_name = self._get_unique_name(MOVERS, mover_type, mover_name)
    mover = xml.Element(mover_type,
                        name=mover_name,
                        # scorefxn="",
                        # task_operations="",
                        # cst_file=""
                        )
    self._xml.find(RESIDUE_SELECTORS).append( mover )
    return mover

  def add_fastrelax_mover( self,
                           mover_name : str = None,
                           residue_selectors : list = None,
                           task_operations : list = None ):
    """"""
    return

  def _create_combined_residue_selector( self,
                                         residue_selectors : list,
                                         sele_type : str = "Index") -> ResidueSelector:
    """"""
    comb_sele_name = self._get_unique_name( RESIDUE_SELECTORS, sele_type, prefix="comb_" )
    all_res = np.array( [], dtype=int )
    for sele in residue_selectors:
      all_res = np.concatenate( all_res, sele.residues )
    comb_selector = ResidueSelector( comb_sele_name, sele_type, res_list=all_res )
    return comb_selector

  def add_new_movers( self,
                      selected_movers = {} ):
    """"""
    # Currently all movers added will be auto generated and use the active residue selectors
    if selected_movers == {}:
      return
    for mover, selected in selected_movers.values():
      if selected and mover in self._available_movers:
        res_sele = self._create_combined_residue_selector( residue_selectors=selected_movers )
        self._available_movers[mover]( residue_selectors=res_sele )

  def _finalise_xml( self ):
    # TODO implement checks that all referenced residue selectors/task operations are included
    # TODO add all movers to the list of protocols
    return

  def export_xml(self) -> str:
    """"""
    self._finalise_xml()
    return xml.tostring( self._xml, encoding="utf-8" ).decode() # As to string gives a bytearray