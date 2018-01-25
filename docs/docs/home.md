---
permalink: /
layout: splash
title: "Djongo"
excerpt: "A Django and MongoDB connector"
header:
    overlay_image: /assets/images/landing-banner.jpg

punchline:
  - excerpt: Use MongoDB as a backend database for your Django project, without changing the Django ORM. 

feature_row:
  - image_path: /assets/images/feature-admin-mongo.jpg
    alt: "Admin MongoDB"
    title: "Use Django Admin to access MongoDB"
    excerpt: "Use the Django Admin app to insert, modify and delete documents in MongoDB."
  
  - image_path: /assets/images/djongo-symbol.jpg
    alt: "MongoDB data fields"
    title: "Use Django with MongoDB data fields"
    excerpt: "Use MongoDB embedded documents and embedded arrays in Django Models."
    
  - image_path: /assets/images/drf.jpg
    alt: "3rd party apps"
    title: "Connect 3rd party apps with MongoDB"
    excerpt: "Apps like **Django Rest Framework** and Viewflow app that use Django Models integrate easily with MongoDB."

---


{% include feature_row id="punchline" type="center" %}

{% include feature_row %}

