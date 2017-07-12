from sqlparse import parse, tokens
from sqlparse.sql import IdentifierList, Token, \
     Identifier, Parenthesis, Where, Comparison
import re

i=0
def print_token(tok):
   global i
   attrs = [key for key in tok.__dir__() if not key.startswith('_')]
   attrs = sorted(attrs)
   print('--'*i,'type: {}, value: {}, attrs: {}, len:{}\n'.format(type(tok),\
                                                   tok.value,attrs, len(attrs)))
   print(tok.value)
   if isinstance(tok, Identifier):
      
      tok.get_parent_name()
   if hasattr(tok,'token_first') and tok.token_first():
      i+=1
      print('deeper of {}, type:{}'.format(tok.value,type(tok)))
      print_token(tok.token_first())
      print('outer of {}, type:{}'.format(tok.value,type(tok)))
      i-=1
   if not hasattr(tok, 'token_next'):
      return
   nextid, nexttok = tok.token_next(0)
   while nextid:
      print('next of i:{}, {}, type:{}'.format(i,tok.value,type(tok)))
      print_token(nexttok)
      nextid, nexttok = tok.token_next(nextid)     

class Evaluate():
   def __init__(self, params):

      self.params = params      
      self.lhs={}
      self.rhs={}      
      self._and, self._or, self.placeholder = [],[],[]
      self._in = {}
   
   def evaluate(self, token):
      if isinstance(token, Identifier):
         yield (token.get_parent_name(), token.get_name())          

      elif isinstance(token, IdentifierList):
         for anIden in token.get_identifiers():
            yield from self.evaluate(anIden)
            pass
      
      elif isinstance(token, Comparison):
         coll, field = next(self.evaluate(token.left))
         operator = token.token_next(0)[1].value
         if operator == '=':
            ret = {field:next(self.params)}
         else:
            assert False
         yield ret
      
      elif isinstance(token, Parenthesis):      
         next_id, next_tok = token.token_next(0)
        # assert not self.lhs, 'There shd be no returened docs'
        # eval_obj = Evaluate(self.params)
         while next_id: 
            yield from self.evaluate(next_tok)            
            next_id, next_tok = token.token_next(next_id)
      
      else:
         assert False   
   
   def concat(self):
      if self._and:
         self._and.append(self.lhs)
         ret = { '$and': self._and }
         self._and = []         
      elif self._or:
         self._or.append(self.lhs)
         ret = {'$or': self._or }
         self._or = []         
      elif self._in:
            # self._in.append(self.lhs)
         ret = { self._in['field']:{'$in': self.placeholder} }
         self._in = None 
         self.placeholder = None
      elif self.placeholder:
         ret = self.placeholder
         self.placeholder = None
      else:
         assert False
      
      self.lhs={}   
      return ret         
     
   def evaluate_where(self, token):   
      if isinstance(token, Identifier):
         yield (token.get_parent_name(), token.get_name())          

      elif isinstance(token, IdentifierList):
         for anIden in token.get_identifiers():
            yield from self.evaluate_where(anIden)
            pass
      
      elif isinstance(token, Comparison):
         coll, field = next(self.evaluate_where(token.left))
         operator = token.token_next(0)[1].value
         if operator == '=':
            ret = {field:next(self.params)}
         else:
            ret = {field:{OPERATOR_MAP[operator]:next(self.params)}}
         yield ret
      
      elif isinstance(token, Parenthesis):      
         next_id, next_tok = token.token_next(0)
         assert not self.lhs, 'There shd be no returened docs'
         eval_obj = Evaluate(self.params)
         while next_id: 
            for returned_obj in (eval_obj.evaluate_where(next_tok)):               
               if isinstance(returned_obj, dict):
                  eval_obj.lhs.update(returned_obj)
               elif isinstance(returned_obj, tuple):
                  eval_obj.field = returned_obj[1]
               elif isinstance(returned_obj, list):
                  eval_obj.placeholder = returned_obj
               else:
                  eval_obj.placeholder.append(returned_obj)
            next_id, next_tok = token.token_next(next_id)         
         yield eval_obj.concat()  
         
      elif isinstance(token, Token):
         if token.match(tokens.Keyword, 'AND'):
            assert len(self.lhs) == 1
            self._and.append(self.lhs)
            self.lhs = {}
         elif token.match(tokens.Keyword, 'OR'):
            assert len(self.lhs) == 1
            self._or.append(self.lhs)
            self.lhs = {}
         elif token.match(tokens.Keyword, 'IN'):
            assert self.field
            self._in['field']= self.field
            self.field = None
            pass
         elif token.match(tokens.Name.Placeholder, '%s'):
            yield next(self.params)
         yield {}
         
      else:
         print('type:{}'.format(type(token)))
         pass

   def _where(self, token):
      whr_nxt_id, whr_nxt_tok = token.token_next(0)
      while whr_nxt_id:      
         self.lhs = next(ut.evaluate_where(whr_nxt_tok))
         whr_nxt_id, whr_nxt_tok = token.token_next(whr_nxt_id)      
         
sql = 'SELECT "auth_permission"."content_type_id" FROM "auth_permission"\
INNER JOIN "django_content_type" ON ("auth_permission"."content_type_id" = "django_content_type"."id")\
WHERE "auth_permission"."content_type_id" NOT IN (%(0)s, %(1)s)\
ORDER BY "django_content_type"."app_label" ASC, "django_content_type"."model" ASC, "auth_permission"."codename" ASC'

sm = parse(sql)[0]
first_tok = sm.token_first()
print('next of {}'.format(first_tok.value))

nextid, nexttok = sm.token_next(0)
while nextid:
   print_token(nexttok)
   nextid, nexttok = sm.token_next(nextid)


