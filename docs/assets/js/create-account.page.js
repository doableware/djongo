import {API_BASE, Page} from "./utils.js";

class CreateAccountPage extends Page {
  constructor() {
    let els = {
      ok: document.getElementById('ok'),
      userExists: document.getElementById('user-exists'),
      loader: document.getElementById('loader')
    }
    super(els);
    this.form = document.querySelector("form");
  }

  sendToBackend(API_BASE) {
    let data = new FormData(this.form);
    fetch(API_BASE + 'create-account/',
      { method: 'POST',
        body: data,
        mode: 'cors'
      }).then(resp => {
        resp.json().then(result => {
          this.hide('loader');
          if (result.status === 'OK') {
            this.show('ok');
          }
          else if (result.status === 'USER_EXISTS') {
            this.show('userExists');
          }
        });
    })
  }
}

export {CreateAccountPage}
