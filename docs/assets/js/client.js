import {Cookie} from "./utils.js";

(() => {
  const apiUrl = 'https://api.djongomapper.com/mapper/'
  const loginPath = '/server/login/'

  if (!Cookie.has('UserId')) {
    window.location.href = loginPath;
    return;
  }
  fetch(apiUrl+'user-info/').then(resp => {
    resp.json().then(user => {
      if (user['status'] === "LOGIN_REQUIRED") {
        window.location.href = loginPath;
      } else if (user['status'] === 'OK') {

      }
    })
  }, reason => {
    //No error handling
  })
})()