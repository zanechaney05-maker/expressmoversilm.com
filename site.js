/* Express Movers site script. One file, no libraries, nothing loaded from other sites
   unless an analytics ID is set in build.py. Kept external so the page can run under a
   Content-Security-Policy that blocks inline scripts. */
(function () {
  'use strict';
  var root = document.documentElement;
  var loadedAt = Date.now();

  /* Close the phone menu when a link in it is used or Escape is pressed. */
  var menu = document.querySelector('.menu');
  if (menu) {
    menu.addEventListener('click', function (e) { if (e.target.closest('a')) menu.open = false; });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') menu.open = false; });
  }

  /* Estimate form. */
  var form = document.getElementById('estimate-form');
  if (form) {
    var note = document.getElementById('form-note');
    var action = form.getAttribute('data-action') || '';
    var done = form.getAttribute('data-done') || '';
    var phoneText = form.getAttribute('data-phone') || '';

    /* A link such as /contact?service=local picks the matching choice. */
    try {
      var wanted = new URLSearchParams(location.search).get('service');
      if (wanted) {
        var pick = form.querySelector('input[name="service"][data-key="' + wanted.replace(/[^a-z]/g, '') + '"]');
        if (pick) pick.checked = true;
      }
    } catch (err) { /* older browsers: keep the default choice */ }

    var say = function (text) { note.hidden = false; note.textContent = text; };

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var name = form.elements.name.value.trim();
      var phone = form.elements.phone.value.trim();
      var digits = phone.replace(/\D/g, '');
      if (!name || digits.length < 10) { say('Add your name and a 10-digit phone number so we can reach you.'); return; }
      /* Spam traps: a hidden field people never see, and a form sent faster than a person can type.
         A real person who trips one still gets the phone number. */
      if (form.elements._gotcha.value || Date.now() - loadedAt < 2500) { say('The request did not send. Call or text ' + phoneText + '.'); return; }
      if (!action) { say('This form is not connected yet, so nothing was sent. Call or text ' + phoneText + '.'); return; }
      var button = form.querySelector('button[type="submit"]');
      button.disabled = true;
      say('Sending your request.');
      fetch(action, { method: 'POST', body: new FormData(form), headers: { 'Accept': 'application/json' } })
        .then(function (r) {
          if (!r.ok) throw new Error('send failed');
          if (done) { location.href = done; } else { form.reset(); say('Request sent. We will get back to you soon.'); }
        })
        .catch(function () { button.disabled = false; say('The request did not send. Call or text ' + phoneText + '.'); });
    });
  }

  /* Analytics. Off unless build.py sets an ID. Each ID belongs to Express Movers, never to the agency. */
  var ga = root.getAttribute('data-ga');
  if (ga) {
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(ga);
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', ga);
    if (root.hasAttribute('data-lead')) window.gtag('event', 'generate_lead');
  }
  var pixel = root.getAttribute('data-pixel');
  if (pixel) {
    var fbq = window.fbq = function () { fbq.callMethod ? fbq.callMethod.apply(fbq, arguments) : fbq.queue.push(arguments); };
    if (!window._fbq) window._fbq = fbq;
    fbq.push = fbq; fbq.loaded = true; fbq.version = '2.0'; fbq.queue = [];
    var p = document.createElement('script');
    p.async = true;
    p.src = 'https://connect.facebook.net/en_US/fbevents.js';
    document.head.appendChild(p);
    fbq('init', pixel);
    fbq('track', 'PageView');
    if (root.hasAttribute('data-lead')) fbq('track', 'Lead');
  }
})();
