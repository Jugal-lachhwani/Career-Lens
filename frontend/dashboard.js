const API_BASE_URL = 'http://localhost:8000';

let chartInstances = [];

function destroyCharts() {
    chartInstances.forEach((chart) => chart.destroy());
    chartInstances = [];
}

function makeChart(ctx, config) {
    const chart = new Chart(ctx, config);
    chartInstances.push(chart);
    return chart;
}

function showDashboardError(message) {
    const errorEl = document.getElementById('dashboardError');
    errorEl.textContent = message;
    errorEl.style.display = 'block';
}

function renderKpis(summary) {
    const kpiGrid = document.getElementById('kpiGrid');
    const kpis = [
        { label: 'Total Jobs', value: summary.total_jobs || 0 },
        { label: 'Unique Companies', value: summary.unique_companies || 0 },
        { label: 'Unique Locations', value: summary.unique_locations || 0 },
        { label: 'Unique Skills', value: summary.unique_skills || 0 },
        { label: 'Last Updated', value: summary.last_updated ? new Date(summary.last_updated).toLocaleString() : 'N/A' },
    ];

    kpiGrid.innerHTML = kpis.map((kpi) => `
        <div class="kpi-card">
            <div class="label">${kpi.label}</div>
            <div class="value">${kpi.value}</div>
        </div>
    `).join('');
}

function renderSkillsChart(topSkills) {
    const ctx = document.getElementById('skillsChart');
    makeChart(ctx, {
        type: 'bar',
        data: {
            labels: topSkills.map((x) => x.skill),
            datasets: [{
                label: 'Job Mentions',
                data: topSkills.map((x) => x.count),
                backgroundColor: '#0ea5e9',
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: { legend: { display: false } },
        },
    });
}

function renderRolesChart(roleCounts) {
    const ctx = document.getElementById('rolesChart');
    makeChart(ctx, {
        type: 'doughnut',
        data: {
            labels: roleCounts.map((x) => x.role),
            datasets: [{
                data: roleCounts.map((x) => x.count),
                backgroundColor: [
                    '#0f766e', '#1d4ed8', '#f97316', '#e11d48', '#7c3aed', '#16a34a',
                    '#0891b2', '#dc2626', '#ca8a04', '#4f46e5', '#0284c7', '#334155',
                ],
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom' } },
        },
    });
}

function renderEngineeringRolesChart(engineeringRoleCounts) {
    const ctx = document.getElementById('engineeringRolesChart');
    makeChart(ctx, {
        type: 'bar',
        data: {
            labels: engineeringRoleCounts.map((x) => x.role),
            datasets: [{
                label: 'Jobs',
                data: engineeringRoleCounts.map((x) => x.count),
                backgroundColor: '#22c55e',
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { x: { ticks: { maxRotation: 45, minRotation: 30 } } },
        },
    });
}

function renderCompaniesChart(topCompanies) {
    const ctx = document.getElementById('companiesChart');
    makeChart(ctx, {
        type: 'bar',
        data: {
            labels: topCompanies.map((x) => x.company),
            datasets: [{
                label: 'Openings',
                data: topCompanies.map((x) => x.count),
                backgroundColor: '#f59e0b',
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { x: { ticks: { maxRotation: 50, minRotation: 30 } } },
        },
    });
}

function renderTimelineChart(timeline) {
    const ctx = document.getElementById('timelineChart');
    makeChart(ctx, {
        type: 'line',
        data: {
            labels: timeline.map((x) => x.date),
            datasets: [{
                label: 'Jobs Posted',
                data: timeline.map((x) => x.count),
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.12)',
                fill: true,
                tension: 0.3,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
        },
    });
}

function renderRoleLocationChart(rolesByLocation) {
    const roleSet = new Set();
    const locationMap = new Map();

    rolesByLocation.forEach((item) => {
        roleSet.add(item.role);
        if (!locationMap.has(item.location)) {
            locationMap.set(item.location, {});
        }
        locationMap.get(item.location)[item.role] = item.count;
    });

    const labels = Array.from(locationMap.keys());
    const roles = Array.from(roleSet);

    const colors = ['#0ea5e9', '#14b8a6', '#f97316', '#ef4444', '#8b5cf6', '#22c55e', '#eab308', '#06b6d4'];

    const datasets = roles.map((role, idx) => ({
        label: role,
        data: labels.map((location) => locationMap.get(location)[role] || 0),
        backgroundColor: colors[idx % colors.length],
    }));

    const ctx = document.getElementById('locationRoleChart');
    makeChart(ctx, {
        type: 'bar',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom' } },
            scales: {
                x: { stacked: true },
                y: { stacked: true },
            },
        },
    });
}

async function loadDashboard() {
    const loading = document.getElementById('dashboardLoading');
    const content = document.getElementById('dashboardContent');

    loading.style.display = 'block';
    content.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE_URL}/analytics/dashboard`);
        if (!response.ok) {
            throw new Error('Failed to fetch analytics data from API');
        }

        const data = await response.json();
        destroyCharts();

        renderKpis(data.summary || {});
        renderSkillsChart(data.top_skills || []);
        renderRolesChart(data.role_counts || []);
        renderEngineeringRolesChart(data.engineering_role_counts || []);
        renderCompaniesChart(data.top_companies || []);
        renderTimelineChart(data.timeline || []);
        renderRoleLocationChart(data.roles_by_location || []);

        loading.style.display = 'none';
        content.style.display = 'block';
    } catch (error) {
        loading.style.display = 'none';
        showDashboardError(error.message || 'Failed to load dashboard');
    }
}

document.addEventListener('DOMContentLoaded', loadDashboard);
