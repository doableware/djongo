# Django MongoDB connector design document

## SQL to MongoDB query mapping.

SQL query | pymongo API
----------|------------
SELECT | find(projection=)
WHERE | find(filter=)
AND | $and
OR | $or
NOT | $neq
IN | $in
INNER JOIN | find(), find(), find()
LEFT JOIN | aggregate($lookup)
UPDATE | update_many
DELETE | delete_many
INSERT INTO | insert_many
CREATE DATABASE | implicit
ALTER DATABASE | implicit
CREATE TABLE | implicit
ALTER TABLE | implicit
DROP TABLE | drop_collection
CREATE INDEX | create_indexes
DROP INDEX | drop_index

## Performing relational JOIN in MongoDB

Since MongoDB does not have an intrinsic JOIN command the multi-collection JOIN must be done at the application layer. Due to the intrinsic design of MongoDB, if a parallel thread does an update operation on the **same set of documents** on which JOIN is taking place, there is a possibility of getting different results than expected. This possibility exists in multi-threaded SQL implementations as well. 

Application layer multi-collection JOINS without any interleaved updates are completely thread safe and can be done in MongoDB. 

INNER JOIN can be done using three application level find operations in pymongo.

LEFT JOIN can be done using a single aggregation lookup operation.


<script>
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');

  ga('create', 'UA-75159067-1', 'auto');
  ga('send', 'pageview');

</script>
