"""Generic utilities."""

from typing import Any


def detect_patch_update(patch: Any, target: Any) -> bool:
  """Returns True if the patch structure could change the target structure.

  The two arguments should be data trees consisting of trees of dicts and
  lists. They will be deeply compared by walking into the contents of dicts
  and lists. Other items will be compared using the == operator.

  Args:
    patch: A structure to update the target with.
    target: A structure receiving the patch updates.
  """
  if type(patch) is not type(target):
    return True

  if isinstance(patch, dict):
    new_keys = set(patch.keys()).difference(target.keys())
    if new_keys:
      return True
    for k in patch:
      if detect_patch_update(patch[k], target[k]):
        return True
  elif isinstance(patch, (list, tuple, set)):
    if len(patch) != len(target):
      return True
    for patch_i, target_i in zip(patch, target):
      if detect_patch_update(patch_i, target_i):
        return True
  elif patch != target:
    return True

  return False
