class GraphStreamer {
  constructor(jobId) {
    this.jobId = jobId;
    this.nodes = new Map();
    this.edges = [];
    this.chart = null;
    this.progress = new mdc.linearProgress.MDCLinearProgress(
      document.querySelector('.mdc-linear-progress'),
    );
  }

  async init() {
    this.setupChart();
    await this.streamData();
    this.updateChart();
  }

  setupChart() {
    const ctx = document.createElement('canvas');
    document.getElementById('graph-container').appendChild(ctx);

    this.chart = new Chart(ctx, {
      type: 'forceDirectedGraph',
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: false,
        },
        elements: {
          node: {
            color: (ctx) => (ctx.raw.external ? '#ff5252' : '#6200ee'),
          },
        },
      },
    });
  }

  async streamData() {
    const response = await fetch(`/api/v1/graph/${this.jobId}/data`);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value);
      this.processBuffer(buffer);

      // Update progress bar
      const progress = Math.min(
        ((this.nodes.size + this.edges.length) /
          (this.nodes.size + this.edges.length + 1000)) *
          100,
        95,
      );
      this.progress.progress = progress / 100;
    }

    this.progress.progress = 1;
  }

  processBuffer(buffer) {
    try {
      const data = JSON.parse(buffer);

      if (data.nodes) {
        data.nodes.forEach((node) => {
          this.nodes.set(node.id, {
            id: node.id,
            label: node.url,
            external: node.external,
          });
        });
      }

      if (data.edges) {
        this.edges.push(
          ...data.edges.map((edge) => ({
            source: edge.source,
            target: edge.target,
          })),
        );
      }

      // Throttle chart updates
      if (this.nodes.size % 50 === 0 || this.edges.length % 100 === 0) {
        this.updateChart();
      }
    } catch (e) {
      // Incomplete JSON, wait for more data
    }
  }

  updateChart() {
    this.chart.data = {
      nodes: Array.from(this.nodes.values()),
      edges: this.edges,
    };
    this.chart.update();
  }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
  const graph = new GraphStreamer(jobId);
  graph.init();
});

// Force-directed graph plugin for Chart.js
Chart.register({
  id: 'forceDirectedGraph',
  beforeDraw(chart) {
    if (!chart.forceLayout) {
      chart.forceLayout = {
        nodes: [],
        edges: [],
        simulation: null,
      };
    }
  },
  draw(chart) {
    const { ctx, data, options } = chart;
    const width = chart.width;
    const height = chart.height;

    if (!chart.forceLayout.simulation && data.nodes.length > 0) {
      // Initialize force layout
      chart.forceLayout.simulation = d3
        .forceSimulation(data.nodes)
        .force('charge', d3.forceManyBody().strength(-100))
        .force(
          'link',
          d3.forceLink(data.edges).id((d) => d.id),
        )
        .force('center', d3.forceCenter(width / 2, height / 2));

      chart.forceLayout.simulation.on('tick', () => {
        chart.update('none'); // Don't animate
      });
    }

    // Draw edges
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
    data.edges.forEach((edge) => {
      ctx.beginPath();
      ctx.moveTo(edge.source.x, edge.source.y);
      ctx.lineTo(edge.target.x, edge.target.y);
      ctx.stroke();
    });

    // Draw nodes
    data.nodes.forEach((node) => {
      ctx.fillStyle = options.elements.node.color({ raw: node });
      ctx.beginPath();
      ctx.arc(node.x, node.y, 5, 0, Math.PI * 2);
      ctx.fill();

      // Draw labels
      if (node.x && node.y) {
        ctx.fillStyle = '#333';
        ctx.fillText(node.label, node.x + 8, node.y + 3);
      }
    });
  },
});
