# Integrating Django with MongoDB

This document is a tutorial on how to integrate MongoDB with Django. It describes the Django ORM internal implementation that is not covered by the [Django documentation](https://docs.djangoproject.com/en/dev/). There are different ways to integrate MongoDB with Django, each with positives and negatives.

Insights into the Django ORM design will help in understanding ways to integrate MongoDB and Django.     

## Django ORM internals

The Django ORM can be broadly thought of as multiple Abstraction Layers stacked on top of each other.

![Abstraction Layers](/images/layers.svg)

### User Layer

### SQL Layer

### Database Layer


## Django ORM operations

### lookup

### filter

### etc


## A common misconception 

### Relational data cannot be represented within a non relational data-store

### Unstructured data is a super set of structured data 


## Ways to integrate Django with MongoDB

### From ORM to ODM

### MongoEngine

### Django-non-rel

### django-mongo-engine

### Django SQL transpiler
 Is it efficient? Nope
 

## SQL to MongoDB query mapping. 