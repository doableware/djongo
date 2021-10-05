import {Cookie, API_BASE} from "./utils.js";

(() => {
  const loginRedirect = '/djongocs/login/'

  if (!Cookie.has('UserId')) {
    window.location.href = loginRedirect;
    return;
  }
  fetch(API_BASE + 'user-info/').then(resp => {
    resp.json().then(user => {
      if (user['status'] === "LOGIN_REQUIRED") {
        window.location.href = loginRedirect;
      } else if (user['status'] === 'OK') {

      }
    })
  }, reason => {
    //No error handling
  })
})()