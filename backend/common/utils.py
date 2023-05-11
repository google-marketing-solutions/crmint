"""Generic utilities."""

from typing import Any, Callable, Iterable, Optional, TypeVar

T = TypeVar('T')


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


def first(iterable: Iterable[T],
          condition: Callable[[T], bool] = lambda x: True,
          default: Optional[T] = None) -> T:
  """Returns the first item in the `iterable` that satisfies the `condition`.

  If the condition is not given, returns the first item of
  the iterable.

  If the `default` argument is given and the iterable is empty,
  or if it has no items matching the condition, the `default` argument
  is returned if it matches the condition.

  The `default` argument being None is the same as it not being given.

  Raises `StopIteration` if no item satisfying the condition is found
  and default is not given or doesn't satisfy the condition.

  Args:
    iterable: List of elements.
    condition: Condition to test elements on.
    default: Optional default value.
  """
  try:
    return next(x for x in iterable if condition(x))
  except StopIteration:
    if default is not None and condition(default):
      return default
    else:
      raise
