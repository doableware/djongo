import {API_BASE} from "./utils.js";
import {CreateAccountPage} from "./create-account.page.js";

(() => {
  const form = document.querySelector("form");
  const page = new CreateAccountPage();
  page.form.addEventListener(
    'submit',
    evt => {
      evt.preventDefault();
      document.querySelector('input[type="submit"]').disabled = true;
      page.show('loader');
      page.sendToBackend(API_BASE);
    },
    false)

})()
