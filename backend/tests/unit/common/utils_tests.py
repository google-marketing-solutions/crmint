"""Tests for common.utils."""

from absl.testing import absltest
from absl.testing import parameterized

from common import utils


class CommonUtilsTest(parameterized.TestCase):

  @parameterized.named_parameters(
      ('Different types', 'abc', 1, True),
      ('Same strings', 'abc', 'abc', False),
      ('Different strings', 'abc', 'def', True),
      ('Empty lists', [], [], False),
      ('Different length lists', [], ['abc'], True),
      ('Same lists', ['abc'], ['abc'], False),
      ('Different lists', ['abc'], ['def'], True),
      ('Same nested struct', {'a': {'b': 'c'}}, {'a': {'b': 'c'}}, False),
      ('Different nested struct', {'a': {'b': 'c'}}, {'a': {'b': 'd'}}, True),
      ('Missing top level key', {'a': {'b': 'c'}}, {'a': 'b'}, True),
      ('Missing nested level key', {'a': {'b': 'c'}}, {'a': {'c': 'd'}}, True),
      ('Same nested list', {'a': {'b': [1, 2]}}, {'a': {'b': [1, 2]}}, False),
      ('Different nested list', {'a': [1, 2]}, {'a': [3, 4]}, True),
      ('Partial patch without update', {'b': 2}, {'a': 1, 'b': 2}, False),
      ('Partial patch with update', {'b': 3}, {'a': 1, 'b': 2}, True),
      ('Partial patch with nested list', [{'b': 3}], [{'a': 1, 'b': 2}], True),
  )
  def test_detect_patch_update(self, patch, target, expected_result):
    self.assertEqual(utils.detect_patch_update(patch, target), expected_result)


if __name__ == '__main__':
  absltest.main()
