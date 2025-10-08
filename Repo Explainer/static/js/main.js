async function analyzeRepo() {
  const repoUrl = document.getElementById('repoUrl').value.trim();
  const branch = document.getElementById('branch').value.trim();
  const token = document.getElementById('token').value.trim();
  const status = document.getElementById('status');
  status.textContent = 'Analyzing...';

  const payload = { repo_url: repoUrl };
  if (branch) payload.branch = branch;
  // pass optional params to server (server uses GITHUB_TOKEN env if available)
  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) {
      status.textContent = 'Error: ' + (data.error || res.statusText);
      return;
    }
    status.textContent = 'Done';
    renderResults(data);
  } catch (err) {
    status.textContent = 'Network error: ' + err.message;
  }
}

function renderResults(data) {
  document.getElementById('results').style.display = 'block';
  const summ = document.getElementById('summaryArea');
  summ.innerHTML = `
    <p><strong>${data.owner}/${data.repo}</strong> — branch: ${data.branch}</p>
    <p>Total files (repo reported): ${data.file_count}</p>
    <p>Files analyzed: ${data.files_returned}</p>
    ${data.warning ? `<p style="color: #b45309">${data.warning}</p>` : ''}
    <p>Total bytes: ${data.stats.total_bytes} • Total lines: ${data.stats.total_lines}</p>
    <p>Languages: ${Object.entries(data.stats.languages).map(([k,v]) => `${k}: ${v}`).join(', ')}</p>
  `;

  // file tree display (simple)
  document.getElementById('fileTree').textContent = JSON.stringify(data.tree, null, 2);

  // top files
  const top = document.getElementById('topFiles');
  top.innerHTML = '';
  (data.top_files || []).forEach(f => {
    const li = document.createElement('li');
    li.textContent = `${f.path} — ${(f.size/1024).toFixed(1)} KB • ${f.lines} lines • ${f.language}`;
    top.appendChild(li);
  });

  renderGraph(data.nodes, data.edges);
}

function renderGraph(nodes, edges) {
  const svg = d3.select("#graph");
  svg.selectAll("*").remove();
  const width = +svg.attr("width");
  const height = +svg.attr("height");

  const nodeById = new Map(nodes.map(d => [d.id, d]));

  // small scaling for node radius
  const sizeExtent = d3.extent(nodes, d => d.size || 1);
  const sizeScale = d3.scaleSqrt().domain(sizeExtent).range([4, 18]);

  const link = svg.append("g")
      .attr("stroke", "#9ca3af")
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke-width", 1);

  const node = svg.append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", d => sizeScale(d.size || 1))
      .attr("fill", "#2563eb")
      .call(drag(simulation));

  const label = svg.append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text(d => d.label)
      .attr("font-size", 10)
      .attr("dx", 6)
      .attr("dy", 3);

  const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(edges).id(d => d.id).distance(60).strength(0.6))
      .force("charge", d3.forceManyBody().strength(-120))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .on("tick", ticked);

  function ticked() {
    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);

    node
      .attr("cx", d => d.x)
      .attr("cy", d => d.y);

    label
      .attr("x", d => d.x)
      .attr("y", d => d.y);
  }

  function drag(sim) {
    function started(event, d) {
      if (!event.active) sim.alphaTarget(0.3).restart();
      d.fx = d.x; d.fy = d.y;
    }
    function dragged(event, d) {
      d.fx = event.x; d.fy = event.y;
    }
    function ended(event, d) {
      if (!event.active) sim.alphaTarget(0);
      d.fx = null; d.fy = null;
    }
    return d3.drag().on("start", started).on("drag", dragged).on("end", ended);
  }

  // basic hover tooltip
  node.append("title").text(d => `${d.id}\n${d.group}\n${d.size} bytes\n${d.lines} lines`);
}
document.getElementById('analyzeBtn').addEventListener('click', analyzeRepo);
