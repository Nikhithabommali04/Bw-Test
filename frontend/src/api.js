const BASE = '/api/tasks';

async function request(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    throw new Error(`Request failed: ${options.method || 'GET'} ${url} (${res.status})`);
  }
  return res;
}

export async function fetchTasks() {
  const res = await request(BASE);
  return res.json();
}

export async function createTask(title, status = 'todo') {
  const res = await request(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, status }),
  });
  return res.json();
}

export async function updateTaskStatus(id, status) {
  const res = await request(`${BASE}/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  return res.json();
}

export async function deleteTask(id) {
  await request(`${BASE}/${id}`, { method: 'DELETE' });
}
