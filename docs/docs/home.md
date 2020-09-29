---
permalink: /
layout: splash
title: "MongoDB Document Mapper"
classes:
    - landing-page
excerpt: 
description: "Djongo is a smarter approach to pymongo programming. It maps python objects to MongoDB documents. It is popularly referred to as an Object Document Mapper or ODM. It is an extension to the traditional Django object relational modeling framework. Use Django Admin to directly add and modify documents stored in MongoDB. Use other contrib modules such as Auth and Sessions without any changes."

header:
    overlay_image: /assets/images/landing/landing-banner-narrow.jpg
    overlay_color: #092e20

punchline:
  - excerpt: Python Object to MongoDB Document Mapping Framework

value_row_first:
  - image_path: /assets/images/landing/security-green.png
    alt: "Security"
    title: "Security"
    excerpt: "Directly saving raw `JSON` into the database is scary. Djongo secures and validates the `JSON` document before saving."
    
  - image_path: /assets/images/landing/query-green-own.png
    alt: "Simplify Query Creation"
    title: "Simplify Query Creation"
    excerpt: "Easily create and query [embedded documents](/djongo/using-django-with-mongodb-data-fields/) 
     and [arrays](/djongo/using-django-with-mongodb-array-field/). Add
    MongoDB specific [indexes](/djongo/djongonxt-indexes/), [transactions](djongonxt-database-transactions/),
    and much more."

  - image_path: /assets/images/landing/webpage.png
    alt: "Web Interface"
    title: "Web Interface"
    excerpt: "Access and modify MongoDB through the web browser."

  - image_path: /assets/images/landing/support-new.png
    alt: "Support"
    title: "Support"
    excerpt: "Get immediate support for queries on MongoDB document modeling."
    url: /support/
    btn_label: "Learn More"
    btn_class: "btn--primary"
    
  - image_path: /assets/images/landing/rapid.png
    alt: "Rapid Prototyping"
    title: "Rapid Prototyping"
    excerpt: "Speed up app development and execution with [schema free models](/djongo/get-started/#enforce-schema), 
    skip migrations, and [autogenerate complex queries](/djongo/using-django-with-mongodb-array-reference-field/)."  
      
  - image_path: /assets/images/landing/third-party-thin.png
    alt: "Admin MongoDB"
    title: "Third Party Packages"
    excerpt: "Modules that help interface your MongoDB data with other popular packages."

djongonxt_row:
  - image_path: /assets/images/landing/djongo-Nxt-v1.png
    alt: "Djongo Next"
    title: "Djongo Next"
    excerpt: "The advanced modeling framework. Ships with extra features for professional usage."
    url: /support/
    btn_label: "Learn More"
    btn_class: "btn--primary"
  
    
advert_row:
  - image_path: /assets/images/landing/e2e.png
    alt: "Admin MongoDB"
    image_link: http://www.e2eprojects.com/
    
  - image_path: /assets/images/white.jpg
    alt: "Admin MongoDB"

  - image_path: /assets/images/landing/sumeru.png
    alt: "Admin MongoDB"
    image_link: https://www.sumerusolutions.com/

---

{% include feature_row id="punchline" type="center" %}

<!--
{% include advert_row %}
-->
{% include feature_row id="value_row_first" %}

{% include feature_row id="djongonxt_row" type="center" %}

Djongo maps python objects to MongoDB documents, a technique popularly referred to as Object Document Mapping or ODM. It is an extension to the traditional Django ORM framework. 

Constructing queries is much easier compared to manually writing lengthy query documents with pymongo. Djongo automatically creates complex query documents for you. 

Storing raw `JSON` emitted by the frontend directly into the database is scary. Djongo ensures that only clean data gets through. 

You no longer need to use the shell to inspect your data. By using the `Admin` package, you can access and modify data directly from the web browser. Djongo carries handy UI elements that help represent MongoDB documents on the browser. 


[Get Started](/djongo/get-started){: .btn .btn--primary}
{: .text-center}



