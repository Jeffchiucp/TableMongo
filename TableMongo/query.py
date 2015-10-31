""" LOCAL IMPORTS """
from .properties import Property, PropertyQuery, SortDescriptor
from .key import Key
import pymongo


class InvalidSortDescriptor(Exception):
  pass


# TODO once used the query iterator is done


class Query(object):
  """
  ' PURPOSE
  '   Is a form of lazy-loading for database queries.
  '   AKA provides iterators and helpful sorting and fetching
  '   actions that don't load memory until needed.
  """
  
  def __init__(self, model, logic_chain):
    """
    ' PURPOSE
    '   Construct the class with the given model and query
    '   logic chain.
    ' PARAMETERS
    '   <Model model>
    '   <LogicOperator logic_chain>
    ' RETURNS
    '   <Query query>
    """
    self._model = model
    self._logic_chain = logic_chain
    self._query = self._query()
  
  def _query(self):
    """
    ' PURPOSE
    '   Loads a pymongo cursor based on the given logic chain's bson.
    ' PARAMETERS
    '   None
    ' RETURNS
    '   <Iterator cursor>
    """
    collection = self._model._collection()
    bson = self._logic_chain.bson(self._model)
    cursor = collection.find(bson, projection={ '_id':1 })
    return cursor
  
  def filter(self, *args):
    """
    ' PURPOSE
    '   Combines the logic chain for this query with a new logic chain
    '   and returns the new resulting query object.
    ' PARAMETERS
    '   <PropertyQuery prop_query1>
    '   <PropertyQuery prop_query2>
    '   ...
    '   <PropertyQuery prop_queryN>
    ' RETURNS
    '   <Query query>
    """
    new_login_chain = AND(self.logic_chain, *args)
    return Query(self._model, new_login_chain)
  
  def fetch(self, offset=0, count=0, keys_only=False):
    """
    ' PURPOSE
    '   Returns a subsection of the queried models.
    ' PARAMETERS
    '   <int offset>
    '   <int count>
    '   <bool keys_only>
    ' RETURNS
    '   <list Key key> if keys_only
    '   <list Model model> if not keys_only
    """
    subsection = self._query[offset:offset+count]
    if keys_only:
      return [Key(self._model, str(document['_id'])) for document in subsection]
    return [Key(self._model, str(document['_id'])).get() for document in subsection]
  
  def count(self):
    """
    ' PURPOSE
    '   Returns the count of entities matched by this query.
    ' PARAMETERS
    '   NONE
    ' RETURNS
    '   <int count>
    """
    return self._query.count()
  
  def get(self, keys_only=False):
    """
    ' PURPOSE
    '   Returns the first model in this query or None if there
    '   isn't one.
    ' PARAMETERS
    '   <bool keys_only>
    ' RETURNS
    '   <Key key> if keys_only
    '   <Model model> if not keys_only
    """
    if self.count() == 0:
      return None
    
    key = Key(self._model, str(self._query[0]['_id']))
    if keys_only:
      return key
    return key.get()
  
  def order(self, sort_descriptor):
    if isinstance(sort_descriptor, Property):
      sort_descriptor = +sort_descriptor
    elif not isinstance(sort_descriptor, SortDescriptor):
      raise InvalidSortDescriptor()
    # TODO write this method
  
  def __iter__(self, *args, **kwargs):
    """
    ' PURPOSE
    '   Allows this class to be iterable by delegating to the iter
    '   method.
    ' NOTES
    '   1. see self.iter
    """
    return self.iter(*args, **kwargs)
  
  def iter(self, keys_only=False):
    """
    ' PURPOSE
    '   Is a generator that iterates over all entities matched by
    '   this query.
    ' PARAMETERS
    '   <bool keys_only>
    ' RETURNS
    '   <Key key> if keys_only
    '   <Model model> if not keys_only
    """
    for document in self._query:
      key = Key(self._model, str(document['_id']))
      if keys_only:
        yield key
      yield key.get()


class LogicOperator(object):
  pass


class AND(LogicOperator):
  """
  ' PURPOSE
  '   Concatinates many property queries into a
  '   single and statement.
  ' EXAMPLE USAGE
  '   -> db.AND(User.email == 'john@doe.com', User.age < 25)
  """
  
  def __init__(self, *partialqueries):
    """
    ' PURPOSE
    '   Initializes the AND with given property queries.
    ' PARAMETERS
    '   <PropertyQuery propquery1>
    '   <PropertyQuery propquery2>
    '   ...
    '   <PropertyQuery propqueryN>
    ' RETURNS
    '   <AND and>
    ' NOTES
    '   1. May also take LogicOperator objects as arguments.
    """
    self._bson = None
    self._partialqueries = partialqueries
  
  def bson(self, modelcls):
    # TODO make each property aware of it's name
    """
    ' PURPOSE
    '   Given a Model subclass class. Convert the property queries
    '   into a PyMongo compatible BSON query.
    '   * see https://docs.mongodb.org/manual/reference/operator/query/ *
    ' PARAMETERS
    '   <class MyModel extends Model>
    ' RETURNS
    '   <dict bson>
    ' NOTES
    '   1. Caches the result (memoize)
    """
    if not self._partialqueries: return {}
    if self._bson: return self._bson
    
    attr_map = {}
    
    for attr in vars(modelcls):
      val = getattr(modelcls, attr)
      if isinstance(val, Property):
        attr_map[val] = attr
    
    self._bson = { '$and': [] }
    and_query = self._bson['$and']
    
    for partialquery in self._partialqueries:
      if isinstance(partialquery, PropertyQuery):
        and_query.append({
          attr_map[partialquery.property]: {
            partialquery.operator: partialquery.property._pack(partialquery.value)
          }
        })
      elif isinstance(partialquery, LogicOperator):
        and_query.append(partialquery.bson(modelcls))
    
    return self._bson


class OR(LogicOperator):
  """
  ' PURPOSE
  '   Concatinates many property queries into a
  '   single or statement.
  ' EXAMPLE USAGE
  '   -> db.OR(User.email == 'john@doe.com', User.age < 25)
  """
  
  def __init__(self, *partialqueries):
    """
    ' PURPOSE
    '   Initializes the OR with given property queries.
    ' PARAMETERS
    '   <PropertyQuery propquery1>
    '   <PropertyQuery propquery2>
    '   ...
    '   <PropertyQuery propqueryN>
    ' RETURNS
    '   <OR or>
    ' NOTES
    '   1. May also take LogicOperator objects as arguments.
    """
    self._bson = None
    self._partialqueries = partialqueries
  
  def bson(self, modelcls):
    """
    ' PURPOSE
    '   Given a Model subclass class. Convert the property queries
    '   into a PyMongo compatible BSON query.
    '   * see https://docs.mongodb.org/manual/reference/operator/query/ *
    ' PARAMETERS
    '   <class MyModel extends Model>
    ' RETURNS
    '   <dict bson>
    ' NOTES
    '   1. Caches the result (memoize)
    """
    if not self._partialqueries: return {}
    if self._bson: return self._bson
    
    attr_map = {}
    
    for attr in vars(modelcls):
      val = getattr(modelcls, attr)
      if isinstance(val, Property):
        attr_map[val] = attr
    
    self._bson = { '$or': [] }
    or_query = self._bson['$or']
    
    for partialquery in self._partialqueries:
      if isinstance(partialquery, PropertyQuery):
        or_query.append({
          attr_map[partialquery.property]: {
            partialquery.operator: partialquery.property._pack(partialquery.value)
          }
        })
      elif isinstance(partialquery, LogicOperator):
        or_query.append(partialquery.bson(modelcls))
    
    return self._bson