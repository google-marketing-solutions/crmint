# Copyright 2018 Google Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Base class for all our models.

The mixin classes are inspired by SQLAlchemy-Mixins, which itself was heavily
inspired by Django ORM and Eloquent ORM.

Source: https://github.com/absent1706/sqlalchemy-mixins
License: MIT
"""

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import func
from sqlalchemy import inspect
from sqlalchemy import orm
from sqlalchemy import sql

_OPERATOR_SPLITTER = "__"


class TimestampsMixin(object):
  created_at = Column(DateTime, nullable=False, default=func.now())
  updated_at = Column(
      DateTime,
      nullable=False,
      onupdate=func.now(),
      default=func.now()
  )


class classproperty:  # pylint: disable=invalid-name
  """Minimalistic class property implementation.

  Decorator that converts a method with a single cls argument into a property
  that can be accessed directly from the class.
  """

  def __init__(self, method=None):
    self.fget = method

  def __get__(self, instance, cls=None):
    return self.fget(cls)

  def getter(self, method):
    self.fget = method
    return self


class InspectionMixin:
  """Introspection helpers."""

  @classproperty
  def columns(cls):  # pylint: disable=no-self-argument
    return inspect(cls).columns.keys()

  @classproperty
  def relations(cls):  # pylint: disable=no-self-argument
    """Returns a list of relationship names or the given model."""
    return [c.key for c in cls.__mapper__.iterate_properties
            if isinstance(c, orm.RelationshipProperty)]

  @classproperty
  def settable_relations(cls):  # pylint: disable=no-self-argument
    """Returns a `list` of relationship names or the given model."""
    return [r for r in cls.relations if not getattr(cls, r).property.viewonly]


class SessionMixin:
  """Session helpers."""
  _session = None

  @classmethod
  def set_session(cls, session):
    """Binds the model to a given session."""
    cls._session = session

  @classproperty
  def session(cls):  # pylint: disable=no-self-argument
    if cls._session is not None:
      return cls._session
    else:
      raise ValueError("Cant get session. "
                       "Please, call db.Model.set_session()")


class ActiveRecordMixin(InspectionMixin, SessionMixin):
  """Mixin combining Django-like helpers."""

  @classproperty
  def settable_attributes(cls):  # pylint: disable=no-self-argument
    return cls.columns + cls.settable_relations

  def fill(self, **kwargs):
    for name in kwargs:
      if name in self.settable_attributes:
        setattr(self, name, kwargs[name])
      else:
        raise KeyError("Attribute '{}' doesn't exist".format(name))

    return self

  def save(self):
    """Saves the updated model to the current entity db."""
    self.session.add(self)
    self.session.commit()
    return self

  @classmethod
  def create(cls, **kwargs):
    """Creates a new record and insert it into the database.

    Args:
      **kwargs: Attributes to create a new record with.

    Returns:
      The new Model.
    """
    return cls().fill(**kwargs).save()

  def update(self, **kwargs):
    """Persists changes to the database."""
    return self.fill(**kwargs).save()

  def delete(self):
    """Removes the model from the current entity session and mark for deletion.
    """
    self.session.delete(self)
    self.session.commit()

  @classmethod
  def destroy(cls, *ids):
    """Deletes the records with the given ids.

    Args:
      *ids: Primary key ids of records.
    """
    for pk in ids:
      obj = cls.find(pk)
      if obj:
        obj.delete()
    cls.session.flush()

  @classmethod
  def all(cls):
    return cls.query.all()

  @classmethod
  def first(cls):
    return cls.query.first()

  @classmethod
  def find(cls, id_):
    """Returns the record fetched for the given id.

    Args:
      id_: The primary key.
    """
    return cls.query.get(id_)


class ReprMixin:
  """Replicates the Django-like __repr__ behavior."""

  __repr_attrs__ = []
  __repr_max_length__ = 15

  @property
  def _id_str(self):
    ids = inspect(self).identity
    if ids:
      return "-".join([str(x) for x in ids]) if len(ids) > 1 else str(ids[0])
    else:
      return "None"

  @property
  def _repr_attrs_str(self):
    """Formats attributes for printing a representation of this object."""
    max_length = self.__repr_max_length__

    values = []
    single = len(self.__repr_attrs__) == 1
    for key in self.__repr_attrs__:
      if not hasattr(self, key):
        raise KeyError("{} has incorrect attribute '{}' in "
                       "__repr__attrs__".format(self.__class__, key))
      value = getattr(self, key)
      wrap_in_quote = isinstance(value, str)

      value = str(value)
      if len(value) > max_length:
        value = value[:max_length] + "..."

      if wrap_in_quote:
        value = "'{}'".format(value)
      values.append(value if single else f"{key}:{value}")

    return " ".join(values)

  def __repr__(self):
    # get id like '#123'
    id_str = ("#" + self._id_str) if self._id_str else ""
    # join class name, id and repr_attrs
    class_name = self.__class__.__name__
    repr_attrs = " " + self._repr_attrs_str if self._repr_attrs_str else ""
    return f"<{class_name} {id_str}{repr_attrs}>"


class SmartQueryMixin:
  """Replicates the Django-like filtering helpers."""

  # Supported operators using the Django-like syntax "<attr_name>__<op_name>".
  _operators = {
      "in": sql.operators.in_op,
  }

  @classproperty
  def filterable_attributes(cls):  # pylint: disable=no-self-argument
    return cls.relations + cls.columns

  @classmethod
  def where(cls, **filters):
    """Returns filtered entities matching the given filters.

    Example 1:
      Product.where(subject_id__in=[1, 2], grade_from_id=2).all()
    Example 2:
      filters = {'subject_id__in': [1, 2], 'grade_from_id': 2}
      Product.where(**filters).all()

    Args:
      **filters: List of filtering conditions.

    Raises:
      KeyError: if the operator is not supported or if the attribute is
        not filterable.
    """
    conditions = []
    valid_attributes = cls.filterable_attributes
    for attr, value in filters.items():
      if _OPERATOR_SPLITTER in attr:
        attr_name, op_name = attr.rsplit(_OPERATOR_SPLITTER, 1)
        if op_name not in cls._operators:
          raise KeyError(f"Expression `{attr}` has incorrect "
                         f"operator `{op_name}`")
        op = cls._operators[op_name]
      else:
        # Assumes equality operator for other cases.
        attr_name, op = attr, sql.operators.eq

      if attr_name not in valid_attributes:
        raise KeyError(f"Expression `{attr}` "
                       f"has incorrect attribute `{attr_name}`")

      column = getattr(cls, attr_name)
      conditions.append(op(column, value))
    return cls.query.filter(*conditions)


class AllFeaturesMixin(ActiveRecordMixin, SmartQueryMixin, ReprMixin):
  __repr__ = ReprMixin.__repr__
