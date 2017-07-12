from sqlparse import parse, tokens
from sqlparse.sql import IdentifierList, Token, \
     Identifier, Parenthesis, Where, Comparison
import re

OPERATOR_MAP = {
   '=': '$eq',
   '>': '$gt',
   '<': '$lt',
   '>=': '$gte',
   '<=': '$lte',
}

OPERATOR_PRECEDENCE = {
   'IN': 1,
   'NOT': 2,
   'AND':3,
   'OR':4,
   'generic':50
}

class SQLObj:
   def __init__(self, field, coll=None):
      self.field = field
      self.coll = coll
      
   @staticmethod   
   def token_2_obj(token):
      if isinstance(token, Identifier):
         yield SQLObj(token.get_name(), token.get_parent_name())          

      elif isinstance(token, IdentifierList):
         for anIden in token.get_identifiers():
            yield from SQLObj.token_2_obj(anIden)
            pass
      
      elif isinstance(token, Comparison):
         lhs = next(SQLObj.token_2_obj(token.left))         
         assert not isinstance(token.right, Identifier)
         op = OPERATOR_MAP[token.token_next(0)[1].value]
         index = int(re.match(r'%\(([0-9]+)\)s', token.right.value, flags=re.IGNORECASE).group(1))
         yield CmpOb( **vars(lhs), operator=op, rhs_obj=params[index] )
      
      elif isinstance(token, Parenthesis):      
         next_id, next_tok = token.token_next(0)
         while next_tok.value != ')': 
            yield from SQLObj.token_2_obj(next_tok)            
            next_id, next_tok = token.token_next(next_id)
      
      else:
         assert False
   
   def to_mongo(self):
      assert False
   

      
class CmpOb(SQLObj):
   def __init__(self, operator, rhs_obj, *args, **kwargs):
      super(CmpOb, self).__init__(*args, **kwargs)
      self.operator = operator
      self.rhs_obj = rhs_obj
      self.is_not = False
      
   def to_mongo(self):
      if not self.is_not:
         return { self.field: { self.operator: self.rhs_obj} }
      else:
         return { self.field: { '$not': {self.operator: self.rhs_obj}}}
      
class Op:
   
   def __init__(self, lhs=None, rhs=None, op_name='generic'):
      self.lhs = lhs
      self.rhs = rhs
      self.is_not = False
      self._op_name = op_name
      self.precedence = OPERATOR_PRECEDENCE[op_name]    
      
   @staticmethod
   def token_2_op(token):
      def resolve_token( token):
         print ('resolving token: {}'.format(token.value))
         def helper():
            nonlocal lhs_obj, hanging_obj, next_id, next_tok
            assert hanging_obj
            lhs_obj = hanging_obj
            next_id, next_tok = token.token_next(next_id)
            hanging_obj = {'obj':next_tok}           
                     
         
         next_id, next_tok = token.token_next(0)
         hanging_obj = {}
         lhs_obj={}
         while next_id:
            if next_tok.match(tokens.Keyword, 'AND'):
               helper()          
               yield AndOp(lhs=lhs_obj, rhs=hanging_obj)         
            
            elif next_tok.match(tokens.Keyword, 'OR'):
               helper()          
               yield OrOp(lhs=lhs_obj, rhs=hanging_obj)         
            
            elif next_tok.match(tokens.Keyword, 'IN'):
               helper()
               yield InOp(lhs=lhs_tok, rhs=hanging_obj)       
           
            elif next_tok.match(tokens.Keyword, 'NOT'):            
               helper()
               yield NotOp(lhs=lhs_tok, rhs=hanging_obj)
            
            elif next_tok.match(tokens.Keyword, '.*'):
               helper()
               yield Op(lhs=lhs_tok, rhs=hanging_obj)            
               
            elif next_tok.match(tokens.Punctuation, ')'):
               break
            
            else:
               hanging_obj = {'obj':next_tok}            
            next_id, next_tok = token.token_next(next_id)             
      
      
      def op_precedence(operator_obj):
         nonlocal op_list
         if not op_list:
            op_list.append(operator_obj)
            return
         for i in range(len(op_list)):
            if operator_obj.precedence > op_list[i].precedence:
               op_list.insert(i,operator_obj)
               break
         else:
            op_list.insert(i+1,operator_obj)      
      
      op_list = []
      
      for op in resolve_token(token):
         op_precedence(op)
      
      while op_list:
         eval_op = op_list.pop(0)
         eval_op.evaluate()
      return eval_op
         
   def evaluate(self):
      self.lhs['obj'].rhs['obj']=self.rhs['obj']
      self.rhs['obj'].lhs['obj']=self.lhs['obj']
      
   def to_mongo(self):
      assert False
      
         
class AndOp(Op):
   def __init__(self, *args, **kwargs):
      super(AndOp, self).__init__(*args, **kwargs, op_name='AND')
      self._and=[]
      
   def evaluate(self):
      assert self.lhs or self.lhs['obj']
      assert self.rhs or self.rhs['obj']
      if isinstance(self.lhs['obj'], AndOp):
         self._and.extend(self.lhs['obj']._and)      
      elif isinstance(self.lhs['obj'], Op):
         self._and.append(self.lhs['obj'])      
      elif isinstance(self.lhs['obj'], Parenthesis):
         self._and.append(self.token_2_op(self.lhs['obj']))      
      else:
         self._and.append(next(SQLObj.token_2_obj(self.lhs['obj'])))
      
      if isinstance(self.rhs['obj'], AndOp):
         self._and.extend(self.rhs['obj']._and)      
      elif isinstance(self.rhs['obj'], Op):
         self._and.append(self.rhs['obj'])      
      elif isinstance(self.rhs['obj'], Parenthesis):
         self._and.append(self.token_2_op(self.rhs['obj']))      
      else:
         self._and.append(next(SQLObj.token_2_obj(self.rhs['obj'])))
      
      self.lhs['obj'] = self
      self.rhs['obj'] = self
      
   def to_mongo(self):
      if self.is_not is False:
         ret_doc = {'$and': []}
         for itm in self._and:
            ret_doc['$and'].append( itm.to_mongo())
      else:
         ret_doc = {'$or': []}
         for itm in self._and:
            itm.is_not = True
         for itm in self._and:
            ret_doc['$or'].append( itm.to_mongo())
      return ret_doc
         

class OrOp(Op):
   def __init__(self, *args, **kwargs):
      super(OrOp, self).__init__(*args, **kwargs, op_name='OR')
      self._or=[]
      
   def evaluate(self):
      assert self.lhs or self.lhs['obj']
      assert self.rhs or self.rhs['obj']
      if isinstance(self.lhs['obj'], OrOp):
         self._or.extend(self.lhs['obj']._or)      
      elif isinstance(self.lhs['obj'], Op):
         self._or.append(self.lhs['obj'])      
      elif isinstance(self.lhs['obj'], Parenthesis):
         self._or.append(self.token_2_op(self.lhs['obj']))      
      else:
         self._or.append(next(SQLObj.token_2_obj(self.lhs['obj'])))
      
      if isinstance(self.rhs['obj'], OrOp):
         self._or.extend(self.rhs['obj']._or)      
      elif isinstance(self.rhs['obj'], Op):
         self._or.append(self.rhs['obj'])      
      elif isinstance(self.rhs['obj'], Parenthesis):
         self._or.append(self.token_2_op(self.rhs['obj']))      
      else:
         self._or.append(next(SQLObj.token_2_obj(self.rhs['obj'])))
      
      self.lhs['obj'] = self
      self.rhs['obj'] = self
      
   def to_mongo(self):
      if not self.is_not:
         oper = '$or'
      else:
         oper = '$nor'
      
      ret_doc = {oper: []}
      for itm in self._or:
         ret_doc[oper].append( itm.to_mongo())       
      return ret_doc      
      
            



sql = 'SELECT "django_migrations"."app", "django_migrations"."trial"\
FROM  "django_migrations" WHERE ("django_migrations"."app" <=%s AND \
"django_migrations"."trial" >=%s AND "django_migrations"."app" >=%s) OR ("django_migrations"."app" <=%s AND\
"django_migrations"."app" IN (%s,%s))'

sql = 'SELECT "django_migrations"."app", "django_migrations"."trial"\
FROM  "django_migrations" WHERE ("django_migrations"."app" <=%s AND \
"django_migrations"."trial" >=%s AND "django_migrations"."app" >=%s) OR ("django_migrations"."app" <=%s AND \
"django_migrations"."app">%s)'

#sql = 'UPDATE "django_migrations" SET "app"=%s, "main"=%s, "else"=%s'
i=-1
def param_index(x):
   global i
   i=i+1
   return '%({})s'.format(i)

sql = re.sub(r'%s',param_index, sql)

sm = parse(sql)[0]
first_tok = sm.token_first()
print('next of {}'.format(first_tok.value))
nextid, nexttok = sm.token_next(0)
collection = ''
params = [2,3,4,5,6]


#print_token(nexttok)
if nexttok.value == '*':
   projection = {}
else:
   projection = {'_id': False}
   for sql_ob in SQLObj.token_2_obj(nexttok):
      coll = sql_ob.coll
      field = sql_ob.field
      if not collection:
         collection = coll
      else:
         assert collection == coll
      projection.update( {field:True} )
      
nextid, nexttok = sm.token_next(nextid)
assert nexttok.match(tokens.Keyword, 'FROM')

nextid, nexttok = sm.token_next(nextid)
sql_ob = next(SQLObj.token_2_obj(nexttok))
assert collection == sql_ob.field

nextid, nexttok = sm.token_next(nextid)
if nextid and isinstance(nexttok, Where):
   where_op = Op.token_2_op(nexttok)
   pass
   find = where_op.to_mongo()
   

print('main next of {}'.format(nexttok.value))
nextid, nexttok = sm.token_next(nextid)
