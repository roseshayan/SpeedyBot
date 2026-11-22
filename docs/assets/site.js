const clipboardStatus = document.querySelector('#clipboard-status');

for (const button of document.querySelectorAll('.copy')) {
  button.hidden = false;
  let reset;
  button.addEventListener('click', async () => {
    const code = button.closest('.terminal').querySelector('code');
    const original = button.dataset.label;
    let status = button.dataset.copied;
    try {
      await navigator.clipboard.writeText(code.textContent);
    } catch {
      const range = document.createRange();
      range.selectNodeContents(code);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      status = button.dataset.selected;
    }
    button.textContent = status;
    clipboardStatus.textContent = status;
    clearTimeout(reset);
    reset = setTimeout(() => { button.textContent = original; }, 1800);
  });
}

const search = document.querySelector('#admin-search');
const sections = [...document.querySelectorAll('#admin details')];
const normalize = (value) => value.toLowerCase()
  .replaceAll('ي', 'ی').replaceAll('ك', 'ک').replaceAll('\u200c', '').trim();

search.parentElement.hidden = false;
search.addEventListener('input', () => {
  const query = normalize(search.value);
  for (const section of sections) {
    section.hidden = query !== '' && !normalize(section.textContent).includes(query);
    if (query && !section.hidden) section.open = true;
  }
  document.querySelector('#admin-empty').hidden = sections.some((section) => !section.hidden);
});

function revealTopic() {
  const topic = document.getElementById(window.location.hash.slice(1));
  if (topic?.tagName === 'DETAILS') {
    topic.open = true;
    topic.scrollIntoView();
  }
}
window.addEventListener('hashchange', revealTopic);
revealTopic();
