---
title: Sponsor
permalink: /sponsor/ 
layout: splash

excerpt: "If you are a company that uses Djongo in your products, consider enrolling in a subscription plan. You get long term support and advertisement space"
description: "If you are a company that uses Djongo in your products, consider enrolling in a subscription plan. You get long term support and advertisement space."

sponsor_row:
  - title: A Sweet Tip
    price: 3
    btn_id: price_3
    benefits:
      - You use Djongo and you LOVE IT.
      - You want to tip me! Thanks!
  
  - title: Q&A
    price: 4
    btn_id: price_4
    benefits:
      - I will take a look at your **one question**.
      - You support the long term sustainability of the project.
      - Your token of appreciation will help me continue maintain the repository.

  - title: Generous Supporter
    price: 7
    btn_id: price_7
    benefits:
      - I answer your questions within 24 hours on Discord priority-support.
      - You support the long term sustainability of the project.
      - I mention your name in the source code.
  
  - title: Evangelist Supporter
    price: 15
    btn_id: price_15
    benefits:
      - You **get access to the djongoNxt** repository.
      - Your questions are **immediately** taken up for consideration on Discord priority-support.
      - You support the long term sustainability of the project.
  
  - title: Advertise on Djongo
    price: 50
    btn_id: price_50
    benefits:
      - Your name or company logo will be displayed on the home page.
      - Your feature requests and support queries to be given top priority.
      
---

{% include tire_row %}

 * *Subscriptions are not binding and can be canceled any time.*
 * *Upon successful checkout you are provided with an option to submit additional details required to deliver your benefits.*

<script>
  // Replace with your own publishable key: https://dashboard.stripe.com/test/apikeys
  var PUBLISHABLE_KEY = "pk_live_eEfW8XjO4oZUPRFaYASLCWqn";
  // Replace with the domain you want your users to be redirected back to after payment
  var DOMAIN = "https://nesdis.github.io";

  var stripe = Stripe(PUBLISHABLE_KEY);

  // Handle any errors from Checkout
  var handleResult = function (result) {
    if (result.error) {
      var displayError = document.getElementById("error-message");
      displayError.textContent = result.error.message;
    }
  };

  var redirectToCheckout = function (priceId) {
    // Make the call to Stripe.js to redirect to the checkout page
    // with the current quantity
    stripe
      .redirectToCheckout({
        lineItems: [{ price: priceId, quantity: 1 }],
        successUrl:
          DOMAIN + "/djongo?session_id={CHECKOUT_SESSION_ID}",
        cancelUrl: DOMAIN + "/sponsor",
        mode: 'subscription',
      })
      .then(handleResult);
  };

  document
    .getElementById("price_3")
    .addEventListener("click", function (evt) {
      redirectToCheckout("price_1HIKfSLbyDBUaJVjuc3i3YEW");
    });

  document
    .getElementById("price_4")
    .addEventListener("click", function (evt) {
      redirectToCheckout("price_1HIKi6LbyDBUaJVj7FvgB3gx");
    });
  
  document
    .getElementById("price_7")
    .addEventListener("click", function (evt) {
      redirectToCheckout("price_1HIKkyLbyDBUaJVj8XbaHS8O");
    });
  
  document
    .getElementById("price_15")
    .addEventListener("click", function (evt) {
      redirectToCheckout("price_1HIKphLbyDBUaJVjQylkb7QE");
    });
  
  document
    .getElementById("price_50")
    .addEventListener("click", function (evt) {
      redirectToCheckout("price_1HHwbOLbyDBUaJVjYnDESotB");
    });
    
</script>
