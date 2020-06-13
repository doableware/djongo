---
permalink: /
layout: splash
title: "Django MongoDB connector"
excerpt: "Djongo"
description: "Djongo is a python connector for using the Django ORM with MongoDB. Use Django Admin to directly add and modify documents stored in MongoDB. Use other contrib modules such as Auth and Sessions without any changes"

header:
    overlay_image: /assets/images/landing-banner3.jpg

punchline:
  - excerpt: A python Object Document Mapper (ODM) that let's you use Django with MongoDB *without* changing the Django ORM.

feature_row1:

  - image_path: /assets/images/support.png
    alt: "Support"
    title: "Support"
    excerpt: "Get immediate support for queries on using Django with MongoDB."
    url: https://www.patreon.com/nesdis/
    btn_label: "Learn More"
    btn_class: "btn--primary"

  - image_path: /assets/images/mongo.jpg
    alt: "Unleash MongoDB on Django"
    title: "Unleash MongoDB On Django"
    excerpt: "Create MongoDB [embedded documents,](/using-django-with-mongodb-data-fields/) 
    [embedded arrays](/using-django-with-mongodb-array-field/) in Django Models,
    [MongoDB specific indexes](/djongonxt-indexes/) and [transactions.](/djongonxt-database-transactions/)"

  - image_path: /assets/images/feature-admin-mongo.jpg
    alt: "Admin MongoDB"
    title: "Access MongoDB Through Django Admin"
    excerpt: "Use Django Admin GUI to insert, modify and delete documents in MongoDB."

feature_row2:

  - image_path: /assets/images/django.jpg
    alt: "Security"
    title: "Security"
    excerpt: "Since there are **zero modifications** to the Django source code, 
    you get complete security and reliability of Django."
    
  - image_path: /assets/images/djongo-symbol2.jpg
    alt: "Admin MongoDB"
    title: "Rapid App Development"
    excerpt: "Speed up app development and execution with [schema free models](integrating-django-with-mongodb/#enforce-schema), 
    skipping migrations, and reducing two query intermediate joins to single query [direct joins.](/using-django-with-mongodb-array-reference-field/)"
    
  - image_path: /assets/images/drf.jpg
    alt: "Admin MongoDB"
    title: "Sweet Third Party Package Support"
    excerpt: "Extra goodies that help interface MongoDB with Django Rest Framework."        
    
addendum_row1:
  - image_path: /assets/images/djongo-Nxt-v1.png
    alt: "Djongo Next"
    title: "Djongo Next"
    excerpt: "The next generation connector. Ships with binary extensions for professional usage."
    url: https://www.patreon.com/nesdis
    btn_label: "Learn More"
    btn_class: "btn--primary"
---


{% include feature_row id="punchline" type="center" %}

{% include feature_row id="feature_row1" %}

{% include feature_row id="feature_row2" %}

{% include feature_row id="addendum_row1" type="center" %}

