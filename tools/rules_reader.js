(() => {
  'use strict';
  const all = (selector, root = document) => [...root.querySelectorAll(selector)];
  const sections = all('.rule-section');
  const search = document.getElementById('search');
  const source = document.getElementById('source');
  const onlyAnnotated = document.getElementById('annotated-only');
  const categoryButtons = all('.category-filter');
  const status = document.getElementById('result-status');
  const reset = document.getElementById('reset-filters');
  let debounce;
  let searchMarks = [];
  const normalize = text => text.toLocaleLowerCase().replace(/\s+/g, ' ').trim();
  sections.forEach(section => {
    section.readerText = normalize(section.textContent);
    section.readerNotes = all('.annotation', section);
    section.readerBase = normalize([...section.querySelectorAll('.section-header,.rule-paragraph,.rule-heading,table,.layout-block,.rule-list')].map(x => x.textContent).join(' '));
  });
  function clearHighlights() {
    searchMarks.forEach(mark => {
      const parent = mark.parentNode;
      if (parent) { mark.replaceWith(document.createTextNode(mark.textContent)); parent.normalize(); }
    });
    searchMarks = [];
  }
  function highlight(root, query) {
    if (query.length < 2) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: node => node.parentElement.closest('a,button,summary,kbd,[hidden]') || !node.nodeValue.trim() ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    let maximum = 350;
    for (const node of nodes) {
      let text = node.nodeValue;
      if (!text.toLocaleLowerCase().includes(query)) continue;
      const fragment = document.createDocumentFragment();
      while (maximum > 0) {
        const index = text.toLocaleLowerCase().indexOf(query);
        if (index < 0) break;
        fragment.append(document.createTextNode(text.slice(0, index)));
        const mark = document.createElement('mark');
        mark.className = 'search-match';
        mark.textContent = text.slice(index, index + query.length);
        searchMarks.push(mark); fragment.append(mark);
        text = text.slice(index + query.length); maximum--;
      }
      fragment.append(document.createTextNode(text)); node.replaceWith(fragment);
    }
  }
  function filter() {
    clearHighlights();
    const query = normalize(search.value);
    const tokens = query.split(' ').filter(Boolean);
    const allowed = new Set(categoryButtons.filter(x => x.getAttribute('aria-pressed') === 'true').map(x => x.dataset.category));
    let visible = 0, noteCount = 0;
    const uniqueNotes = new Set();
    for (const section of sections) {
      const notes = section.readerNotes.filter(note => allowed.has(note.dataset.category));
      section.readerNotes.forEach(note => { note.hidden = !allowed.has(note.dataset.category); });
      all('.related-notes', section).forEach(group => { group.hidden = !all('.annotation', group).some(note => !note.hidden); });
      const text = section.readerBase + ' ' + notes.map(note => normalize(note.textContent)).join(' ');
      const matches = (!source.value || source.value === section.dataset.source) && (!onlyAnnotated.checked || notes.length > 0) && tokens.every(token => text.includes(token));
      section.hidden = !matches;
      if (matches) { visible++; noteCount += notes.length; notes.forEach(note => uniqueNotes.add(note.dataset.noteId)); if (query) highlight(section, query); }
    }
    status.textContent = `${visible} of ${sections.length} rule sections · ${noteCount} annotation placement${noteCount === 1 ? '' : 's'} · ${uniqueNotes.size} unique note${uniqueNotes.size === 1 ? '' : 's'}`;
    document.getElementById('empty-state').hidden = visible > 0;
    reset.hidden = !query && !source.value && !onlyAnnotated.checked && allowed.size === categoryButtons.length;
  }
  function resetFilters() {
    search.value = ''; source.value = ''; onlyAnnotated.checked = false;
    categoryButtons.forEach(button => button.setAttribute('aria-pressed', 'true')); filter();
  }
  search.addEventListener('input', () => { clearTimeout(debounce); debounce = setTimeout(filter, 130); });
  search.addEventListener('keydown', event => { if (event.key === 'Escape') { search.value = ''; filter(); } });
  source.addEventListener('change', filter); onlyAnnotated.addEventListener('change', filter);
  categoryButtons.forEach(button => button.addEventListener('click', () => {
    button.setAttribute('aria-pressed', button.getAttribute('aria-pressed') === 'true' ? 'false' : 'true'); filter();
  }));
  reset.addEventListener('click', resetFilters); document.getElementById('empty-reset').addEventListener('click', resetFilters);
  document.addEventListener('keydown', event => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); search.focus(); search.select(); }
  });
  document.getElementById('print-button').addEventListener('click', () => window.print());
  const navToggle = document.getElementById('nav-toggle');
  function closeNav() { document.body.classList.remove('nav-open'); navToggle.setAttribute('aria-expanded', 'false'); }
  navToggle.addEventListener('click', () => {
    const open = document.body.classList.toggle('nav-open'); navToggle.setAttribute('aria-expanded', String(open));
  });
  document.getElementById('scrim').addEventListener('click', closeNav);
  all('.toc nav a').forEach(link => link.addEventListener('click', () => {
    const target = document.getElementById(decodeURIComponent(link.hash.slice(1)));
    if (target?.hidden) resetFilters();
    closeNav();
  }));
  function revealHash() {
    let target;
    try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch { return; }
    if (!target) return;
    const section = target.closest('.rule-section');
    if (section?.hidden || target.closest('.annotation')?.hidden) resetFilters();
    const tocLink = all('.toc nav a').find(link => section && link.hash === '#' + section.id);
    if (tocLink) tocLink.closest('details').open = true;
  }
  window.addEventListener('hashchange', revealHash); revealHash();
  if ('IntersectionObserver' in window) {
    const navLinks = new Map(all('.toc nav a').map(link => [decodeURIComponent(link.hash.slice(1)), link]));
    const observer = new IntersectionObserver(entries => {
      entries.filter(entry => entry.isIntersecting).forEach(entry => {
        all('.toc nav a.active').forEach(link => link.classList.remove('active'));
        navLinks.get(entry.target.id)?.classList.add('active');
      });
    }, { rootMargin: '-8% 0px -72% 0px', threshold: 0 });
    sections.forEach(section => observer.observe(section));
  }
  filter();
})();
