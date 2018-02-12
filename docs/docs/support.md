---
title: Support
permalink: /support/
layout: splash

row1:
  - image_path: /assets/images/sagome.jpg
    alt: "Admin MongoDB"
    title: "Migration Support"
    excerpt: "Ask for support to migrate existing data from SQL DB or MongoDB in a phased manner."

row2:    
  - image_path: /assets/images/optimize.jpg
    alt: "Admin MongoDB"
    title: "Database Optimization"
    excerpt: "Ask for support to migrate Django Fields to Djongo Fields in a phased manner and notice the difference."    
    
row3:
  - excerpt: ">Thanks again for the quick responses! Great work by the way! --- Chan"
  
row4:
  - excerpt: ">Works like a charm. Thanks a lot. --- Theo"
  
row5:
  - excerpt: ">Thanks for you work on this. Thanks so much for your help and for Djongo. --- Ryan"
  
row6:
  - excerpt: ">I have to say Djongo is very useful between Django and Mongodb.--- Feng"      
---

{% include feature_row id="row1" type="left" %}

{% include feature_row id="row2" type="right" %}

{% include feature_row id="row3" type="center" %}

{% include feature_row id="row4" type="center" %}

{% include feature_row id="row5" type="center" %}

{% include feature_row id="row6" type="center" %}



<form action="https://formspree.io/nesdis@gmail.com"
      method="POST">
    Name:
    <input type="text" name="name" required>
    Organization:
    <input type="text" name="Organization" required>
    Email:
    <input type="email" name="_replyto" required>
    Support Request:
    <TEXTAREA Name="comments" rows="4" cols="20"></TEXTAREA> 
    <input type="submit" value="Send">
</form> 