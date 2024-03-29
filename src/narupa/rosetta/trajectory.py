# Copyright (c) Tim Neary, University of Bristol. Github username: TENeary, contact: tn15550@bristol.ac.uk
# Licensed under the GPL. See License.txt in the project root for license information.

from concurrent import futures
from collections import deque
from threading import RLock
from time import sleep

from narupa.trajectory.frame_publisher import FramePublisher
from .pdb_util import convert_pdb_string_to_framedata

class RosettaTrajectoryManager:
  """
  Used for managing incoming PDBs and in progress frame viewing.
  """
  def __init__(self,
               frame_publisher : FramePublisher,
               stored_frames : int = 100,
               user_fps : int = 15):
    self._frame_publisher = frame_publisher
    self._thread_pool = futures.ThreadPoolExecutor(max_workers=1)
    self._thread = None
    self._lock = RLock()
    self.stored_frames = deque(maxlen=stored_frames)
    self.user_fps = user_fps

    # Bools for controlling the state of the TrajectoryManager
    self._new_frames = None
    self._updated = None
    self._stop = None
    self._pause = None
    self.frame_id = None
    self._reset_bools()


  def _reset_bools(self) -> None:
    with self._lock:
      self._new_frames = True
      self._updated = False
      self._stop = False
      self._pause = False
      self.frame_id = 0

  @property
  def is_collecting(self) -> bool:
    return self._new_frames

  @property
  def is_playing(self) -> bool:
    return not self._stop or not self._pause

  def update_frames(self,
                    new_frame : str = None) -> None:
    with self._lock:
      if new_frame and self._new_frames:
        self.stored_frames.append(new_frame)
        self.frame_id += 1
        self._updated = True

  def clear_frames(self) -> None:
    with self._lock:
      self._new_frames = False
      self._stop = True
    while self._thread and not self._thread.done():
      sleep(0.1)
    with self._lock:
      self.stored_frames.clear()
      self._reset_bools()

  def _send_last_frame(self) -> None:
    frame = None
    with self._lock:
      if self._new_frames and self._updated:
        frame = self.stored_frames[-1]
        self._updated = False
    if frame:
      frame = convert_pdb_string_to_framedata(frame)
      self._frame_publisher.send_frame(0, frame)

  def _realtime_playback(self) -> None:
    while self._new_frames:
      self._send_last_frame()

  def realtime_playback(self) -> None:
    if self._thread:
      if self._thread.done():
        self._reset_bools()
        self._thread = self._thread_pool.submit(self._realtime_playback)
    else:
      self._reset_bools()
      self._thread = self._thread_pool.submit(self._realtime_playback)

  def cancel_realtime(self) -> None:
    with self._lock:
      self._new_frames = False
      self._stop = True

  ################################################################
  ################### For playing saved frames ###################
  ################################################################

  def step(self) -> None:
    self._frame_publisher.send_frame( self.frame_id, self.stored_frames[self.frame_id] )
    self.frame_id = ( self.frame_id + 1) % len(self.stored_frames)

  def reset(self) -> None:
    with self._lock:
      self.frame_id = 0

  def _play(self) -> None:
    if self.stored_frames and not self._new_frames:
      while not self._stop:
        if not self._pause:
          self.step()
        sleep(1 / self.user_fps)

  def play_saved(self) -> None:
    with self._lock:
      self._stop = False
      self._pause = False
    if self._thread:
      if self._thread.done():
        self._thread = self._thread_pool.submit(self._play)
    else:
      self._thread = self._thread_pool.submit(self._play)

  def cancel(self) -> None:
    with self._lock:
      self._stop = True

  def pause(self) -> None:
    with self._lock:
      self._pause = True

  ################################################################
  #####################  Utility functions   #####################
  ################################################################

  def get_current_frame(self) -> str:
    """
    Gets the pdb of the frame as indicated by the current frame_id.

    :return pdb_string: String corresponding to the pdb of the current frame.
    """
    return self.stored_frames[self.frame_id]

  def send_current_frame(self) -> None:
    if self.stored_frames:
      frame = self.stored_frames[self.frame_id]
    frame = convert_pdb_string_to_framedata(frame)
    self._frame_publisher.send_frame(0, frame)