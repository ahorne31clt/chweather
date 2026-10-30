const menuButton = document.querySelector('.menu-button');
const navigation = document.querySelector('#navigation');
menuButton?.addEventListener('click', () => {
  const open = menuButton.getAttribute('aria-expanded') !== 'true';
  menuButton.setAttribute('aria-expanded', String(open));
  navigation.classList.toggle('open', open);
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && menuButton?.getAttribute('aria-expanded') === 'true') {
    menuButton.setAttribute('aria-expanded', 'false');
    navigation.classList.remove('open');
    menuButton.focus();
  }
});
document.querySelectorAll('[data-filter]').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('[data-filter]').forEach(item => {
      item.classList.toggle('active', item === button);
      item.setAttribute('aria-pressed', String(item === button));
    });
    let visible = 0;
    document.querySelectorAll('[data-category]').forEach(course => {
      course.hidden = button.dataset.filter !== 'all' && course.dataset.category !== button.dataset.filter;
      if (!course.hidden) visible++;
    });
    document.querySelector('#filter-status').textContent = `${visible} courses shown.`;
  });
});

// Load X's official widget only on pages with a timeline, near the viewport.
const timeline = document.querySelector('.twitter-timeline');
if (timeline) {
  const observer = new IntersectionObserver(entries => {
    if (!entries.some(entry => entry.isIntersecting)) return;
    const script = document.createElement('script');
    script.src = 'https://platform.twitter.com/widgets.js';
    script.async = true;
    script.charset = 'utf-8';
    document.body.append(script);
    observer.disconnect();
  }, { rootMargin: '600px' });
  observer.observe(timeline);
}
