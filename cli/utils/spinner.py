"""Defines methods to create a spinning wheel on stdout."""

import itertools
import sys
import threading
import time
from typing import Optional

import click


class Spinner(object):
  """Implements a context manager to display a spinner on stdout.

  Inspired from https://github.com/click-contrib/click-spinner
  """
  spinner_cycle = itertools.cycle(['-', '/', '|', '\\'])

  def __init__(self,
               beep: bool = False,
               disable: bool = False,
               force: bool = False,
               color: str = None,
               bold: bool = False):
    self.disable = disable
    self.beep = beep
    self.force = force
    self.color = color
    self.bold = bold
    self.stop_running = None
    self.spin_thread = None

  def start(self):
    if self.disable:
      return
    if sys.stdout.isatty() or self.force:
      self.stop_running = threading.Event()
      self.spin_thread = threading.Thread(target=self.init_spin)
      self.spin_thread.start()

  def stop(self):
    if self.spin_thread:
      self.stop_running.set()
      self.spin_thread.join()

  def init_spin(self):
    sys.stdout.write(click.style(' ', fg=self.color, bold=self.bold))
    while not self.stop_running.is_set():
      sys.stdout.write(
          click.style(next(self.spinner_cycle), fg=self.color, bold=self.bold))
      sys.stdout.flush()
      time.sleep(0.25)
      sys.stdout.write('\b')
      sys.stdout.flush()

  def __enter__(self):
    self.start()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    if self.disable:
      return False
    self.stop()
    if self.beep:
      sys.stdout.write('\7')
      sys.stdout.flush()
    else:
      sys.stdout.write(' ')
      sys.stdout.write('\N{check mark}')
      sys.stdout.flush()
    return False


def spinner(beep: bool = False,
            disable: bool = False,
            force: bool = False,
            color: Optional[str] = None,
            bold: bool = False) -> Spinner:
  """Returns a context manager that is used to display a spinner.

  The spinner is created only if stdout is not redirected, or if the spinner
  is forced using the `force` parameter.

  The spinner will stop when the context has exited.

  Example:

    with spinner():
      do_something()
      do_something_else()

  Args:
    beep: Beep when spinner finishes.
    disable: Hides spinner.
    force: Force creation of spinner even when stdout is redirected.
    color: Color of the spinning wheel.
    bold: Draws the spinning wheel in bold.
  """
  return Spinner(beep, disable, force, color=color, bold=bold)
