---
permalink: /support/djongocs/create-account/ 
layout: splash
classes:
  - empty-header
  - l-splash
---

# Create Account

{% include form.html 
    form=site.data.support.tire_form.webserver 
    next="/support/payment/webserver/"
    subject="webserver Access" %}

<div id="success" class="is-hidden notice--success" markdown="1">
**Success!**
{: .text-center}

Your Account has been created and will be activated after your email and payment have been verified.
{: .text-center}

<button id="button" class="btn btn--success btn--large center-box">Proceed to Payment</button>
</div>


## Oops! Account exists. Try again
{: #account-exists .reset-border .is-hidden}

{% include vendors/stripe.html btn_id="button" price_id="price_1HIKphLbyDBUaJVjQylkb7QE" %}