document.querySelectorAll('pre').forEach((pre) => {
  const wrap = document.createElement('div');
  wrap.className = 'code';
  pre.parentNode.insertBefore(wrap, pre);
  wrap.appendChild(pre);
  const button = document.createElement('button');
  button.className = 'copy';
  button.textContent = 'copiar';
  button.addEventListener('click', async () => {
    await navigator.clipboard.writeText(pre.innerText);
    button.textContent = 'copiado';
    setTimeout(() => { button.textContent = 'copiar'; }, 1300);
  });
  wrap.appendChild(button);
});

const key = 'videria-checks:' + document.body.dataset.role;
const saved = JSON.parse(localStorage.getItem(key) || '{}');
document.querySelectorAll('.check input').forEach((box, index) => {
  box.checked = !!saved[index];
  box.closest('.check').classList.toggle('done', box.checked);
  box.addEventListener('change', () => {
    saved[index] = box.checked;
    localStorage.setItem(key, JSON.stringify(saved));
    box.closest('.check').classList.toggle('done', box.checked);
  });
});
