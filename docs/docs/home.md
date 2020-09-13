---
permalink: /
layout: splash
title: "Python ODM for MongoDB"
excerpt: 
description: "Djongo is a python connector for using the Django ORM with MongoDB. Use Django Admin to directly add and modify documents stored in MongoDB. Use other contrib modules such as Auth and Sessions without any changes"

header:
    overlay_image: /assets/images/landing-banner3.jpg

punchline:
  - excerpt: A python Object Document Mapper (ODM) for MongoDB.

feature_row1:
  - image_path: /assets/images/django.jpg
    alt: "Security"
    title: "Security"
    excerpt: "Djongo adds functionality to the popular Django ORM. There are zero modifications 
    to the original source code. You inherit the security and reliability of Django."
    
  - image_path: /assets/images/mongo.jpg
    alt: "Unleash MongoDB on Django"
    title: "Simplify Query Creation"
    excerpt: "Create [embedded documents](/djongo/using-django-with-mongodb-data-fields/) 
     and [arrays](/djongo/using-django-with-mongodb-array-field/) within a model,
    MongoDB specific [indexes](/djongo/djongonxt-indexes/), [transactions](djongonxt-database-transactions/),
    and much more."

  - image_path: /assets/images/feature-admin-mongo.jpg
    alt: "Admin MongoDB"
    title: "Web interface"
    excerpt: "Use Django Admin to access, insert, modify and delete documents in MongoDB."

  - image_path: /assets/images/support.png
    alt: "Support"
    title: "Support"
    excerpt: "Get immediate support for queries on using Django with MongoDB."
    url: https://nesdis.github.io/djongo/sponsor/
    btn_label: "Learn More"
    btn_class: "btn--primary"
    
  - image_path: /assets/images/djongo-symbol2.jpg
    alt: "Admin MongoDB"
    title: "Rapid Prototyping"
    excerpt: "Speed up app development and execution with [schema free models](/djongo/get-started/#enforce-schema), 
    skipping migrations, and autogenerate [complex queries](/djongo/using-django-with-mongodb-array-reference-field/)."    
  - image_path: /assets/images/drf.jpg
    alt: "Admin MongoDB"
    title: "Third Party Packages"
    excerpt: "Modules that help interface MongoDB with Django Rest Framework."            

addendum_row1:
  - image_path: /assets/images/djongo-Nxt-v1.png
    alt: "Djongo Next"
    title: "Djongo Next"
    excerpt: "The next generation connector. Ships with extra features for professional usage."
    url: https://nesdis.github.io/djongo/sponsor/
    btn_label: "Learn More"
    btn_class: "btn--primary"
    
advert_row:
  - image_path: /assets/images/e2e.png
    alt: "Admin MongoDB"
    image_link: http://www.e2eprojects.com/
    
  - image_path: /assets/images/white.jpg
    alt: "Admin MongoDB"

  - image_path: /assets/images/sumeru.png
    alt: "Admin MongoDB"
    image_link: https://www.sumerusolutions.com/

---

{% include feature_row id="punchline" type="center" %}

<!--
{% include advert_row %}
-->
{% include feature_row id="feature_row1" %}

{% include feature_row id="addendum_row1" type="center" %}





