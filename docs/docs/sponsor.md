---
title: Sponsor Djongo
permalink: /sponsor/ 
layout: splash
classes:
  - empty-header
  - custom-splash

excerpt: "If you are a company that uses Djongo in your products, consider enrolling in a subscription plan. You get long term support and advertisement space"
description: "If you are a company that uses Djongo in your products, consider enrolling in a subscription plan. You get long term support and advertisement space."

tire_column:
  tires:
  - title: Evangelist User
    price: 15
    btn_id: price_15
    price_id: price_1HIKphLbyDBUaJVjQylkb7QE
    benefits:
      - You get access to the djongoNxt repository.
      - Tickets raised under djongoNxt are triaged faster and have a higher priority.
      - You get access to the *priority discussion board* on GitHub.
      - Your questions are answered immediately.

  - title: Priority discussion
    price: 7
    btn_id: price_7
    price_id: price_1HIKkyLbyDBUaJVj8XbaHS8O
    benefits:
      - You get access to the *priority discussion board* on GitHub.
      - Your questions are answered immediately.

  - title: A Sweet Tip
    price: 4
    btn_id: price_4
    price_id: price_1HIKi6LbyDBUaJVj7FvgB3gx
    benefits:
      - You use Djongo and you LOVE IT.
      - You want to tip the project! Thanks!
    invisible: true

  - title: Q&A
    price: 4
    btn_id: price_4
    price_id: price_1HIKi6LbyDBUaJVj7FvgB3gx
    benefits:
      - Your questions are answered as soon as possible.
      - You support the long term sustainability of the project.
    invisible: true

  - title: A Sweet Tip
    price: 3
    btn_id: price_3
    price_id: price_1HIKfSLbyDBUaJVjuc3i3YEW
    benefits:
      - You use Djongo and you LOVE IT.
      - You want to tip the project! Thanks!
    invisible: true

  - title: Advertise on Djongo
    price: 50
    btn_id: price_50
    price_id: price_1HHwbOLbyDBUaJVjYnDESotB
    benefits:
      - Your name or company logo will be displayed on the home page.
      - Your feature requests and support queries to be given top priority.
    invisible: true

  disclaimer:
    - Subscriptions are not binding and can be canceled any time.
    - Upon successful checkout you requested to submit additional details required to deliver your benefits.

form:
  subject: sponsor-page
  fields:
    - type: text
      name: Name
      label: "Name:"
    - type: email
      name: Email
      label: "Email:"
    - type: select
      name: Subject
      label: "Subject:"
      options:
        - Request a commercial license
        - Unsubscribe from a tire

---

{% include sponsor.html %}

{% include vendors/stripe.html %}
