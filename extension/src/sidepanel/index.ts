import { Chart, ScatterController, PointElement, LinearScale, Tooltip } from 'chart.js';
import type { VehicleListing } from '../types/canonical';
import type { CheckListingStatusResponse, GetAllListingsResponse, SaveListingResponse } from '../types/messages';

Chart.register(ScatterController, PointElement, LinearScale, Tooltip);

let allListings: VehicleListing[] = [];
let currentUrl: string | null = null;
let currentParsedListing: Record<string, unknown> | null = null;
let chartInstance: Chart | null = null;
let lastSavedId: number | null = null;

const saveBtn = document.getElementById('save-btn') as HTMLButtonElement;
const statusText = document.getElementById('status-text') as HTMLSpanElement;
const resultsCount = document.getElementById('results-count') as HTMLDivElement;
const listingsList = document.getElementById('listings-list') as HTMLUListElement;
const chartCanvas = document.getElementById('scatter-chart') as HTMLCanvasElement;

const filterBrand = document.getElementById('filter-brand') as HTMLInputElement;
const filterModel = document.getElementById('filter-model') as HTMLInputElement;
const filterYearMin = document.getElementById('filter-year-min') as HTMLInputElement;
const filterYearMax = document.getElementById('filter-year-max') as HTMLInputElement;
const filterKmMin = document.getElementById('filter-km-min') as HTMLInputElement;
const filterKmMax = document.getElementById('filter-km-max') as HTMLInputElement;
const filterPriceMin = document.getElementById('filter-price-min') as HTMLInputElement;
const filterPriceMax = document.getElementById('filter-price-max') as HTMLInputElement;
const filterSource = document.getElementById('filter-source') as HTMLSelectElement;

function getFilteredListings(): VehicleListing[] {
  return allListings.filter(l => {
    if (filterBrand.value && !l.brand?.toLowerCase().includes(filterBrand.value.toLowerCase())) return false;
    if (filterModel.value && !l.model?.toLowerCase().includes(filterModel.value.toLowerCase())) return false;
    if (filterYearMin.value && (l.year ?? 0) < parseInt(filterYearMin.value)) return false;
    if (filterYearMax.value && (l.year ?? 9999) > parseInt(filterYearMax.value)) return false;
    if (filterKmMin.value && (l.mileage_km ?? 0) < parseInt(filterKmMin.value)) return false;
    if (filterKmMax.value && (l.mileage_km ?? Infinity) > parseInt(filterKmMax.value)) return false;
    if (filterPriceMin.value && (l.price_amount ?? 0) < parseInt(filterPriceMin.value)) return false;
    if (filterPriceMax.value && (l.price_amount ?? Infinity) > parseInt(filterPriceMax.value)) return false;
    if (filterSource.value && l.source_marketplace !== filterSource.value) return false;
    return true;
  });
}

function priceToColor(price: number | null, minPrice: number, maxPrice: number): string {
  if (price === null) return 'rgba(150,150,150,0.7)';
  const range = maxPrice - minPrice || 1;
  const ratio = (price - minPrice) / range;
  const r = Math.round(255 * ratio);
  const b = Math.round(255 * (1 - ratio));
  return `rgba(${r},0,${b},0.7)`;
}

function renderChart(listings: VehicleListing[]): void {
  if (chartInstance) {
    chartInstance.destroy();
    chartInstance = null;
  }

  const prices = listings.map(l => l.price_amount).filter((p): p is number => p !== null);
  const minPrice = Math.min(...prices, 0);
  const maxPrice = Math.max(...prices, 1);

  const data = listings
    .filter(l => l.year !== null && l.mileage_km !== null)
    .map(l => ({
      x: l.year!,
      y: l.mileage_km!,
      price: l.price_amount,
      id: l.id,
    }));

  chartInstance = new Chart(chartCanvas, {
    type: 'scatter',
    data: {
      datasets: [{
        label: 'Listings',
        data: data as Array<{ x: number; y: number }>,
        backgroundColor: data.map(d =>
          d.id === lastSavedId ? 'rgba(255,200,0,0.9)' : priceToColor(d.price, minPrice, maxPrice)
        ),
        pointRadius: data.map(d => d.id === lastSavedId ? 8 : 5),
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { title: { display: true, text: 'Year' } },
        y: { title: { display: true, text: 'Mileage (km)' } },
      },
    },
  });
}

function renderListings(listings: VehicleListing[]): void {
  listingsList.innerHTML = '';
  resultsCount.textContent = `${listings.length} listing${listings.length !== 1 ? 's' : ''}`;

  for (const l of listings) {
    const li = document.createElement('li');
    li.className = 'listing-item';
    if (l.id === lastSavedId) li.classList.add('highlight');

    li.innerHTML = `
      <div class="listing-title">${l.brand ?? '?'} ${l.model ?? ''}</div>
      <div class="listing-meta">${l.year ?? '?'} · ${l.mileage_km?.toLocaleString() ?? '?'} km · ${l.source_marketplace}</div>
      <div class="listing-price">${l.price_amount ? l.price_amount.toLocaleString() + ' ' + (l.price_currency ?? '€') : '?'}</div>
      <a href="${l.url}" target="_blank">View listing ↗</a>
    `;
    listingsList.appendChild(li);
  }

  if (lastSavedId !== null) {
    setTimeout(() => {
      const highlighted = listingsList.querySelector('.listing-item.highlight');
      if (highlighted) highlighted.classList.remove('highlight');
      lastSavedId = null;
      renderChart(getFilteredListings());
    }, 3000);
  }
}

function refresh(): void {
  chrome.runtime.sendMessage({ type: 'GET_ALL_LISTINGS' }, (response: GetAllListingsResponse) => {
    allListings = response?.listings ?? [];
    const filtered = getFilteredListings();
    renderListings(filtered);
    renderChart(filtered);
  });
}

function checkCurrentTab(): void {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs[0];
    if (!tab?.url) return;
    currentUrl = tab.url;

    chrome.tabs.sendMessage(tab.id!, { type: 'GET_PARSED_LISTING' }, (parsed) => {
      if (chrome.runtime.lastError) {
        statusText.textContent = 'Not a supported page';
        saveBtn.disabled = true;
        return;
      }
      if (parsed) {
        currentParsedListing = parsed;
        chrome.runtime.sendMessage({ type: 'CHECK_LISTING_STATUS', payload: { url: currentUrl! } }, (status: CheckListingStatusResponse) => {
          if (status?.stored) {
            statusText.textContent = '✓ Already stored';
          } else {
            statusText.textContent = '○ Not yet saved';
          }
          saveBtn.disabled = false;
        });
      } else {
        statusText.textContent = 'Not a supported page';
        saveBtn.disabled = true;
      }
    });
  });
}

saveBtn.addEventListener('click', () => {
  if (!currentParsedListing) return;
  chrome.runtime.sendMessage({ type: 'SAVE_LISTING', payload: currentParsedListing }, (response: SaveListingResponse) => {
    if (response?.success) {
      lastSavedId = response.listingId;
      statusText.textContent = response.isNew ? '✓ Saved!' : '✓ Updated';
      refresh();
    }
  });
});

[filterBrand, filterModel, filterYearMin, filterYearMax, filterKmMin, filterKmMax, filterPriceMin, filterPriceMax, filterSource].forEach(el => {
  el.addEventListener('input', () => {
    const filtered = getFilteredListings();
    renderListings(filtered);
    renderChart(filtered);
  });
});

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === 'LISTING_SAVED') {
    lastSavedId = message.payload.listingId;
    refresh();
    checkCurrentTab();
  }
});

checkCurrentTab();
refresh();
