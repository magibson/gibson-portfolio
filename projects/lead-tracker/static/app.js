const rows = Array.from(document.querySelectorAll('tbody tr'));
const filter = document.getElementById('status-filter');

function applyFilter() {
  const value = filter.value;
  rows.forEach((row) => {
    const status = row.dataset.status;
    if (value === 'all' || status === value) {
      row.classList.remove('hidden');
    } else {
      row.classList.add('hidden');
    }
  });
}

async function updateLead(row) {
  const id = row.dataset.id;
  const status = row.querySelector('.status').value;
  const notes = row.querySelector('.notes').value.trim();

  const res = await fetch('/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, status, notes }),
  });

  if (!res.ok) {
    console.error('Update failed');
    return;
  }

  const data = await res.json();
  row.dataset.status = status;
  row.querySelector('.last-contact').textContent = data.last_contact || '-';
  applyFilter();
}

rows.forEach((row) => {
  const statusSelect = row.querySelector('.status');
  const notesField = row.querySelector('.notes');

  statusSelect.addEventListener('change', () => updateLead(row));
  notesField.addEventListener('blur', () => updateLead(row));
});

filter.addEventListener('change', applyFilter);
applyFilter();
