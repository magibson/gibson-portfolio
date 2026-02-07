const searchInput = document.getElementById("searchInput");
const cityFilter = document.getElementById("cityFilter");
const leadGrid = document.getElementById("leadGrid");

const applyFilters = () => {
  const term = (searchInput.value || "").trim().toLowerCase();
  const city = (cityFilter.value || "").trim().toLowerCase();
  const cards = leadGrid.querySelectorAll(".lead-card");

  cards.forEach((card) => {
    const name = card.dataset.name || "";
    const cardCity = card.dataset.city || "";
    const matchesName = !term || name.includes(term);
    const matchesCity = !city || cardCity === city;
    card.style.display = matchesName && matchesCity ? "flex" : "none";
  });
};

searchInput?.addEventListener("input", applyFilters);
cityFilter?.addEventListener("change", applyFilters);
