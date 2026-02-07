/**
 * Apartment Finder Dashboard
 * Static HTML frontend for browsing listings
 */

// State
let listings = [];
let filteredListings = [];
let favorites = new Set(JSON.parse(localStorage.getItem('apartment_favorites') || '[]'));
let currentView = 'list';
let map = null;
let markers = [];

// Constants
const UTILITY_ESTIMATES = {
    electric: { studio: 80, '1br': 100 },
    gas: { studio: 40, '1br': 50 },
    water: { studio: 30, '1br': 35 },
    internet: 70,
    renters_insurance: 20
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadListings();
    setupFilterListeners();
});

// Load listings from JSON
async function loadListings() {
    const container = document.getElementById('listingsContainer');
    container.innerHTML = '<div class="loading">Loading listings...</div>';
    
    try {
        // Try to load from data directory (relative path)
        const response = await fetch('../data/listings.json');
        if (!response.ok) throw new Error('Failed to load listings');
        
        const data = await response.json();
        listings = data.listings || [];
        
        // Update last updated time
        document.getElementById('lastUpdated').textContent = 
            `Updated: ${new Date(data.generated_at).toLocaleString()}`;
        
        applyFilters();
    } catch (error) {
        console.error('Error loading listings:', error);
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <h3>No listings found</h3>
                <p>Run the scraper first: <code>python scripts/scrape.py</code></p>
                <p style="margin-top: 10px; color: var(--text-muted)">Error: ${error.message}</p>
            </div>
        `;
    }
}

// Filter listeners
function setupFilterListeners() {
    const filterIds = ['minPrice', 'maxPrice', 'bedStudio', 'bed1', 
                       'cityFilter', 'sourceFilter', 'sortBy', 'showFavorites'];
    
    filterIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', applyFilters);
            el.addEventListener('input', debounce(applyFilters, 300));
        }
    });
}

// Apply filters
function applyFilters() {
    const minPrice = parseInt(document.getElementById('minPrice').value) || 0;
    const maxPrice = parseInt(document.getElementById('maxPrice').value) || 999999;
    const showStudio = document.getElementById('bedStudio').checked;
    const show1Br = document.getElementById('bed1').checked;
    const cityFilter = document.getElementById('cityFilter').value;
    const sourceFilter = document.getElementById('sourceFilter').value;
    const sortBy = document.getElementById('sortBy').value;
    const showFavoritesOnly = document.getElementById('showFavorites').checked;
    
    filteredListings = listings.filter(listing => {
        // Price filter
        const price = listing.price || 0;
        if (price < minPrice || price > maxPrice) return false;
        
        // Beds filter
        const beds = listing.beds ?? -1;
        if (beds === 0 && !showStudio) return false;
        if (beds === 1 && !show1Br) return false;
        if (beds > 1) return false; // Only show studio and 1BR
        
        // City filter
        if (cityFilter && listing.city !== cityFilter) return false;
        
        // Source filter
        if (sourceFilter && listing.source !== sourceFilter) return false;
        
        // Favorites filter
        if (showFavoritesOnly && !favorites.has(listing.id)) return false;
        
        return true;
    });
    
    // Sort
    filteredListings.sort((a, b) => {
        switch (sortBy) {
            case 'newest':
                return new Date(b.first_seen) - new Date(a.first_seen);
            case 'price_asc':
                return (a.price || 0) - (b.price || 0);
            case 'price_desc':
                return (b.price || 0) - (a.price || 0);
            case 'truecost':
                return (a.true_monthly_cost || 0) - (b.true_monthly_cost || 0);
            default:
                return 0;
        }
    });
    
    updateStats();
    renderListings();
}

// Update stats bar
function updateStats() {
    const total = filteredListings.length;
    const newCount = filteredListings.filter(l => l.is_new).length;
    const favCount = filteredListings.filter(l => favorites.has(l.id)).length;
    
    document.getElementById('statsTotal').textContent = `${total} listings`;
    document.getElementById('statsNew').innerHTML = newCount > 0 
        ? `<span class="new-count">✨ ${newCount} new</span>` : '';
    document.getElementById('statsFavorites').innerHTML = favCount > 0 
        ? `<span class="fav-count">⭐ ${favCount} favorites</span>` : '';
}

// Render listings
function renderListings() {
    const container = document.getElementById('listingsContainer');
    
    if (filteredListings.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <h3>No listings match your criteria</h3>
                <p>Try adjusting your filters</p>
            </div>
        `;
        return;
    }
    
    container.className = `listings-container view-${currentView}`;
    container.innerHTML = filteredListings.map(listing => renderCard(listing)).join('');
    
    // Update map if visible
    if (currentView === 'map') {
        updateMap();
    }
}

// Render a single card
function renderCard(listing) {
    const isFavorite = favorites.has(listing.id);
    const bedText = listing.beds === 0 ? 'Studio' : listing.beds === 1 ? '1 BR' : `${listing.beds} BR`;
    const images = listing.images || [];
    const mainImage = images.length > 0 ? images[0] : null;
    
    return `
        <div class="listing-card ${isFavorite ? 'is-favorite' : ''} ${listing.is_new ? 'is-new' : ''}"
             onclick="showDetail(${listing.id})">
            ${mainImage 
                ? `<img src="${mainImage}" class="listing-image" alt="${listing.title}" onerror="this.outerHTML='<div class=\\'no-image\\'>🏠</div>'">`
                : '<div class="no-image">🏠</div>'
            }
            <div class="listing-content">
                <div class="listing-header">
                    <div>
                        <div class="listing-title">${escapeHtml(listing.title || listing.address || 'Untitled')}</div>
                        <div class="listing-address">${escapeHtml(listing.city || '')}${listing.zip_code ? ', ' + listing.zip_code : ''}</div>
                    </div>
                    <div class="listing-badges">
                        ${listing.is_new ? '<span class="badge badge-new">New</span>' : ''}
                        <span class="badge badge-source">${listing.source}</span>
                    </div>
                </div>
                <div class="listing-details">
                    <span>🛏 ${bedText}</span>
                    ${listing.baths ? `<span>🛁 ${listing.baths} BA</span>` : ''}
                    ${listing.sqft ? `<span>📐 ${listing.sqft.toLocaleString()} sqft</span>` : ''}
                </div>
            </div>
            <div class="listing-price-section">
                <div class="listing-price">${listing.price ? '$' + listing.price.toLocaleString() : 'Contact'}</div>
                <div class="listing-truecost">~$${(listing.true_monthly_cost || 0).toLocaleString()}/mo total</div>
                <div class="listing-actions" onclick="event.stopPropagation()">
                    <button class="favorite-btn ${isFavorite ? 'active' : ''}" 
                            onclick="toggleFavorite(${listing.id}, event)">
                        ${isFavorite ? '⭐' : '☆'}
                    </button>
                    <a href="${listing.url}" target="_blank" class="btn btn-secondary" 
                       onclick="event.stopPropagation()">View ↗</a>
                </div>
            </div>
        </div>
    `;
}

// Toggle favorite
function toggleFavorite(id, event) {
    if (event) event.stopPropagation();
    
    if (favorites.has(id)) {
        favorites.delete(id);
    } else {
        favorites.add(id);
    }
    
    localStorage.setItem('apartment_favorites', JSON.stringify([...favorites]));
    applyFilters();
}

// Show detail modal
function showDetail(id) {
    const listing = listings.find(l => l.id === id);
    if (!listing) return;
    
    const modal = document.getElementById('detailModal');
    const modalBody = document.getElementById('modalBody');
    
    const bedText = listing.beds === 0 ? 'Studio' : listing.beds === 1 ? '1 BR' : `${listing.beds} BR`;
    const images = listing.images || [];
    const isFavorite = favorites.has(listing.id);
    
    // Calculate true cost breakdown
    const bedKey = listing.beds === 0 ? 'studio' : '1br';
    const utilities = {
        electric: UTILITY_ESTIMATES.electric[bedKey],
        gas: UTILITY_ESTIMATES.gas[bedKey],
        water: UTILITY_ESTIMATES.water[bedKey],
        internet: UTILITY_ESTIMATES.internet,
        insurance: UTILITY_ESTIMATES.renters_insurance
    };
    const totalUtilities = Object.values(utilities).reduce((a, b) => a + b, 0);
    const trueCost = (listing.price || 0) + totalUtilities;
    
    modalBody.innerHTML = `
        <div class="detail-header">
            <h2 class="detail-title">${escapeHtml(listing.title || listing.address || 'Apartment')}</h2>
            <div class="detail-address">${escapeHtml(listing.address || '')} • ${escapeHtml(listing.city || '')}, NJ ${listing.zip_code || ''}</div>
        </div>
        
        ${images.length > 0 ? `
            <div class="detail-gallery">
                ${images.map(img => `<img src="${img}" alt="Apartment photo" onerror="this.style.display='none'">`).join('')}
            </div>
        ` : ''}
        
        <div class="detail-stats">
            <div class="detail-stat">
                <div class="detail-stat-value">${listing.price ? '$' + listing.price.toLocaleString() : 'N/A'}</div>
                <div class="detail-stat-label">Monthly Rent</div>
            </div>
            <div class="detail-stat">
                <div class="detail-stat-value">${bedText}</div>
                <div class="detail-stat-label">Bedrooms</div>
            </div>
            <div class="detail-stat">
                <div class="detail-stat-value">${listing.baths || 'N/A'}</div>
                <div class="detail-stat-label">Bathrooms</div>
            </div>
            <div class="detail-stat">
                <div class="detail-stat-value">${listing.sqft ? listing.sqft.toLocaleString() : 'N/A'}</div>
                <div class="detail-stat-label">Sq Ft</div>
            </div>
        </div>
        
        <div class="detail-cost-breakdown">
            <h3 style="margin-bottom: 15px;">💰 True Monthly Cost Estimate</h3>
            <div class="cost-row">
                <span>Base Rent</span>
                <span>$${(listing.price || 0).toLocaleString()}</span>
            </div>
            <div class="cost-row">
                <span>⚡ Electric</span>
                <span>~$${utilities.electric}</span>
            </div>
            <div class="cost-row">
                <span>🔥 Gas</span>
                <span>~$${utilities.gas}</span>
            </div>
            <div class="cost-row">
                <span>💧 Water</span>
                <span>~$${utilities.water}</span>
            </div>
            <div class="cost-row">
                <span>📶 Internet</span>
                <span>~$${utilities.internet}</span>
            </div>
            <div class="cost-row">
                <span>🛡 Renter's Insurance</span>
                <span>~$${utilities.insurance}</span>
            </div>
            <div class="cost-row" style="margin-top: 10px; padding-top: 10px; border-top: 2px solid var(--border);">
                <span>Estimated Total</span>
                <span>~$${trueCost.toLocaleString()}/mo</span>
            </div>
        </div>
        
        ${listing.description ? `
            <div style="margin-bottom: 20px;">
                <h3 style="margin-bottom: 10px;">Description</h3>
                <p style="color: var(--text-secondary);">${escapeHtml(listing.description)}</p>
            </div>
        ` : ''}
        
        <div class="detail-actions">
            <a href="${listing.url}" target="_blank" class="btn btn-primary">View Original Listing ↗</a>
            <button class="btn btn-secondary" onclick="toggleFavorite(${listing.id})">
                ${isFavorite ? '⭐ Remove from Favorites' : '☆ Add to Favorites'}
            </button>
            ${listing.lat && listing.lng ? `
                <a href="https://www.google.com/maps?q=${listing.lat},${listing.lng}" 
                   target="_blank" class="btn btn-secondary">🗺 View on Map</a>
            ` : ''}
        </div>
        
        <div style="margin-top: 20px; font-size: 0.8rem; color: var(--text-muted);">
            Source: ${listing.source} • First seen: ${new Date(listing.first_seen).toLocaleDateString()}
        </div>
    `;
    
    modal.style.display = 'flex';
}

// Close modal
function closeModal() {
    document.getElementById('detailModal').style.display = 'none';
}

// View toggle
function setView(view) {
    currentView = view;
    
    document.querySelectorAll('.view-toggle button').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`view${view.charAt(0).toUpperCase() + view.slice(1)}`).classList.add('active');
    
    if (view === 'map') {
        document.getElementById('listingsContainer').style.display = 'none';
        document.getElementById('mapContainer').style.display = 'block';
        initMap();
    } else {
        document.getElementById('listingsContainer').style.display = 'grid';
        document.getElementById('mapContainer').style.display = 'none';
    }
    
    renderListings();
}

// Initialize map
function initMap() {
    if (map) return;
    
    // Center on Red Bank, NJ
    map = L.map('map').setView([40.3470, -74.0643], 12);
    
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);
    
    updateMap();
}

// Update map markers
function updateMap() {
    if (!map) return;
    
    // Clear existing markers
    markers.forEach(m => map.removeLayer(m));
    markers = [];
    
    // Add markers for listings with coordinates
    filteredListings.forEach(listing => {
        if (listing.lat && listing.lng) {
            const isFavorite = favorites.has(listing.id);
            const marker = L.marker([listing.lat, listing.lng])
                .addTo(map)
                .bindPopup(`
                    <strong>${escapeHtml(listing.title || listing.address)}</strong><br>
                    ${listing.price ? '$' + listing.price.toLocaleString() : 'Contact'}<br>
                    <a href="${listing.url}" target="_blank">View Listing</a>
                `);
            markers.push(marker);
        }
    });
    
    // Fit bounds if we have markers
    if (markers.length > 0) {
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

// Export functions
function exportListings() {
    const csv = [
        ['Title', 'Address', 'City', 'Price', 'Beds', 'Baths', 'SqFt', 'True Cost', 'Source', 'URL'].join(','),
        ...filteredListings.map(l => [
            `"${(l.title || '').replace(/"/g, '""')}"`,
            `"${(l.address || '').replace(/"/g, '""')}"`,
            l.city || '',
            l.price || '',
            l.beds ?? '',
            l.baths || '',
            l.sqft || '',
            l.true_monthly_cost || '',
            l.source || '',
            l.url || ''
        ].join(','))
    ].join('\n');
    
    downloadFile(csv, 'apartments.csv', 'text/csv');
}

function exportFavorites() {
    const favListings = filteredListings.filter(l => favorites.has(l.id));
    const data = JSON.stringify(favListings, null, 2);
    downloadFile(data, 'favorites.json', 'application/json');
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Utilities
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Close modal on escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

// Close modal on outside click
document.getElementById('detailModal')?.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) closeModal();
});
