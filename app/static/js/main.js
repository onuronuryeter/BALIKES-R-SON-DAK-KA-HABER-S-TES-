// ===================================
// BALIKESİR SON DAKİKA HABER
// app/static/js/main.js
// ===================================

'use strict';

// ─── Tarih Formatlama ─────────────────────────────────────────
function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now - d) / 1000);

  if (diff < 60) return 'Az önce';
  if (diff < 3600) return Math.floor(diff / 60) + ' dakika önce';
  if (diff < 86400) return Math.floor(diff / 3600) + ' saat önce';
  if (diff < 604800) return Math.floor(diff / 86400) + ' gün önce';

  return d.toLocaleDateString('tr-TR', {
    day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

// Sayfadaki tüm data-time elementlerini formatla
function initDateTimes() {
  document.querySelectorAll('[data-time]').forEach(el => {
    const raw = el.getAttribute('data-time');
    if (raw) el.textContent = formatDate(raw);
  });
}

// ─── Ticker ───────────────────────────────────────────────────
function initTicker() {
  const track = document.querySelector('.ticker-content');
  if (!track) return;
  // İçeriği kopyala — sonsuz döngü efekti
  const clone = track.cloneNode(true);
  track.parentElement.appendChild(clone);
}

// ─── Hero Slider ─────────────────────────────────────────────
let heroSlideIndex = 0;
let heroSliderInterval;

function initHeroSlider() {
  const slides = document.querySelectorAll('.hero-slide');
  if (slides.length <= 1) return;
  
  startHeroSlider();
  
  // Pause on hover
  const sliderWrapper = document.querySelector('.hero-slider-wrapper');
  if (sliderWrapper) {
    sliderWrapper.addEventListener('mouseenter', () => clearInterval(heroSliderInterval));
    sliderWrapper.addEventListener('mouseleave', startHeroSlider);
  }
}

function startHeroSlider() {
  clearInterval(heroSliderInterval);
  heroSliderInterval = setInterval(() => {
    moveHeroSlider(1);
  }, 5000); // Her 5 saniyede bir geçiş
}

window.moveHeroSlider = function(step) {
  const slides = document.querySelectorAll('.hero-slide');
  if (!slides.length) return;
  
  let newIndex = heroSlideIndex + step;
  if (newIndex >= slides.length) newIndex = 0;
  if (newIndex < 0) newIndex = slides.length - 1;
  
  window.goToHeroSlide(newIndex);
}

window.goToHeroSlide = function(index) {
  const slides = document.querySelectorAll('.hero-slide');
  const slidesContainer = document.querySelector('.hero-slides');
  const dots = document.querySelectorAll('.hero-page-num');
  if (!slides.length || index < 0 || index >= slides.length) return;
  
  if (dots[heroSlideIndex]) dots[heroSlideIndex].classList.remove('active');
  
  heroSlideIndex = index;
  
  if (slidesContainer) {
    slidesContainer.style.transform = `translateX(-${index * 100}%)`;
  }
  
  if (dots[heroSlideIndex]) {
    dots[heroSlideIndex].classList.add('active');
    // Numarayı görünür alana kaydır (scrollIntoView)
    dots[heroSlideIndex].scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
  }
}

// ─── Toast Bildirimleri ───────────────────────────────────────
function showToast(message, type = 'info', duration = 3500) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  toast.innerHTML = `<span>${icons[type] || ''}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ─── Paylaşım ─────────────────────────────────────────────────
function initShareButtons() {
  document.querySelectorAll('.share-btn').forEach(btn => {
    btn.addEventListener('click', e => {
      const type = btn.dataset.share;
      const url = encodeURIComponent(window.location.href);
      const title = encodeURIComponent(document.title);
      let shareUrl = '';

      if (type === 'twitter') {
        shareUrl = `https://twitter.com/intent/tweet?url=${url}&text=${title}`;
      } else if (type === 'facebook') {
        shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${url}`;
      } else if (type === 'whatsapp') {
        shareUrl = `https://wa.me/?text=${title}%20${url}`;
      }

      if (shareUrl) window.open(shareUrl, '_blank', 'width=600,height=400');
    });
  });
}

// ─── Lazy Loading ─────────────────────────────────────────────
function initLazyLoad() {
  if (!('IntersectionObserver' in window)) return;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;
        if (img.dataset.src) {
          img.src = img.dataset.src;
          img.removeAttribute('data-src');
          observer.unobserve(img);
        }
      }
    });
  }, { rootMargin: '100px' });

  document.querySelectorAll('img[data-src]').forEach(img => observer.observe(img));
}

// ─── Admin: Login Formu ───────────────────────────────────────
function initAdminLogin() {
  const form = document.getElementById('login-form');
  if (!form) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = form.querySelector('[type=submit]');
    const errorEl = document.getElementById('login-error');
    const fd = new FormData(form);

    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span> Giriş yapılıyor...';
    if (errorEl) errorEl.style.display = 'none';

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        body: fd,
        credentials: 'include',
      });
      const data = await res.json();

      if (res.ok) {
        showToast('Giriş başarılı! Yönlendiriliyor...', 'success');
        setTimeout(() => window.location.href = '/admin', 800);
      } else {
        if (errorEl) { errorEl.textContent = data.detail || 'Giriş hatası'; errorEl.style.display = 'block'; }
        btn.disabled = false;
        btn.innerHTML = 'Giriş Yap';
      }
    } catch {
      if (errorEl) { errorEl.textContent = 'Sunucu bağlantı hatası'; errorEl.style.display = 'block'; }
      btn.disabled = false;
      btn.innerHTML = 'Giriş Yap';
    }
  });
}

// ─── Admin: Haber Sil ─────────────────────────────────────────
function initDeleteArticle() {
  document.querySelectorAll('.delete-article-btn').forEach(btn => {
    btn.addEventListener('click', async e => {
      const id = btn.dataset.id;
      const title = btn.dataset.title || 'bu haberi';
      if (!confirm(`"${title}" haberini silmek istediğinizden emin misiniz?`)) return;

      btn.disabled = true;
      try {
        const res = await fetch(`/api/articles/${id}`, {
          method: 'DELETE',
          credentials: 'include',
        });
        if (res.ok || res.status === 204) {
          btn.closest('tr')?.remove();
          showToast('Haber silindi.', 'success');
        } else {
          showToast('Silme işlemi başarısız.', 'error');
          btn.disabled = false;
        }
      } catch {
        showToast('Bağlantı hatası.', 'error');
        btn.disabled = false;
      }
    });
  });
}

// ─── Admin: Haber Yayınla ─────────────────────────────────────
function initPublishArticle() {
  document.querySelectorAll('.publish-article-btn').forEach(btn => {
    btn.addEventListener('click', async e => {
      const id = btn.dataset.id;
      btn.disabled = true;
      try {
        const res = await fetch(`/api/articles/${id}/publish`, {
          method: 'POST',
          credentials: 'include',
        });
        if (res.ok) {
          showToast('Haber yayınlandı!', 'success');
          setTimeout(() => window.location.reload(), 800);
        } else {
          showToast('Yayınlama başarısız.', 'error');
          btn.disabled = false;
        }
      } catch {
        showToast('Bağlantı hatası.', 'error');
        btn.disabled = false;
      }
    });
  });
}

// ─── Admin: Haber Formu ───────────────────────────────────────
function initArticleForm() {
  const form = document.getElementById('article-form');
  if (!form) return;

  // Başlıktan otomatik slug
  const titleInput = document.getElementById('title');
  const slugInput = document.getElementById('slug');
  if (titleInput && slugInput) {
    let slugManual = slugInput.value.length > 0;
    titleInput.addEventListener('input', () => {
      if (slugManual) return;
      slugInput.value = titleInput.value
        .toLowerCase()
        .replace(/ğ/g, 'g').replace(/ü/g, 'u').replace(/ş/g, 's')
        .replace(/ı/g, 'i').replace(/ö/g, 'o').replace(/ç/g, 'c')
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .trim();
    });
    slugInput.addEventListener('input', () => { slugManual = slugInput.value.length > 0; });
  }

  // Medya yükleme fonksiyonu
  async function uploadMediaFile(file, loadingEl) {
    if (loadingEl) loadingEl.style.display = 'inline-block';
    const fd = new FormData();
    fd.append('file', file);
    
    try {
      const res = await fetch('/api/articles/upload_media', {
        method: 'POST',
        body: fd,
        credentials: 'include'
      });
      const data = await res.json();
      if (loadingEl) loadingEl.style.display = 'none';
      if (res.ok && data.url) {
        return data.url;
      } else {
        showToast(data.detail || 'Dosya yüklenemedi', 'error');
        return null;
      }
    } catch (e) {
      if (loadingEl) loadingEl.style.display = 'none';
      showToast('Yükleme hatası', 'error');
      return null;
    }
  }

  // Kapak görseli upload event'i
  // ─── Kapak Görseli İşlemleri ve Önizlemesi ────────────────────
  const featuredUpload = document.getElementById('featured_image_upload');
  const featuredUrlInput = document.getElementById('featured_image');
  const featuredLoading = document.getElementById('featured_image_loading');
  const featuredPreviewBox = document.getElementById('featured_image_preview_box');
  const featuredPreviewImg = document.getElementById('featured_image_preview_img');
  const featuredRemoveBtn = document.getElementById('featured_image_remove_btn');
  const featuredConfirm = document.getElementById('featured_image_confirm');
  const featuredConfirmFilename = document.getElementById('featured_confirm_filename');

  function updateFeaturedPreview(url, filename = '') {
    if (url) {
      if (featuredPreviewImg) featuredPreviewImg.src = url;
      if (featuredPreviewBox) featuredPreviewBox.style.display = 'block';
      if (filename && featuredConfirm) {
        if (featuredConfirmFilename) featuredConfirmFilename.textContent = `(${filename})`;
        featuredConfirm.style.display = 'flex';
      }
    } else {
      if (featuredPreviewImg) featuredPreviewImg.src = '';
      if (featuredPreviewBox) featuredPreviewBox.style.display = 'none';
      if (featuredConfirm) featuredConfirm.style.display = 'none';
    }
  }

  if (featuredUpload && featuredUrlInput) {
    featuredUpload.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      if (featuredConfirm) featuredConfirm.style.display = 'none';
      const url = await uploadMediaFile(file, featuredLoading);
      if (url) {
        featuredUrlInput.value = url;
        updateFeaturedPreview(url, file.name);
        showToast(`✅ Kapak görseli başarıyla yüklendi! (${file.name})`, 'success');
      }
      e.target.value = ''; // inputu sıfırla
    });
  }

  if (featuredUrlInput) {
    featuredUrlInput.addEventListener('input', () => {
      const url = featuredUrlInput.value.trim();
      if (featuredConfirm) featuredConfirm.style.display = 'none';
      updateFeaturedPreview(url);
    });
  }

  if (featuredRemoveBtn) {
    featuredRemoveBtn.addEventListener('click', () => {
      if (featuredUrlInput) featuredUrlInput.value = '';
      updateFeaturedPreview('');
      showToast('Kapak görseli kaldırıldı', 'info');
    });
  }

  // ─── Çoklu Bölüm & Görsel Sistemi (En Üst, Orta, En Son) ─────────
  const contentHidden = document.getElementById('content');
  const sectionedContainer = document.getElementById('sectioned-editor-container');
  const classicContainer = document.getElementById('classic-editor-container');
  const classicTextarea = document.getElementById('classic-content-textarea');
  const tabBtnSectioned = document.getElementById('tab-btn-sectioned');
  const tabBtnClassic = document.getElementById('tab-btn-classic');
  const sectionsWrapper = document.getElementById('sections-wrapper');
  const addNewSectionBtn = document.getElementById('add-new-section-btn');
  let activeTab = 'sectioned';

  // Canlı Önizleme Güncelle
  function updateSectionPreview(card) {
    const urlInput = card.querySelector('.section-img-url');
    const prevContainer = card.querySelector('.section-preview-container');
    const prevImg = card.querySelector('.section-image-preview');
    const box = card.querySelector('.section-image-box');
    const url = urlInput ? urlInput.value.trim() : '';

    if (url) {
      prevImg.src = url;
      prevContainer.style.display = 'block';
      box.classList.add('has-image');
    } else {
      prevImg.src = '';
      prevContainer.style.display = 'none';
      box.classList.remove('has-image');
    }
  }

  // Yükleme Doğrulama Bildirimi Göster
  function showSectionConfirmation(card, filename = '') {
    const badge = card.querySelector('.section-confirm-badge');
    const box = card.querySelector('.section-image-box');
    if (badge) {
      const nameEl = badge.querySelector('.confirm-filename');
      if (nameEl) nameEl.textContent = filename ? `(${filename})` : '';
      badge.style.display = 'flex';
    }
    if (box) {
      box.classList.add('uploaded');
    }
  }

  // Yükleme Doğrulama Bildirimi Gizle
  function hideSectionConfirmation(card) {
    const badge = card.querySelector('.section-confirm-badge');
    const box = card.querySelector('.section-image-box');
    if (badge) badge.style.display = 'none';
    if (box) box.classList.remove('uploaded');
  }

  // Bölümleri Semantik HTML'e Derle
  function compileSectionsToContent() {
    if (!sectionsWrapper || !contentHidden) return;
    const cards = sectionsWrapper.querySelectorAll('.content-section-card');
    const parts = [];

    cards.forEach((card) => {
      const textArea = card.querySelector('.section-text');
      const text = textArea ? textArea.value.trim() : '';
      const urlInput = card.querySelector('.section-img-url');
      const imgUrl = urlInput ? urlInput.value.trim() : '';
      const captionInput = card.querySelector('.section-img-caption');
      const imgCaption = captionInput ? captionInput.value.trim() : '';
      const alignSelect = card.querySelector('.section-img-align');
      const imgAlign = alignSelect ? alignSelect.value : 'full-width';

      const headingInput = card.querySelector('.section-heading');
      const headingText = headingInput ? headingInput.value.trim() : '';

      // 1. Alt Başlık Bloğu
      if (headingText) {
        parts.push(`<h3><strong>${headingText}</strong></h3>`);
      }

      // 2. Metin Bloğu
      if (text) {
        if (text.startsWith('<p>') || text.includes('</p>')) {
          parts.push(text);
        } else {
          const paragraphs = text.split(/\n\s*\n/).map(s => s.trim()).filter(Boolean);
          paragraphs.forEach(p => {
            parts.push(`<p>${p.replace(/\n/g, '<br>')}</p>`);
          });
        }
      }

      // 3. Görsel Bloğu
      if (imgUrl) {
        const captionHtml = imgCaption ? `\n  <figcaption>${imgCaption}</figcaption>` : '';
        const figHtml = `<figure class="article-figure ${imgAlign}">\n  <img src="${imgUrl}" alt="${imgCaption || 'Haber Görseli'}" loading="lazy">${captionHtml}\n</figure>`;
        parts.push(figHtml);
      }
    });

    const compiledHtml = parts.join('\n\n');
    contentHidden.value = compiledHtml;
    if (classicTextarea && activeTab !== 'classic') {
      classicTextarea.value = compiledHtml;
    }

    // Kapak görseli boşsa, ilk bölümdeki görseli otomatik kapak yap
    if (featuredUrlInput && (!featuredUrlInput.value || featuredUrlInput.value.trim() === '' || featuredUrlInput.value === 'None')) {
      const allCards = sectionsWrapper.querySelectorAll('.content-section-card');
      for (const c of allCards) {
        const u = c.querySelector('.section-img-url');
        if (u && u.value.trim() && u.value.trim() !== 'None') {
          featuredUrlInput.value = u.value.trim();
          updateFeaturedPreview(u.value.trim());
          break;
        }
      }
    }
  }

  // Bir Bölüm Kartına Event Dinleyicilerini Bağla
  function setupSectionCard(card) {
    const fileInput = card.querySelector('.section-file-input');
    const urlInput = card.querySelector('.section-img-url');
    const captionInput = card.querySelector('.section-img-caption');
    const alignSelect = card.querySelector('.section-img-align');
    const headingInput = card.querySelector('.section-heading');
    const textArea = card.querySelector('.section-text');
    const removeBtn = card.querySelector('.section-image-remove-btn');
    const spinner = card.querySelector('.section-upload-spinner');
    const deleteCardBtn = card.querySelector('.section-delete-card-btn');

    if (fileInput) {
      fileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        hideSectionConfirmation(card);
        const url = await uploadMediaFile(file, spinner);
        if (url) {
          if (urlInput) urlInput.value = url;
          updateSectionPreview(card);
          showSectionConfirmation(card, file.name);
          // Kapak görseli henüz yoksa, bu görseli otomatik kapak yap
          if (featuredUrlInput && (!featuredUrlInput.value || featuredUrlInput.value.trim() === '' || featuredUrlInput.value === 'None')) {
            featuredUrlInput.value = url;
            updateFeaturedPreview(url, file.name);
          }
          compileSectionsToContent();
          showToast(`✅ Görsel yüklendi: ${file.name}`, 'success');
        }
        e.target.value = '';
      });
    }

    if (urlInput) {
      urlInput.addEventListener('input', () => {
        hideSectionConfirmation(card);
        updateSectionPreview(card);
        compileSectionsToContent();
      });
      urlInput.addEventListener('change', () => {
        updateSectionPreview(card);
        compileSectionsToContent();
      });
    }

    if (captionInput) {
      captionInput.addEventListener('input', compileSectionsToContent);
    }

    if (alignSelect) {
      alignSelect.addEventListener('change', compileSectionsToContent);
    }

    if (headingInput) {
      headingInput.addEventListener('input', compileSectionsToContent);
    }

    if (textArea) {
      textArea.addEventListener('input', compileSectionsToContent);
    }

    if (removeBtn) {
      removeBtn.addEventListener('click', () => {
        if (urlInput) urlInput.value = '';
        if (captionInput) captionInput.value = '';
        hideSectionConfirmation(card);
        updateSectionPreview(card);
        compileSectionsToContent();
        showToast('Görsel kaldırıldı', 'info');
      });
    }

    if (deleteCardBtn) {
      deleteCardBtn.addEventListener('click', () => {
        card.remove();
        compileSectionsToContent();
        showToast('Bölüm kaldırıldı', 'info');
      });
    }
  }

  // Mevcut Kartları Başlat
  if (sectionsWrapper) {
    sectionsWrapper.querySelectorAll('.content-section-card').forEach(setupSectionCard);
  }

  // Yeni Bölüm & Görsel Ekle Butonu
  if (addNewSectionBtn && sectionsWrapper) {
    addNewSectionBtn.addEventListener('click', () => {
      const existingCards = sectionsWrapper.querySelectorAll('.content-section-card');
      const newIdx = existingCards.length + 1;

      const card = document.createElement('div');
      card.className = 'content-section-card';
      card.dataset.sectionIndex = newIdx;
      card.innerHTML = `
        <div class="section-card-header">
          <span class="section-badge custom">📍 ${newIdx}. BÖLÜM — EK BÖLÜM</span>
          <button type="button" class="btn btn-secondary btn-sm section-delete-card-btn" style="color:#dc2626;border-color:#fca5a5;">🗑️ Bu Bölümü Sil</button>
        </div>
        <input type="text" class="form-control section-heading" placeholder="Siyah Kalın Alt Başlık (İsteğe bağlı)..." style="margin-bottom:8px;font-weight:bold;color:#000;">
        <textarea class="form-control section-text" rows="4" placeholder="Bu bölümün haber metni..."></textarea>
        
        <div class="section-image-box">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
            <span style="font-size:13px;font-weight:600;color:#334155;">🖼️ ${newIdx}. Görsel Alanı</span>
            <div style="display:flex;gap:8px;align-items:center;">
              <label class="btn btn-secondary btn-sm" style="cursor:pointer;margin:0;">
                💻 PC'den Yükle
                <input type="file" class="section-file-input" accept="image/*" style="display:none;">
              </label>
              <span class="section-upload-spinner" style="display:none;font-size:12px;color:#6c757d;">Yükleniyor...</span>
            </div>
          </div>

          <!-- Doğrulama Bildirimi -->
          <div class="section-confirm-badge upload-confirmation-alert" style="display:none;">
            <span class="confirm-icon">✅</span>
            <span>Görsel başarıyla yüklendi!</span>
            <span class="confirm-filename"></span>
          </div>

          <div class="section-preview-container" style="display:none;">
            <div class="section-image-preview-wrapper">
              <img src="" class="section-image-preview" alt="Önizleme">
              <button type="button" class="section-image-remove-btn" title="Görseli Kaldır">✕</button>
            </div>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px;">
            <input type="url" class="form-control form-control-sm section-img-url" placeholder="veya Görsel URL'si (https://...)">
            <input type="text" class="form-control form-control-sm section-img-caption" placeholder="Görsel Altyazısı / Açıklaması">
          </div>
          <div style="margin-top:8px;display:flex;align-items:center;gap:12px;">
            <span style="font-size:12px;color:#64748b;">Hizalama:</span>
            <select class="form-control form-control-sm section-img-align" style="width:auto;display:inline-block;">
              <option value="full-width">Tam Genişlik (Önerilen)</option>
              <option value="align-center">Ortalanmış</option>
              <option value="align-left">Sola Hizalı</option>
              <option value="align-right">Sağa Hizalı</option>
            </select>
          </div>
        </div>
      `;

      sectionsWrapper.appendChild(card);
      setupSectionCard(card);
      card.querySelector('.section-text')?.focus();
      showToast(`${newIdx}. Bölüm eklendi`, 'success');
    });
  }

  // HTML'den Bölümlere Akıllı Ayrıştırma (Parser)
  function parseHtmlIntoSections(html) {
    if (!html || !html.trim() || html.trim() === 'None' || !sectionsWrapper) return;
    const temp = document.createElement('div');
    temp.innerHTML = html;

    const figuresAndImgs = temp.querySelectorAll('figure, img');
    const existingCards = sectionsWrapper.querySelectorAll('.content-section-card');

    if (figuresAndImgs.length > 0) {
      // Görseller var: Her görseli ve öncesindeki metni bölümlere ayır
      let currentSectionIdx = 0;
      let textBuffer = [];

      temp.childNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) {
          const isFig = node.tagName.toLowerCase() === 'figure';
          const isImg = node.tagName.toLowerCase() === 'img';

          if (isFig || isImg) {
            // Bir bölüm doldur veya oluştur
            let card = existingCards[currentSectionIdx];
            if (!card && addNewSectionBtn) {
              addNewSectionBtn.click();
              card = sectionsWrapper.querySelectorAll('.content-section-card')[currentSectionIdx];
            }

            if (card) {
              // Metni yaz
              const txtArea = card.querySelector('.section-text');
              if (txtArea) txtArea.value = textBuffer.join('\n\n');
              textBuffer = [];

              // Görseli yaz
              const imgEl = isFig ? node.querySelector('img') : node;
              const figCap = isFig ? node.querySelector('figcaption') : null;
              const urlInput = card.querySelector('.section-img-url');
              const capInput = card.querySelector('.section-img-caption');
              const alignSelect = card.querySelector('.section-img-align');

              if (imgEl && urlInput) {
                urlInput.value = imgEl.getAttribute('src') || '';
              }
              if (capInput) {
                capInput.value = figCap ? figCap.textContent.trim() : (imgEl ? imgEl.getAttribute('alt') || '' : '');
              }
              if (alignSelect && isFig) {
                if (node.classList.contains('align-left')) alignSelect.value = 'align-left';
                else if (node.classList.contains('align-right')) alignSelect.value = 'align-right';
                else if (node.classList.contains('align-center')) alignSelect.value = 'align-center';
                else alignSelect.value = 'full-width';
              }
              updateSectionPreview(card);
            }
            currentSectionIdx++;
          } else if (node.tagName && node.tagName.toLowerCase() === 'h3') {
            let card = existingCards[currentSectionIdx];
            if (!card && addNewSectionBtn) {
              addNewSectionBtn.click();
              existingCards = sectionsWrapper.querySelectorAll('.content-section-card');
              card = existingCards[currentSectionIdx];
            }
            if (card) {
              const headingInput = card.querySelector('.section-heading');
              if (headingInput && !headingInput.value) {
                headingInput.value = node.textContent.trim();
              } else {
                const pText = node.textContent.trim();
                if (pText) textBuffer.push(`<h3><strong>${pText}</strong></h3>`);
              }
            }
          } else {
            const pText = node.innerHTML ? node.innerHTML.trim() : node.textContent.trim();
            if (pText) textBuffer.push(pText);
          }
        } else if (node.nodeType === Node.TEXT_NODE) {
          const t = node.textContent.trim();
          if (t) textBuffer.push(t);
        }
      });

      // Kalan metni son bölüme ata
      if (textBuffer.length > 0) {
        let card = existingCards[currentSectionIdx];
        if (!card && addNewSectionBtn) {
          addNewSectionBtn.click();
          card = sectionsWrapper.querySelectorAll('.content-section-card')[currentSectionIdx];
        }
        if (card) {
          const txtArea = card.querySelector('.section-text');
          if (txtArea) txtArea.value = textBuffer.join('\n\n');
        }
      }
    } else {
      // Görsel yok: Paragrafları 3 bölüme dengeli dağıt
      const pElements = temp.querySelectorAll('p');
      if (pElements.length >= 3) {
        const pTexts = Array.from(pElements).map(p => p.textContent.trim()).filter(Boolean);
        const chunkSize = Math.ceil(pTexts.length / 3);
        const sec1 = pTexts.slice(0, chunkSize).join('\n\n');
        const sec2 = pTexts.slice(chunkSize, chunkSize * 2).join('\n\n');
        const sec3 = pTexts.slice(chunkSize * 2).join('\n\n');

        if (existingCards[0]) existingCards[0].querySelector('.section-text').value = sec1;
        if (existingCards[1]) existingCards[1].querySelector('.section-text').value = sec2;
        if (existingCards[2]) existingCards[2].querySelector('.section-text').value = sec3;
      } else {
        // 1-2 paragraf veya düz metin
        if (existingCards[0]) {
          existingCards[0].querySelector('.section-text').value = temp.textContent.trim();
        }
      }
    }
  }

  // Sayfa İlk Açıldığında Mevcut İçeriği Ayrıştır
  if (contentHidden && contentHidden.value && contentHidden.value.trim() && contentHidden.value.trim() !== 'None') {
    if (classicTextarea) classicTextarea.value = contentHidden.value;
    parseHtmlIntoSections(contentHidden.value);
  } else {
    if (contentHidden) contentHidden.value = '';
    if (classicTextarea) classicTextarea.value = '';
  }

  // Sekme Değiştirme (Bölümlü <-> Klasik)
  if (tabBtnSectioned && tabBtnClassic) {
    tabBtnSectioned.addEventListener('click', () => {
      if (activeTab === 'classic' && classicTextarea) {
        parseHtmlIntoSections(classicTextarea.value);
      }
      activeTab = 'sectioned';
      tabBtnSectioned.classList.add('active');
      tabBtnClassic.classList.remove('active');
      if (sectionedContainer) sectionedContainer.style.display = 'block';
      if (classicContainer) classicContainer.style.display = 'none';
      compileSectionsToContent();
    });

    tabBtnClassic.addEventListener('click', () => {
      compileSectionsToContent();
      if (classicTextarea && contentHidden) {
        classicTextarea.value = contentHidden.value;
      }
      activeTab = 'classic';
      tabBtnClassic.classList.add('active');
      tabBtnSectioned.classList.remove('active');
      if (sectionedContainer) sectionedContainer.style.display = 'none';
      if (classicContainer) classicContainer.style.display = 'block';
    });
  }

  // Klasik Editör: Hızlı Görsel Ekleme Araçları
  const classicPcUpload = document.getElementById('classic-pc-upload');
  const classicUploadSpinner = document.getElementById('classic-upload-spinner');
  if (classicPcUpload && classicTextarea) {
    classicPcUpload.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const url = await uploadMediaFile(file, classicUploadSpinner);
      if (url) {
        const figTag = `\n<figure class="article-figure full-width">\n  <img src="${url}" alt="Haber Görseli" loading="lazy">\n  <figcaption></figcaption>\n</figure>\n`;
        const start = classicTextarea.selectionStart;
        const end = classicTextarea.selectionEnd;
        const text = classicTextarea.value;
        classicTextarea.value = text.substring(0, start) + figTag + text.substring(end);
        contentHidden.value = classicTextarea.value;
        showToast('Görsel metne eklendi!', 'success');
      }
      e.target.value = '';
    });
  }

  const quickTopBtn = document.getElementById('btn-quick-top-img');
  const quickMidBtn = document.getElementById('btn-quick-mid-img');
  const quickBotBtn = document.getElementById('btn-quick-bot-img');

  function insertQuickImageToClassic(position) {
    if (!classicTextarea) return;
    const url = prompt('Eklemek istediğiniz görsel URL adresini girin:');
    if (!url) return;
    const caption = prompt('Görsel altyazısı / açıklaması (isteğe bağlı):') || '';
    const capHtml = caption ? `\n  <figcaption>${caption}</figcaption>` : '';
    const figHtml = `\n<figure class="article-figure full-width">\n  <img src="${url}" alt="${caption || 'Haber Görseli'}" loading="lazy">${capHtml}\n</figure>\n`;

    const text = classicTextarea.value;
    if (position === 'top') {
      classicTextarea.value = figHtml + '\n' + text;
    } else if (position === 'bottom') {
      classicTextarea.value = text + '\n' + figHtml;
    } else if (position === 'mid') {
      const mid = Math.floor(text.length / 2);
      const nextBreak = text.indexOf('\n', mid);
      const insertAt = nextBreak !== -1 ? nextBreak : mid;
      classicTextarea.value = text.substring(0, insertAt) + '\n' + figHtml + '\n' + text.substring(insertAt);
    }
    contentHidden.value = classicTextarea.value;
    showToast('Görsel başarıyla yerleştirildi!', 'success');
  }

  if (quickTopBtn) quickTopBtn.addEventListener('click', () => insertQuickImageToClassic('top'));
  if (quickMidBtn) quickMidBtn.addEventListener('click', () => insertQuickImageToClassic('mid'));
  if (quickBotBtn) quickBotBtn.addEventListener('click', () => insertQuickImageToClassic('bottom'));

  // Karakter sayacı (SEO alanları)
  document.querySelectorAll('[data-maxlength]').forEach(el => {
    const max = parseInt(el.dataset.maxlength);
    const hint = el.parentElement.querySelector('.char-count');
    if (!hint) return;
    const update = () => {
      const len = el.value.length;
      hint.textContent = `${len}/${max}`;
      hint.style.color = len > max ? '#dc2626' : '#6c757d';
    };
    el.addEventListener('input', update);
    update();
  });

  // Form gönder
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = form.querySelector('[type=submit]');
    const action = form.dataset.action || 'create';
    const articleId = form.dataset.id;
    const method = action === 'edit' ? 'PATCH' : 'POST';
    const url = action === 'edit' ? `/api/articles/${articleId}` : '/api/articles/';

    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span> Kaydediliyor...';

    // İçeriği son kez aktif sekmeye göre senkronize et
    if (activeTab === 'classic' && classicTextarea && contentHidden) {
      contentHidden.value = classicTextarea.value;
    } else {
      compileSectionsToContent();
    }

    const fd = new FormData(form);
    const body = {};
    fd.forEach((v, k) => {
      const val = typeof v === 'string' ? v.trim() : v;
      if (val !== '' && val !== 'None') body[k] = val;
    });

    // Explicitly ensure content is assigned and sanitized
    if (contentHidden) {
      const cv = contentHidden.value.trim();
      body.content = (cv === 'None') ? '' : cv;
    }

    // Kapak görseli kontrolü: Boşsa bölümlerdeki ilk resmi kapak yap
    if (!body.featured_image || body.featured_image === 'None') {
      if (featuredUrlInput && featuredUrlInput.value && featuredUrlInput.value.trim() !== '' && featuredUrlInput.value !== 'None') {
        body.featured_image = featuredUrlInput.value.trim();
      } else if (sectionsWrapper) {
        const allImgs = sectionsWrapper.querySelectorAll('.section-img-url');
        for (const imgEl of allImgs) {
          if (imgEl.value && imgEl.value.trim() && imgEl.value.trim() !== 'None') {
            body.featured_image = imgEl.value.trim();
            break;
          }
        }
      }
    }

    // Checkbox'ları işle
    body.is_breaking = form.querySelector('#is_breaking')?.checked || false;
    body.is_featured = form.querySelector('#is_featured')?.checked || false;
    if (body.category_id) body.category_id = parseInt(body.category_id);

    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        credentials: 'include',
      });
      const data = await res.json();
      if (res.ok) {
        showToast(action === 'edit' ? 'Haber güncellendi!' : 'Haber oluşturuldu!', 'success');
        setTimeout(() => window.location.href = '/admin/articles', 900);
      } else {
        showToast(data.detail || 'Kayıt hatası.', 'error');
        btn.disabled = false;
        btn.innerHTML = action === 'edit' ? 'Güncelle' : 'Kaydet';
      }
    } catch {
      showToast('Bağlantı hatası.', 'error');
      btn.disabled = false;
      btn.innerHTML = 'Kaydet';
    }
  });
}

// ─── Admin: Kaynak Yönetimi ───────────────────────────────────
function initSourceDelete() {
  document.querySelectorAll('.delete-source-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;
      if (!confirm('Bu kaynağı silmek istediğinizden emin misiniz?')) return;
      btn.disabled = true;
      try {
        const res = await fetch(`/api/sources/${id}`, { method: 'DELETE', credentials: 'include' });
        if (res.ok || res.status === 204) {
          btn.closest('tr')?.remove();
          showToast('Kaynak silindi.', 'success');
        } else {
          showToast('Silme başarısız.', 'error');
          btn.disabled = false;
        }
      } catch {
        showToast('Bağlantı hatası.', 'error');
        btn.disabled = false;
      }
    });
  });
}

// ─── Admin: Kaynak Toggle ──────────────────────────────────────
function initSourceToggle() {
  document.querySelectorAll('.toggle-source-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;
      const active = btn.dataset.active === 'true';
      try {
        const res = await fetch(`/api/sources/${id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ is_active: !active }),
          credentials: 'include',
        });
        if (res.ok) {
          showToast(active ? 'Kaynak pasif yapıldı.' : 'Kaynak aktif yapıldı.', 'success');
          setTimeout(() => window.location.reload(), 600);
        }
      } catch { showToast('Hata.', 'error'); }
    });
  });
}

// ─── Admin: Logout ─────────────────────────────────────────────
function initLogout() {
  const btn = document.getElementById('logout-btn');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    window.location.href = '/admin/login';
  });
}

// ─── Güncel saat - tarih ────────────────────────────────────────
function initClock() {
  const el = document.getElementById('current-datetime');
  if (!el) return;
  const update = () => {
    el.textContent = new Date().toLocaleDateString('tr-TR', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    });
  };
  update();
  setInterval(update, 60000);
}

// ─── INIT ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initDateTimes();
  initTicker();
  initHeroSlider();
  initShareButtons();
  initLazyLoad();
  initAdminLogin();
  initDeleteArticle();
  initPublishArticle();
  initArticleForm();
  initSourceDelete();
  initSourceToggle();
  initLogout();
  initClock();
});
