// Google Analytics 4 for www.expressmoversilm.com
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'G-N494BH3VD9');

// Count a lead when someone reaches the thank-you page after the estimate form
if (/^\/thank-you(\.html)?\/?$/.test(location.pathname)) {
  gtag('event', 'generate_lead', { form_name: 'estimate_form' });
}

// Count a call when someone taps a phone number
document.addEventListener('click', function (e) {
  var a = e.target.closest && e.target.closest('a[href^="tel:"]');
  if (a) gtag('event', 'phone_call', { link_url: a.getAttribute('href'), page_path: location.pathname });
});
