(() => {
  const menuButton = document.querySelector('[data-menu-toggle]');
  const mobileMenu = document.querySelector('[data-mobile-menu]');
  if (menuButton && mobileMenu) {
    menuButton.addEventListener('click', () => {
      const open = mobileMenu.classList.toggle('open');
      menuButton.setAttribute('aria-expanded', String(open));
      menuButton.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    });
    mobileMenu.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
      mobileMenu.classList.remove('open');
      menuButton.setAttribute('aria-expanded', 'false');
    }));
  }

  const formatDate = (value) => value ? new Intl.DateTimeFormat('en', { year: 'numeric', month: 'short', day: 'numeric' }).format(new Date(value)) : '';
  const escapeHtml = (value = '') => value.replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]);
  const isHindi = (value = '') => /[\u0900-\u097F]/.test(value);
  const classify = (post) => {
    const text = `${post.title || ''} ${post.category || ''} ${(post.categories || []).join(' ')} ${post.group || ''}`.toLowerCase();
    const classes = [];
    if (/science|health|aging|fitness|protein|epigenetic|diabetes|मधुमेह|तनाव/.test(text)) classes.push('science');
    if (/story|stories|fiction|speculative|ghost|moriarty|buddha|train|game|timothy|confession/.test(text)) classes.push('stories');
    if (/poem|poetry|कविता|शायरी|shayari|life|facades|molecules|उड़ान|ख़्वाब|ख़्वाब/.test(text)) classes.push('poems');
    if (isHindi(text)) classes.push('hindi');
    return classes.length ? classes : ['stories'];
  };

  const normalizePost = (post) => {
    const normalized = { ...post };
    if (/^Epigenetics: Shaping Your Genes/i.test(normalized.title || '')) {
      normalized.categories = ['Speculative fiction'];
      normalized.excerpt = 'A speculative story about inheritance, memory, and whether the marks life leaves on us can shape what comes next.';
    }
    if (/^Five Superfood Seeds/i.test(normalized.title || '')) normalized.image = 'superfoods.png';
    if (/^तनाव और चिंता/i.test(normalized.title || '')) normalized.image = 'tanaav.png';
    return normalized;
  };

  const postCard = (post) => {
    const image = post.image ? `<img src="${escapeHtml(post.image)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : '<div class="post-image-placeholder"></div>';
    const category = (post.categories || [post.category || post.group || 'Writing'])[0];
    return `<article class="post-card" data-categories="${classify(post).join(' ')}" data-search="${escapeHtml(`${post.title} ${post.excerpt} ${category}`.toLowerCase())}">
      ${image}<div class="post-card-content"><div class="post-meta"><span>${escapeHtml(category || 'Writing')}</span>${post.date ? `<time>${formatDate(post.date)}</time>` : ''}</div><h3>${escapeHtml(post.title)}</h3><p>${escapeHtml(post.excerpt || '')}</p><a class="text-link" href="${escapeHtml(post.url)}" target="_blank" rel="noopener">Read on Blogger <span aria-hidden="true">↗</span></a></div>
    </article>`;
  };

  const latest = document.getElementById('latest-posts');
  const bloggerContainer = document.getElementById('blogger-posts');
  const renderBloggerPosts = () => {
    if (!window.BLOGGER_POSTS) return;
    const posts = window.BLOGGER_POSTS.map(normalizePost);
    if (latest) {
      const preferred = [
        'Fuel Your Muscles: Protein for Growth, Recovery & Performance',
        'Five Superfood Seeds That Fight Aging and Keep You Healthy',
        'Social Media Overload: A Dangerous Abyss'
      ];
      const curated = preferred.map((title) => posts.find((post) => post.title === title)).filter(Boolean);
      latest.innerHTML = [...curated, ...posts.filter((post) => !curated.includes(post) && !/^Epigenetics:/i.test(post.title || ''))].slice(0, 3).map(postCard).join('');
    }
    if (bloggerContainer) bloggerContainer.innerHTML = posts.map(postCard).join('');
  };
  renderBloggerPosts();

  const archiveContainer = document.getElementById('archive-posts');
  const searchInput = document.querySelector('[data-post-search]');
  const filterButtons = [...document.querySelectorAll('[data-filter]')];
  const loadMore = document.querySelector('[data-load-more]');
  let activeFilter = 'all';
  let visibleArchive = 12;

  const archiveCard = (post, index) => `<a class="archive-card" href="${escapeHtml(post.url)}" data-categories="${classify(post).join(' ')}" data-search="${escapeHtml(`${post.title} ${post.excerpt} ${post.category}`.toLowerCase())}">${post.image ? `<img src="${escapeHtml(post.image)}" alt="" loading="lazy">` : `<span class="archive-number">${String(index + 1).padStart(2, '0')}</span>`}<span><span class="post-meta">${escapeHtml(post.category || post.group)}</span><h3>${escapeHtml(post.title)}</h3><p>${escapeHtml(post.date || post.excerpt.slice(0, 85))}</p></span><span aria-hidden="true">→</span></a>`;

  const renderArchive = () => {
    if (!archiveContainer || !window.ARCHIVE_POSTS) return;
    const query = (searchInput?.value || '').trim().toLowerCase();
    const filtered = window.ARCHIVE_POSTS.filter((post) => {
      const categories = classify(post);
      const matchesFilter = activeFilter === 'all' || categories.includes(activeFilter);
      const haystack = `${post.title} ${post.excerpt} ${post.category}`.toLowerCase();
      return matchesFilter && (!query || haystack.includes(query));
    });
    archiveContainer.innerHTML = filtered.length ? filtered.slice(0, visibleArchive).map(archiveCard).join('') : '<p class="empty-state">No archived writing matches that search.</p>';
    const count = document.getElementById('archive-count');
    if (count) count.textContent = String(filtered.length);
    if (loadMore) loadMore.hidden = filtered.length <= visibleArchive;
  };

  const applyFilters = () => {
    const query = (searchInput?.value || '').trim().toLowerCase();
    document.querySelectorAll('#blogger-posts .post-card').forEach((card) => {
      const matchesFilter = activeFilter === 'all' || card.dataset.categories.split(' ').includes(activeFilter);
      const matchesSearch = !query || card.dataset.search.includes(query);
      card.hidden = !(matchesFilter && matchesSearch);
    });
    visibleArchive = 12;
    renderArchive();
  };

  filterButtons.forEach((button) => button.addEventListener('click', () => {
    activeFilter = button.dataset.filter;
    filterButtons.forEach((item) => item.classList.toggle('active', item === button));
    applyFilters();
  }));
  searchInput?.addEventListener('input', applyFilters);
  loadMore?.addEventListener('click', () => { visibleArchive += 12; renderArchive(); });
  renderArchive();

  // Blogger's public JSONP feed keeps the website current without account access.
  if (latest || bloggerContainer) {
    window.handleAvinashBloggerFeed = (payload) => {
      const stripMarkup = (html = '') => {
        const container = document.createElement('div');
        container.innerHTML = html;
        return (container.textContent || '').replace(/\s+/g, ' ').trim();
      };
      const livePosts = (payload?.feed?.entry || []).map((entry) => {
        const url = entry.link?.find((link) => link.rel === 'alternate')?.href || 'https://avinasholmes.blogspot.com';
        const thumbnail = entry['media$thumbnail']?.url?.replace(/s72-/, 's640-') || '';
        const plain = stripMarkup(entry.content?.$t || '');
        return { title: entry.title?.$t?.trim() || 'Untitled', date: entry.published?.$t || '', categories: (entry.category || []).map((item) => item.term), url, image: thumbnail, excerpt: `${plain.slice(0, 220).replace(/\s+\S*$/, '')}…` };
      });
      if (livePosts.length) {
        window.BLOGGER_POSTS = livePosts;
        renderBloggerPosts();
        applyFilters();
      }
    };
    const feedScript = document.createElement('script');
    feedScript.src = 'https://avinasholmes.blogspot.com/feeds/posts/default?alt=json-in-script&max-results=50&callback=handleAvinashBloggerFeed';
    feedScript.async = true;
    document.head.appendChild(feedScript);
  }

  const homeGallery = document.querySelector('[data-home-gallery]');
  if (homeGallery && window.GALLERY_PHOTOS) {
    const featuredIds = [156, 90, 193, 248, 285, 83, 207, 254, 47, 211, 160, 147];
    const featured = featuredIds.map((id) => window.GALLERY_PHOTOS.find((photo) => photo.id === id)).filter(Boolean);
    homeGallery.innerHTML = featured.map((photo) => `<figure><img src="${escapeHtml(photo.thumb)}" alt="${escapeHtml(photo.alt)}" loading="lazy"><figcaption>${escapeHtml(photo.label)}</figcaption></figure>`).join('');
    const total = document.querySelector('[data-slider-total]');
    if (total) total.textContent = String(featured.length);
  }

  document.querySelectorAll('[data-photo-slider]').forEach((slider) => {
    const viewport = slider.querySelector('[data-slider-viewport]');
    const slides = [...slider.querySelectorAll('figure')];
    const current = slider.querySelector('[data-slider-current]');
    if (!viewport || !slides.length) return;
    const go = (direction) => {
      const gap = parseFloat(getComputedStyle(slider.querySelector('.photo-slider-track')).gap) || 0;
      viewport.scrollBy({ left: direction * (slides[0].getBoundingClientRect().width + gap), behavior: 'smooth' });
    };
    slider.querySelector('[data-slider-prev]')?.addEventListener('click', () => go(-1));
    slider.querySelector('[data-slider-next]')?.addEventListener('click', () => go(1));
    viewport.addEventListener('scroll', () => {
      const gap = parseFloat(getComputedStyle(slider.querySelector('.photo-slider-track')).gap) || 0;
      const index = Math.round(viewport.scrollLeft / Math.max(1, slides[0].getBoundingClientRect().width + gap));
      if (current) current.textContent = String(Math.min(slides.length, Math.max(1, index + 1)));
    }, { passive: true });
    if (slider.querySelector('[data-home-gallery]') && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      let paused = false;
      const advance = () => {
        if (paused) return;
        const gap = parseFloat(getComputedStyle(slider.querySelector('.photo-slider-track')).gap) || 0;
        const step = slides[0].getBoundingClientRect().width + gap;
        const index = Math.round(viewport.scrollLeft / Math.max(1, step));
        if (index >= slides.length - 1) viewport.scrollTo({ left: 0, behavior: 'smooth' });
        else go(1);
      };
      window.setInterval(advance, 4200);
      slider.addEventListener('mouseenter', () => { paused = true; });
      slider.addEventListener('mouseleave', () => { paused = false; });
      slider.addEventListener('focusin', () => { paused = true; });
      slider.addEventListener('focusout', () => { paused = false; });
    }
  });

  const galleryGrid = document.querySelector('[data-gallery-grid]');
  if (galleryGrid && window.GALLERY_PHOTOS) {
    const subjectButtons = [...document.querySelectorAll('[data-gallery-filter]')];
    const placeSelect = document.querySelector('[data-gallery-place]');
    const moreButton = document.querySelector('[data-gallery-more]');
    const count = document.querySelector('[data-gallery-count]');
    const lightbox = document.querySelector('[data-photo-lightbox]');
    const lightboxImage = lightbox?.querySelector('[data-lightbox-image]');
    const lightboxCaption = lightbox?.querySelector('[data-lightbox-caption]');
    let activeSubject = 'all';
    let activePlace = 'all';
    let visible = 48;
    let filtered = [];
    let lightboxIndex = 0;

    const setLightbox = (index) => {
      if (!filtered.length || !lightboxImage) return;
      lightboxIndex = (index + filtered.length) % filtered.length;
      const photo = filtered[lightboxIndex];
      lightboxImage.src = photo.full;
      lightboxImage.alt = photo.alt;
      if (lightboxCaption) lightboxCaption.textContent = photo.label;
    };
    const openLightbox = (index) => {
      if (!lightbox?.showModal) return;
      setLightbox(index);
      lightbox.showModal();
    };
    const renderGallery = () => {
      filtered = window.GALLERY_PHOTOS.filter((photo) => (activeSubject === 'all' || photo.subjects.includes(activeSubject)) && (activePlace === 'all' || photo.place === activePlace));
      const shown = filtered.slice(0, visible);
      galleryGrid.innerHTML = shown.map((photo, index) => `<figure class="gallery-photo"><button type="button" data-gallery-open="${index}" aria-label="Open ${escapeHtml(photo.label)}"><img src="${escapeHtml(photo.thumb)}" alt="${escapeHtml(photo.alt)}" loading="lazy" width="${photo.width}" height="${photo.height}"><figcaption>${escapeHtml(photo.label)}</figcaption></button></figure>`).join('');
      if (count) count.textContent = String(filtered.length);
      if (moreButton) moreButton.hidden = visible >= filtered.length;
    };
    subjectButtons.forEach((button) => button.addEventListener('click', () => {
      activeSubject = button.dataset.galleryFilter;
      visible = 48;
      subjectButtons.forEach((item) => item.classList.toggle('active', item === button));
      renderGallery();
    }));
    placeSelect?.addEventListener('change', () => { activePlace = placeSelect.value; visible = 48; renderGallery(); });
    moreButton?.addEventListener('click', () => { visible += 48; renderGallery(); });
    galleryGrid.addEventListener('click', (event) => {
      const button = event.target.closest('[data-gallery-open]');
      if (button) openLightbox(Number(button.dataset.galleryOpen));
    });
    lightbox?.querySelector('[data-lightbox-close]')?.addEventListener('click', () => lightbox.close());
    lightbox?.querySelector('[data-lightbox-prev]')?.addEventListener('click', () => setLightbox(lightboxIndex - 1));
    lightbox?.querySelector('[data-lightbox-next]')?.addEventListener('click', () => setLightbox(lightboxIndex + 1));
    lightbox?.addEventListener('click', (event) => { if (event.target === lightbox) lightbox.close(); });
    lightbox?.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowLeft') setLightbox(lightboxIndex - 1);
      if (event.key === 'ArrowRight') setLightbox(lightboxIndex + 1);
    });
    renderGallery();
  }

  const reveal = [...document.querySelectorAll('.reveal')];
  if ('IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) { entry.target.classList.add('visible'); observer.unobserve(entry.target); }
    }), { threshold: .12 });
    reveal.forEach((element) => observer.observe(element));
  } else reveal.forEach((element) => element.classList.add('visible'));
})();
