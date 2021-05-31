---
title: Djongo Webserver
permalink: /support/
layout: splash
tagline: "Create and Deploy Web APIs"
description: "If you are a company that uses Djongo in your products, consider enrolling in a subscription plan. You get long term support."
excerpt: "If you are a company that uses Djongo in your products, consider enrolling in a subscription plan. You get long term support."

classes:
  - l-splash-full
  - feature-page

header:
    overlay_image: /assets/images/home/banner-rand-dark-many6.png
    overlay_color_dark: #092e20
    overlay_color: #09411f
    cta_url: /support/contact/webserver/
    cta_label: "Deploy API"     
---

{% capture head %}
  {% include feature_page/support/tire.html %}
{% endcapture%}

{% capture content %}
## Enterprise

{% include form.html form=site.data.support.enterprise_form %}

If you are an enterprise that uses Djongo for commercial purposes, you need a license to use Djongo. Rights 
granted are: 

* Similar to a [MIT](https://opensource.org/licenses/MIT) style license.
* To use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software.

Get **phone, chat, and email support**. Send us a message for more information.

{% endcapture %}

{% include feature_page/features.html 
    content=content 
    head=head %}