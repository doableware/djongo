---
layout: splash
classes:
  - empty-banner
  - l-splash
---

# Create Account

{% include form.html 
    form=site.data.support.forms.webserver 
    next="/support/payment/webserver/"
    subject="webserver Access" %}

<svg id="loader" class="is-hidden align-center" width="38" height="38" viewBox="0 0 38 38" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient x1="8.042%" y1="0%" x2="65.682%" y2="23.865%" id="a">
            <stop stop-color="#000" stop-opacity="0" offset="0%"/>
            <stop stop-color="#000" stop-opacity=".631" offset="63.146%"/>
            <stop stop-color="#000" offset="100%"/>
        </linearGradient>
    </defs>
    <g fill="none" fill-rule="evenodd">
        <g transform="translate(1 1)">
            <path d="M36 18c0-9.94-8.06-18-18-18" id="Oval-2" stroke="url(#a)" stroke-width="2">
                <animateTransform
                    attributeName="transform"
                    type="rotate"
                    from="0 18 18"
                    to="360 18 18"
                    dur="0.9s"
                    repeatCount="indefinite" />
            </path>
            <circle fill="#fff" cx="36" cy="18" r="1">
                <animateTransform
                    attributeName="transform"
                    type="rotate"
                    from="0 18 18"
                    to="360 18 18"
                    dur="0.9s"
                    repeatCount="indefinite" />
            </circle>
        </g>
    </g>
</svg>

<div id="ok" 
    class="is-hidden notice--success text-center" 
    markdown="1" 
>

**Success!**

Your Account has been created and will be activated after your email and payment have been verified.

<button id="button" class="btn btn--success btn--large center-box">Proceed to Payment</button>


</div>

<div id="user-exists" class="is-hidden text-center notice--warning" markdown="1">

**Oops!**

Username and Account already exists. Please try again.

</div>

{% include vendors/stripe.html btn_id="button" price_id="price_1HIKphLbyDBUaJVjQylkb7QE" %}