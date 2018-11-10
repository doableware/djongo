---
permalink: /
layout: splash
title: "Django MongoDB connector"
excerpt: "Djongo"
description: "Djongo is specifically meant to be used with the original Django ORM and MongoDB. Using the Django admin app one can directly add and modify documents stored in MongoDB. Other contrib modules such as Auth and Sessions work without any changes"

header:
    overlay_image: /assets/images/landing-banner3.jpg

punchline:
  - excerpt: Use MongoDB with Django, by adding just one line of code.

feature_row:

  - image_path: /assets/images/support.png
    alt: "Support"
    title: "Support"
    excerpt: "Get immediate support for queries on using Django with MongoDB"
    url: https://www.patreon.com/nesdis/
    btn_label: "Learn More"
    btn_class: "btn--primary"

  - image_path: /assets/images/djongo-symbol2.jpg
    alt: "MongoDB data fields"
    title: "Use Django with MongoDB data fields"
    excerpt: "Use MongoDB embedded documents and embedded arrays in Django Models."

  - image_path: /assets/images/feature-admin-mongo.jpg
    alt: "Admin MongoDB"
    title: "Use Django Admin to access MongoDB"
    excerpt: "Use the Django Admin app to insert, modify and delete documents in MongoDB."


addendum_row1:
  - image_path: /assets/images/djongo-Nxt-v1.png
    alt: "Djongo Next"
    title: "Djongo Next"
    excerpt: "The next generation connector. Ships with binary extensions for enterprise usage."
    url: https://www.patreon.com/posts/djongonxt-next-22247203
    btn_label: "Learn More"
    btn_class: "btn--primary"
---


{% include feature_row id="punchline" type="center" %}

{% include feature_row %}

{% include feature_row id="addendum_row1" type="center" %}