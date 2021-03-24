# Copyright (c) Tim Neary, University of Bristol. Github username: TENeary, contact: tn15550@bristol.ac.uk
# Licensed under the GPL. See License.txt in the project root for license information.

import xml.etree.ElementTree as xml
import numpy as np
from concurrent import futures
from threading import RLock

from narupa.app import NarupaImdClient
from narupa.state.state_service import DictionaryChange

from .pdb_util import get_residues_from_pdb_list
from .residue_selector import ResidueSelector

SHARED_DICT_KEY_RES_SELE = "ros/residue_selectors"
SHARED_DICT_KEY_MOVER = "ros/movers"

DEFAULT_TASK_OPERATION = "OperateOnResidueSubset"
PREVENT_DESIGN = "RestrictToRepackingRLT"
PREVENT_REPACK = "PreventRepackingRLT"

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
  def __init__(self,
               pdb : str = None,
               delimiter : str = None,
               pdb_list : list = None,
               renderer : NarupaImdClient = None):
    """"""
    self._thread_pool = futures.ThreadPoolExecutor(max_workers=1)
    self._selection_lock = RLock()

    if renderer:
      self._renderer = renderer
      self.root_selection = self._renderer.root_selection
      self.active_selection = self._renderer.create_selection(name="active_particles")
    else:
      raise ValueError( "renderer cannot be None" )

    self.residue_selectors = []
    self._active_residue_selectors = []
    self._add_res_to_sele = True

    self._pdb = None
    self._pdb_info = None # [ atom_id, res_id, res_name ]
    self.add_pdb(pdb, delimiter, pdb_list)

    self._available_movers = { "FastDesign" : self.add_fastdesign_mover,
                               "FastRelax" : self.add_fastrelax_mover,
                               "PackRotamers" : self.add_pack_mover,
                               "Minimise" : self.add_minimise_mover }
    # TODO move mover constructor as objects


  def add_pdb(self,
              pdb : str = None,
              delimiter : str = "\n",
              pdb_list : list = None) -> None:
    with self._selection_lock:
      self.clear()
      if pdb:
        self._pdb = pdb.split(delimiter)
      elif pdb_list:
        self._pdb = pdb_list
      else:
        self._pdb = None
      if self._pdb is not None:
        self._pdb_info = get_residues_from_pdb_list(self._pdb)
        self.residue_selectors = [ResidueSelector(name="Whole Protein", sele_type="Index", res_list=self._pdb_info[:, 1])]
        self._thread_pool.submit(self.update_renderer, True)

  def _build_default_rosetta_script(self) -> None:
    """
    Builds default RosettaScript XML format.
    It will be assumed that each first level SubElement is never duplicated.
    """
    self._xml = xml.Element(ROSETTASCRIPTS)
    self._xml.append(xml.Element(SCOREFXNS))
    self._xml.append(xml.Element(RESIDUE_SELECTORS))
    self._xml.append(xml.Element(TASKOPERATIONS))
    self._xml.append(xml.Element(SIMPLE_METRICS))
    self._xml.append(xml.Element(FILTERS))
    self._xml.append(xml.Element(MOVERS))
    self._xml.append(xml.Element(PROTOCOLS))
    self._xml.append(xml.Element(OUTPUT))

  def import_xml_from_string(self,
                             xml_str : str) -> None:
    """
    Sets the current XML script to be the xml provided.
    TODO do basic error checking to ensure it matches the standard ROSETTASCRIPT format
    """
    self._xml = xml.fromstring(xml_str)

  def rebuild_xml(self) -> None:
    """
    Recreates the stored XML in the form of the default RosettaScript format.
    """
    self._build_default_rosetta_script()

  def clear(self) -> None:
    """
    Clears all stored information, including pdb, xml, atom and residue information.
    """
    self._pdb = None
    self._pdb_info = None
    self._build_default_rosetta_script()
    self._active_residue_selectors = []

  def get_residue_selector_dict(self) -> dict:
    """"""
    shared_dict_key = { SHARED_DICT_KEY_RES_SELE : [] }
    with self._selection_lock:
      for res_sele in self.residue_selectors:
        if res_sele.name in self._active_residue_selectors:
          active = True
        else:
          active = False
        shared_dict_key[SHARED_DICT_KEY_RES_SELE].append([res_sele.name, active])
    return shared_dict_key

  def get_movers_dict(self) -> dict:
    """"""
    shared_dict_key = { SHARED_DICT_KEY_MOVER : [] }
    with self._selection_lock:
      for mover in self._available_movers.keys():
        shared_dict_key[SHARED_DICT_KEY_MOVER].append([mover, False])
    return shared_dict_key

  def new_residue_selector(self) -> None:
    with self._selection_lock:
      self.residue_selectors.append(ResidueSelector(name="selector" + str(len(self.residue_selectors)), sele_type="Index"))

  def _entry_exists(self,
                    entry_name : str,
                    entry_type : str,
                    first_level_field : str) -> bool:
    """"""
    try:
      selectors = list(self._xml.find(first_level_field).findall(entry_type))
    except:
      raise KeyError( f"Given keys do not exist: Could not find {first_level_field} in top levels fields or {entry_type} in sub-fields.")
    return any([ele.get("name") == entry_name for ele in selectors])

  def _get_unique_name(self,
                       first_level_field : str,
                       entry_type : str,
                       curr_name: str = None,
                       prefix : str = None) -> str:
    """"""
    new_name = ""
    if prefix:
      new_name += prefix

    if not curr_name or self._entry_exists(curr_name, entry_type, first_level_field):
      new_name += first_level_field.lower()
      new_name += str(len(list(self._xml.find(first_level_field))))
    else:
      new_name += curr_name

    return new_name

  def add_index_residue_selector(self,
                                 residue_selector : ResidueSelector = None,
                                 selector_name : str = None,
                                 atom_selections : np.ndarray = None) -> str:
    """"""
    sele_type = "Index"
    selector_name = self._get_unique_name(RESIDUE_SELECTORS, sele_type, selector_name)
    if residue_selector:
      if residue_selector.type == "Index" and not residue_selector.is_empty:
        residue_selector.name = selector_name
        selector = residue_selector
      else:
        raise ValueError(f"Only non-empty ({not residue_selector.is_empty}) residue selectors of type {residue_selector.type} should be added with this method.")
    else:
      selector = ResidueSelector(name=selector_name, sele_type="Index", res_list=atom_selections)
    self._xml.find(RESIDUE_SELECTORS).append(selector.to_xml())
    return selector_name

  def _get_all_active_particles(self) -> np.array:
    """"""
    if self._pdb is None:
      return np.array([], dtype=int)
    all_res = np.array([], dtype=int)
    with self._selection_lock:
      for sele in self.residue_selectors:
        if sele.name in self._active_residue_selectors:
          all_res = np.concatenate((all_res, sele.residues))
      all_particles = self._pdb_info[np.isin(self._pdb_info[:, 1].astype(int), all_res), 0].astype(int) - 1
    return all_particles

  def update_renderer(self,
                      update_global : bool = False) -> None:
    """"""
    active_particles = map(int, self._get_all_active_particles())
    if update_global:
      with self.root_selection.modify() as root:
        root.renderer = { "color" : "cpk",
                          "render" : "ball and stick" }
      self.root_selection.flush_changes()
    # if not np.isin( active_particles, self.active_selection.selected_particle_ids ).any():
    with self.active_selection.modify() as selection:
      selection.set_particles(active_particles)
      selection.renderer = { "color" : "Green",
                             "render" : "ball and stick" }
    self.active_selection.flush_changes()

  def add_new_res(self,
                  particles : list) -> None:
    """"""
    with self._selection_lock:
      for res_sele in self.residue_selectors:
        if res_sele.name in self._active_residue_selectors:
          res_sele.add_residues(self._pdb_info, np.asarray(particles, dtype=int))

  def rm_new_res(self,
                 particles : list) -> None:
    """"""
    with self._selection_lock:
      for res_sele in self.residue_selectors:
        if res_sele.name in self._active_residue_selectors:
          res_sele.remove_residues(self._pdb_info, np.asarray(particles, dtype=int))

  def new_residues(self,
                   access_token,
                   change : DictionaryChange) -> None:
    """"""
    if not self._pdb or change.updates is None:
      return
    all_particles = []
    for key, item in change.updates.items():
      if key.startswith("interaction."):
        all_particles.extend(item["particles"])
    if not all_particles:
      return
    with self._selection_lock:
      if self._add_res_to_sele:
        self.add_new_res(all_particles)
      else:
        self.rm_new_res(all_particles)
    self._thread_pool.submit(self.update_renderer, True)

  def set_add_new_res(self) -> None:
    """"""
    self._add_res_to_sele = True

  def set_rm_new_res(self) -> None:
    """"""
    self._add_res_to_sele = False

  def set_active_residue_selectors(self,
                                   active_selectors : dict = None) -> dict:
    """"""
    self._active_residue_selectors = []
    with self._selection_lock:
      if active_selectors is None:
        pass
      else:
        for selector, active in active_selectors.items():
          if active:
            self._active_residue_selectors.append(selector)
    self._thread_pool.submit(self.update_renderer, False)
    return self.get_residue_selector_dict()

  def _create_combined_residue_selector(self,
                                        residue_selectors : list,
                                        sele_type : str = "Index") -> ResidueSelector:
    """"""
    comb_sele_name = self._get_unique_name(RESIDUE_SELECTORS, sele_type, prefix="comb_")
    all_res = np.array([], dtype=int)
    for sele in self.residue_selectors:
      if sele.name in residue_selectors:
        all_res = np.concatenate((all_res, sele.residues))
    comb_selector = ResidueSelector(comb_sele_name, sele_type, res_list=all_res)
    return comb_selector

  def add_task_operation(self,
                         residue_selectors : list,
                         invert_selection : bool = False,
                         prevent_design : bool = False) -> str: # TODO implement a way to add multiple task_operations of different types.
    res_sele_names = []
    for res_sele in residue_selectors:
      if invert_selection:
        res_sele = res_sele.invert(self._pdb_info)
      res_sele_names.append(self.add_index_residue_selector(residue_selector=res_sele))

    task_operation_name = self._get_unique_name(TASKOPERATIONS, DEFAULT_TASK_OPERATION)
    task_operation = xml.Element(DEFAULT_TASK_OPERATION,
                                 name=task_operation_name,
                                 selector=",".join(res_sele_names),
                                 )
    if prevent_design:
      task_operation.append(xml.Element(PREVENT_DESIGN))
    else:
      task_operation.append(xml.Element(PREVENT_REPACK))
    self._xml.find(TASKOPERATIONS).append(task_operation)
    return task_operation_name

  def add_pack_mover(self, # TODO implement way to add all available args to RosettaScripts
                     mover_name : str = None,
                     residue_selectors: list = None,
                     task_operations : str = None) -> str:
    """"""
    mover_type  = "PackRotamersMover"
    mover_name = self._get_unique_name(MOVERS, mover_type, mover_name)
    if not residue_selectors:
      residue_selectors = self._active_residue_selectors
    comb_res_sele = self._create_combined_residue_selector(residue_selectors).invert(self._pdb_info)

    mover_dict = { "name" : mover_name,
                   }
    if not comb_res_sele.is_empty:
      task_operation_name = self.add_task_operation([comb_res_sele], invert_selection=False, prevent_design=False)
      mover_dict.update({ "task_operations" : task_operation_name,
                          })

    mover = xml.Element(mover_type,
                        **mover_dict)
    self._xml.find(MOVERS).append(mover)
    return mover_name

  def add_minimise_mover(self,
                         residue_selectors: list = None,
                         mover_name : str = None) -> xml.Element: # TODO currently cannot be controlled with selections implement movemap factory builder
    """"""
    mover_type = "MinMover"
    mover_name = self._get_unique_name(MOVERS, mover_type, mover_name)
    mover = xml.Element(mover_type,
                        name=mover_name,
                        chi="true",
                        bb="true",
                        jump="0",
                        tolerance="0.1",
                        max_iter="1000")
    self._xml.find(MOVERS).append(mover)
    return mover

  def add_fastdesign_mover(self,
                           mover_name : str = None,
                           residue_selectors : list = None,
                           task_operations : list = None) -> xml.Element:
    """"""
    mover_type = "FastDesign"
    mover_name = self._get_unique_name(MOVERS, mover_type, mover_name)
    if not residue_selectors:
      residue_selectors = self._active_residue_selectors
    comb_res_sele = self._create_combined_residue_selector(residue_selectors).invert(self._pdb_info)
    mover_dict = { "name" : mover_name,
                   # "scorefxn" : "",
                   # "cst_file" : "",
                   }
    if not comb_res_sele.is_empty:
      task_operation_name = self.add_task_operation([comb_res_sele], invert_selection=False, prevent_design=False)
      mover_dict.update({ "task_operations" : task_operation_name,
                          })

    mover = xml.Element(mover_type,
                        **mover_dict)
    self._xml.find(MOVERS).append(mover)
    return mover

  def add_fastrelax_mover(self,
                          mover_name : str = None,
                          residue_selectors : list = None,
                          task_operations : list = None) -> xml.Element:
    """"""
    mover_type = "FastDesign"
    mover_name = self._get_unique_name(MOVERS, mover_type, mover_name)
    if not residue_selectors:
      residue_selectors = self._active_residue_selectors
    comb_res_sele = self._create_combined_residue_selector(residue_selectors).invert(self._pdb_info)
    mover_dict = { "name" : mover_name,
                   # "scorefxn" : "",
                   # "cst_file" : "",
                   }
    if not comb_res_sele.is_empty:
      task_operation_name = self.add_task_operation([comb_res_sele], invert_selection=False, prevent_design=False)
      mover_dict.update({ "task_operations" : task_operation_name,
                          })

    mover = xml.Element(mover_type,
                        **mover_dict)
    self._xml.find(MOVERS).append(mover)
    return mover

  def add_new_movers(self,
                     selected_movers : dict = None,
                     residue_selectors : list = None) -> None:
    """"""
    # Currently all movers' names will be auto generated and use the active residue selectors
    if selected_movers is None or selected_movers == {}:
      return
    for mover, selected in selected_movers.items():
      if selected and mover in self._available_movers:
        with self._selection_lock:
          self._available_movers[mover](residue_selectors=residue_selectors)

  def _finalise_xml(self) -> None:
    # TODO implement checks that all referenced residue selectors/task operations are included
    mov_names = []
    proto_names = self._xml.find(PROTOCOLS)
    for mov in self._xml.find(MOVERS):
      if mov.attrib["name"]:
        mov_names.append(mov.attrib["name"])
      else:
        raise KeyError(f"Mover {mov.tag} does not have required field \"name\"")
    for proto in self._xml.find(PROTOCOLS):
      if proto.attrib["mover_name"]:
        proto_names.append(proto.attrib["mover_name"])

    for mov in mov_names:
      if not mov in proto_names:
        proto_ele = xml.Element("Add",
                                mover_name=mov)
        self._xml.find(PROTOCOLS).append(proto_ele)

  def export_xml(self) -> str:
    """"""
    self._finalise_xml()
    return xml.tostring(self._xml, encoding="utf-8").decode() # As to string gives a bytearray