document.getElementById('explain').addEventListener('click', async () => {
  const code = document.getElementById('code').value;
  const res = await fetch('/api/explain', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({code, language: 'python'})
  });
  const js = await res.json();
  if (js.error) {
    document.getElementById('result').textContent = "Error: " + js.error;
  } else {
    // explanation can be an object
    document.getElementById('result').textContent = JSON.stringify(js.explanation, null, 2);
  }
});

document.getElementById('optimize').addEventListener('click', async () => {
  const code = document.getElementById('code').value;
  const res = await fetch('/api/optimize', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({code, language: 'python'})
  });
  const js = await res.json();
  if (js.error) {
    document.getElementById('optimized').textContent = "Error: " + js.error;
  } else {
    document.getElementById('optimized').textContent = js.optimized || js.formatted || '';
  }
});
