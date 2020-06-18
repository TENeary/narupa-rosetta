# Copyright (c) Tim Neary, University of Bristol. Github username: TENeary, contact: tn15550@bristol.ac.uk
# Licensed under the GPL. See License.txt in the project root for license information.

from narupa.trajectory.frame_publisher import FramePublisher
from threading import RLock
from concurrent import futures
from time import sleep

class TrajectoryManager:
  """
  Initialise playback, setting things up.
  """
  # Get a pool of threads (just one) that we can run the play back on
  def __init__( self,
                frame_publisher : FramePublisher,
                all_frames : list = None,
                fps : int = 15 ): # Todo add in-progress viewer as well as just saved frames
    self.threads = futures.ThreadPoolExecutor(max_workers=1)
    self._run_task = None
    self._cancelled = False
    self._cancel_lock = RLock()
    self.frame_index = 0
    self.fps = fps
    self.frame_publisher = frame_publisher
    self.frames = all_frames

  @property
  def is_running( self ):
    # Fancy logic that just checks whether or not we're playing the trajectory in the background
    return self._run_task is not None and not (self._run_task.cancelled() or self._run_task.done())

  def new_frames( self,
                  new_frames : list ):
    """
    Overwrites old frames with the new list of frames. To allow frames to be viewed.

    :param new_frames: List of frames to be used for the newest trajectory viewing
    """
    self.cancel_playback()
    self.frames = new_frames

  def play( self ):
    """
    Plays the trajectory in the background.
    """
    # First, we have to cancel any existing playback, and start a new one.
    with self._cancel_lock:
      self.cancel_playback(wait=True)
    self.run_playback()

  def step( self ):
    """
    Take a single step of the trajectory and stop.
    """
    # The lock here ensures only one person can cancel at a time.
    with self._cancel_lock:
      self.cancel_playback(wait=True)
      self._step_one_frame()

  def pause( self ):
    """
    Pause the playback, by cancelling any current playback.
    """
    with self._cancel_lock:
      self.cancel_playback(wait=True)

  def run_playback( self,
                    block=False ):
    """
    Runs the trajectory playback. If block is False, it will run on a background thread.
    """
    if self.is_running:
      raise RuntimeError("The trajectory is already playing on a thread!")
    if block:
      self._run()
    else:
      self._run_task = self.threads.submit(self._run)

  def _run( self ):
    if self.frames:
      while not self._cancelled:
        self._step_one_frame()
        sleep( 1 / self.fps) # Delay sending frames so we hit the desired FPS
    self._cancelled = False


  def _step_one_frame( self ):
    self.frame_publisher.send_frame( self.frame_index, self.frames[self.frame_index] )
    self.frame_index = (self.frame_index + 1) % len(self.frames)

  def cancel_playback( self,
                       wait=False ):
    """
    Cancel trajectory playback, if it's running. If wait is True, this method will wait until the playback stops
    before returning.
    """
    if self._run_task is None:
      return
    if self._cancelled:
      return

    self._cancelled = True
    if wait:
      self._run_task.result()
      self._cancelled = False

  def reset( self ):
    self.frame_index = 0