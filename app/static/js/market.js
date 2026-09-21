/**
 * Balıkesir Son Dakika Haber
 * Piyasa Takip Sistemi
 */

document.addEventListener('DOMContentLoaded', () => {
  const marketTicker = document.getElementById('market-ticker');
  if (!marketTicker) return;

  const marketDataContainer = document.getElementById('market-data');
  const marketUpdateTime = document.getElementById('market-update-time');

  async function fetchMarketData() {
    try {
      const response = await fetch('/api/market/prices');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      renderMarketData(data);
    } catch (error) {
      console.error('[MARKET API] Veri alınamadı:', error);
      // Let it fail silently, keep existing or empty state
    }
  }

  function formatPrice(item) {
    if (item.status === 'unavailable' || item.price === null) {
      return 'Veri alınamadı';
    }

    try {
      if (item.currency === 'TRY') {
        // Döviz kurları için (USD/TRY, EUR/TRY vb.) 4 ondalık
        return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY', minimumFractionDigits: 4, maximumFractionDigits: 4 }).format(item.price);
      } else if (item.currency === 'USD') {
        // Altın ve BTC için
        let minFrac = 2;
        let maxFrac = 2;
        if (item.id === 'btc') {
            minFrac = 0; // BTC usually doesn't need decimals in UI when price is high
            maxFrac = 0;
        }
        return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'USD', minimumFractionDigits: minFrac, maximumFractionDigits: maxFrac }).format(item.price);
      }
      return item.price; // Fallback
    } catch (e) {
      return item.price;
    }
  }

  function renderMarketData(data) {
    if (!data || !data.items || !Array.isArray(data.items)) return;

    let html = '';
    data.items.forEach(item => {
      let icon = '';
      if (item.id === 'gold') icon = '🥇';
      else if (item.id === 'btc') icon = '₿';
      else if (item.id === 'usdtry') icon = '💵';
      else if (item.id === 'eurtry') icon = '💶';

      const priceStr = formatPrice(item);
      const isUnavailable = item.status === 'unavailable';
      const tooltipText = item.rateType === 'reference' ? 'Canlı (Referans Kur) - ' + item.source : 'Canlı - ' + item.source;
      const statusClass = isUnavailable ? 'market-unavailable' : 'market-live';

      html += `
        <div class="market-item" title="${tooltipText}">
          <span class="market-name">${icon} ${item.name}</span>
          <span class="market-price ${isUnavailable ? 'unavailable-text' : ''}">${priceStr}</span>
          <span class="market-badge ${statusClass}">CANLI</span>
        </div>
      `;
    });

    marketDataContainer.innerHTML = html;

    if (data.updatedAt && marketUpdateTime) {
      try {
        const d = new Date(data.updatedAt);
        const timeStr = d.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        marketUpdateTime.textContent = timeStr;
      } catch (e) {
        console.error(e);
      }
    }
  }

  // Initial fetch
  fetchMarketData();

  // Refresh every 60 seconds to not overload our own API, though gold-api is cached for 10s and frankfurter for 1h
  setInterval(fetchMarketData, 60000);
});
