---
title: Support
permalink: /support/
layout: splash

row1:
  - image_path: /assets/images/migration.png
    alt: "Migration Support"
    title: "Migration Support"
    excerpt: "Migrate your existing Django app to MongoDB in a phased manner."

row2:    
  - image_path: /assets/images/optimization2.png
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

<div class="feature__wrapper">

<div class="liquid-slider"  id="slider-1">
    <div>
        <h2 class="title">Chan</h2>
        <p>Thanks again for the quick responses! Great work by the way!</p>
    </div>
    <div>
        <h2 class="title">Theo</h2>
        <p>Works like a charm. Thanks a lot.</p>
    </div>
    <div>
        <h2 class="title">Ryan</h2>
        <p>Thanks for you work on this. Thanks so much for your help and for Djongo.</p>
    </div>
    <div>
        <h2 class="title">Feng</h2>
        <p>I have to say Djongo is very useful between Django and Mongodb.</p>
    </div>
</div>   
</div>

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