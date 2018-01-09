# How to contribute to this project ?


## Adding support for new operators


As a starter, all the operators mentioned in [#39][iexact...] can be implemented using MongoDB regex operators.

Take a look at [djongo/base.py][base] call that inherits from Django's
`BaseDatabaseWrapper`.

Django operators (eg., `exact `, `contains `, etc.) will have to be mapped to 
any other keyword (You can decide what keyword you want to map it to, for 
now it maps to default SQL keywords of `LIKE`, `REGEXP`)

Next, in [sql2mongo.py][sql2mongo] define a new `Op ` class and do the needful.


The branch [iexact_support][iexact] has this implementation partially underway.


[iexact...]: https://github.com/nesdis/djongo/issues/29
[base]: https://github.com/nesdis/djongo/blob/master/djongo/base.py
[sql2mongo]: https://github.com/nesdis/djongo/blob/master/djongo/sql2mongo.py
[iexact]: https://github.com/nesdis/djongo/tree/iexact_support
