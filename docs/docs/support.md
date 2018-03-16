---
title: Support
permalink: /support/
layout: splash

row1:
  - image_path: /assets/images/sagome.jpg
    alt: "Migration Support"
    title: "Migration Support"
    excerpt: "Migrate your existing Django app to MongoDB in a phased manner."

row2:    
  - image_path: /assets/images/optimize.jpg
    alt: "Database Optimization"
    title: "Database Optimization"
    excerpt: "Migrate Django Fields to powerful Djongo Fields in a phased manner and notice the difference."    
    
row3:    
  - image_path: /assets/images/bug.jpg
    alt: "Debug Support"
    title: "Development and Debug Support"
    excerpt: "Support for Django App development. Data model design and development."  
        
test1:
  - excerpt: ">Thanks again for the quick responses! Great work by the way! --- Chan"
  
test2:
  - excerpt: ">Works like a charm. Thanks a lot. --- Theo"
  
test3:
  - excerpt: ">Thanks for you work on this. Thanks so much for your help and for Djongo. --- Ryan"
  
test4:
  - excerpt: ">I have to say Djongo is very useful between Django and Mongodb.--- Feng"      
---


{% include feature_row id="row1" type="left" %}

{% include feature_row id="row2" type="right" %}

{% include feature_row id="row3" type="left" %}


{% include feature_row id="test1" type="center" %}

{% include feature_row id="test2" type="center" %}

{% include feature_row id="test3" type="center" %}

{% include feature_row id="test4" type="center" %}



<form action="https://formspree.io/nesdis@gmail.com"
      method="POST">
    Name:
    <input type="text" name="Name" required>
    Organization:
    <input type="text" name="Organization" required>
    Email:
    <input type="email" name="_replyto" required>
    Support Request:
    <TEXTAREA Name="Message" rows="4" cols="20"></TEXTAREA> 
    <input type="submit" value="Send">
</form> 