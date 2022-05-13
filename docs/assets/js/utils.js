const API_BASE = 'https://api.djongomapper.com/mapper/';

class Cookie {
  constructor() {
  }

  static has(key) {
    return document.cookie.split(';').
      some(itm => itm.trim().startsWith(key + '='))
  }

  static get(key) {
    let cookie = document.cookie.split(';').
      find(itm => itm.trim().startsWith(key + '='));
    if(cookie) {
      return cookie.trim().split('=')[1];
    }
  }

  static set(key, val) {
    document.cookie = key + '=' + val + ';' + 'Secure';
  }
}

class Page {
  constructor(els) {
    this.els = els;
  }

  show(name) {
    this.els[name].classList.remove('is-hidden');
  }

  hide(name) {
    this.els[name].classList.add('is-hidden');
  }

  hideAll() {
    for (const name in this.els){
      this.hide(name);
    }
  }

  showAll() {
    for (const name in this.els){
      this.show(name);
    }
  }
}

export {
  Cookie,
  API_BASE,
  Page
}