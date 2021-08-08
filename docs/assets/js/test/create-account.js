import {CreateAccountPage} from "../create-account.page.js";
const API_BASE = 'http://127.0.0.1:8000/';

(() => {
  const page = new CreateAccountPage();
  const form = document.querySelector("form");
  page.show('ok');

  page.form.addEventListener(
    'submit',
    evt => {
      evt.preventDefault();
      document.querySelector('input[type="submit"]').disabled = true;
      page.show('ok');
    }, false
  )
})()
