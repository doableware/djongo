---
title: Djongo Support Services
layout: splash
excerpt: "If you are a company that uses Djongo in your products, consider enrolling in a subscription plan. You get long term support"
description: "If you are a company that uses Djongo in your products, consider enrolling in a subscription plan. You get long term support."

classes:
  - l-splash
  - empty-header
---

{% capture enterprise %}
If you are an enterprise that uses Djongo for commercial purposes, you need a license to use Djongo. Rights 
granted are: 

* Similar to a [MIT](https://opensource.org/licenses/MIT) style license.
* To use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software.

Get **phone, chat, and email support**. Send us a message for more information.
{% endcapture %}


{% capture other_benefits %}
## DjongoNxt
DjongoNxt brings support to more features of MongoDB. It is hosted as a private repository on Github. Issues raised here have a higher priority versus those raised on the public repository. 

Critical bug fixes and maintenance patches are first published to DjongoNxt.

## Priority Discussion Board
The priority [discussion board][board] is hosted on github and members with a subscription have access to it. Questions posted get a response within 24 hours.

[board]: https://docs.github.com/en/free-pro-team@latest/github/building-a-strong-community/about-team-discussions

{% endcapture %}

{% capture discuss %}
# Discuss

[Djongo forum](https://groups.google.com/forum/#!forum/djongo) is where you can watch for:

* New release announcements.
* Suggest improvements.
* Ask questions.
* Discuss topics pertaining to Django and MongoDB.

{% endcapture %}

{% include feature_page/support/support.html
 enterprise=enterprise
 enterprise_title=enterprise_title
 other_benefits=other_benefits
 discuss=discuss %}