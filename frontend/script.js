// Configuration
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const tabs = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');
const jobSearchForm = document.getElementById('jobSearchForm');
const searchBtn = document.getElementById('searchBtn');
const loadingState = document.getElementById('loadingState');
const resultsSection = document.getElementById('resultsSection');
const errorMessage = document.getElementById('errorMessage');
const resumeFileInput = document.getElementById('resumeFile');
const clearResultsBtn = document.getElementById('clearResults');
const refreshSavedBtn = document.getElementById('refreshSaved');
const refreshHistoryBtn = document.getElementById('refreshHistory');
const modal = document.getElementById('jobModal');
const closeModal = document.querySelector('.close');

// Tab Switching
tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;
        
        // Update active tab button
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        // Update active tab content
        tabContents.forEach(content => content.classList.remove('active'));
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        // Load data for the tab
        if (tabName === 'saved') {
            loadSavedJobs();
        } else if (tabName === 'history') {
            loadSearchHistory();
        }
    });
});

// File input display
resumeFileInput.addEventListener('change', (e) => {
    const fileName = e.target.files[0]?.name || 'No file chosen';
    document.querySelector('.file-name').textContent = fileName;
});

// Job Search Form Submission
jobSearchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const jobQuery = document.getElementById('jobQuery').value;
    const resumeFile = resumeFileInput.files[0];
    
    if (!resumeFile) {
        showError('Please upload a resume file');
        return;
    }
    
    if (!resumeFile.name.endsWith('.pdf')) {
        showError('Please upload a PDF file');
        return;
    }
    
    // Show loading state
    hideError();
    resultsSection.style.display = 'none';
    loadingState.style.display = 'block';
    searchBtn.disabled = true;
    searchBtn.querySelector('.btn-text').style.display = 'none';
    searchBtn.querySelector('.spinner').style.display = 'inline-block';
    
    // Create FormData
    const formData = new FormData();
    formData.append('user_input', jobQuery);
    formData.append('resume', resumeFile);
    
    try {
        const response = await fetch(`${API_BASE_URL}/process-job-search`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to process job search');
        }
        
        const data = await response.json();
        displayResults(data);
        
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'An error occurred while searching for jobs');
        loadingState.style.display = 'none';
    } finally {
        searchBtn.disabled = false;
        searchBtn.querySelector('.btn-text').style.display = 'inline';
        searchBtn.querySelector('.spinner').style.display = 'none';
    }
});

// Display Results
function displayResults(data) {
    loadingState.style.display = 'none';
    resultsSection.style.display = 'block';
    
    // Display Resume Summary
    displayResumeSummary(data.resume_fields);
    
    // Display Job Cards
    displayJobCards(data.job_summaries, data.job_feedbacks);
}

// Display Resume Summary
function displayResumeSummary(resumeFields) {
    const summaryDiv = document.getElementById('resumeSummary');
    
    summaryDiv.innerHTML = `
        <div class="summary-item">
            <h4>👤 Profile</h4>
            <p>${resumeFields.profile || 'No profile information'}</p>
        </div>
        
        <div class="summary-item">
            <h4>🛠️ Skills</h4>
            <ul>
                ${resumeFields.skills.map(skill => `<li>${skill}</li>`).join('')}
            </ul>
        </div>
        
        <div class="summary-item">
            <h4>💼 Experience</h4>
            ${resumeFields.Experience.map(exp => `<p>• ${exp}</p>`).join('')}
        </div>
        
        <div class="summary-item">
            <h4>🎓 Education</h4>
            ${resumeFields.Education.map(edu => `<p>• ${edu}</p>`).join('')}
        </div>
        
        ${resumeFields.Projects.length > 0 && resumeFields.Projects[0] !== 'No Projects' ? `
        <div class="summary-item">
            <h4>🚀 Projects</h4>
            ${resumeFields.Projects.map(proj => `<p>• ${proj}</p>`).join('')}
        </div>
        ` : ''}
        
        ${resumeFields.Certifications.length > 0 && resumeFields.Certifications[0] !== 'No Certifications' ? `
        <div class="summary-item">
            <h4>📜 Certifications</h4>
            ${resumeFields.Certifications.map(cert => `<p>• ${cert}</p>`).join('')}
        </div>
        ` : ''}
    `;
}

// Display Job Cards
function displayJobCards(jobSummaries, jobFeedbacks) {
    const jobResultsDiv = document.getElementById('jobResults');
    
    // Create a map of feedbacks by job ID
    const feedbackMap = {};
    jobFeedbacks.forEach(feedback => {
        feedbackMap[feedback.id] = feedback;
    });
    
    jobResultsDiv.innerHTML = jobSummaries.map(job => {
        const feedback = feedbackMap[job.id] || { similarity: 0, feedback: 'No feedback available' };
        const matchLevel = getMatchLevel(feedback.similarity);
        
        return `
            <div class="job-card ${matchLevel.class}">
                <div class="job-card-header">
                    <div>
                        <h3 class="job-title">${job.job_info.split('\n')[0] || 'Job Title'}</h3>
                        <p class="job-company">${job.job_info.split('\n')[1] || ''}</p>
                    </div>
                    <div class="similarity-badge ${matchLevel.class}">
                        ${feedback.similarity}%
                    </div>
                </div>
                
                <div class="job-summary">
                    ${job.job_info}
                </div>
                
                <div class="job-skills">
                    <h4>Required Skills:</h4>
                    <div class="skills-list">
                        ${job.job_skills.map(skill => `<span class="skill-tag">${skill}</span>`).join('')}
                    </div>
                </div>
                
                <div class="job-feedback">
                    <h4>💡 AI Feedback</h4>
                    <p>${feedback.feedback}</p>
                </div>
                
                <div class="job-actions">
                    <button class="btn-details" onclick="viewJobDetails('${job.id}')">
                        View Full Details
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Get Match Level
function getMatchLevel(similarity) {
    if (similarity >= 80) return { class: 'excellent', text: 'Excellent Match' };
    if (similarity >= 60) return { class: 'good', text: 'Good Match' };
    if (similarity >= 40) return { class: 'fair', text: 'Fair Match' };
    return { class: 'poor', text: 'Poor Match' };
}

// View Job Details
async function viewJobDetails(jobId) {
    try {
        const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch job details');
        }
        
        const job = await response.json();
        displayJobModal(job);
        
    } catch (error) {
        console.error('Error:', error);
        showError('Failed to load job details');
    }
}

// Display Job Modal
function displayJobModal(job) {
    const modalBody = document.getElementById('modalBody');
    
    const matchLevel = job.analysis ? getMatchLevel(job.analysis.similarity_score) : { class: '', text: '' };
    
    modalBody.innerHTML = `
        <h2>${job.title}</h2>
        <p class="job-company"><strong>Company:</strong> ${job.company_name}</p>
        <p class="job-company"><strong>Location:</strong> ${job.location}</p>
        <p class="job-company"><strong>Posted:</strong> ${job.posted_date || 'N/A'}</p>
        
        ${job.analysis ? `
            <div class="similarity-badge ${matchLevel.class}" style="margin: 1rem 0;">
                Match Score: ${job.analysis.similarity_score}%
            </div>
            
            <div class="job-summary">
                <h3>Summary</h3>
                <p>${job.analysis.summary}</p>
            </div>
            
            <div class="job-skills">
                <h3>Required Skills</h3>
                <div class="skills-list">
                    ${job.analysis.required_skills.map(skill => `<span class="skill-tag">${skill}</span>`).join('')}
                </div>
            </div>
            
            <div class="job-feedback">
                <h3>AI Feedback</h3>
                <p>${job.analysis.feedback}</p>
            </div>
        ` : ''}
        
        <div style="margin-top: 1.5rem;">
            <h3>Full Description</h3>
            <div style="white-space: pre-wrap; background: var(--background); padding: 1rem; border-radius: 8px; max-height: 400px; overflow-y: auto;">
                ${job.description}
            </div>
        </div>
        
        <div style="margin-top: 1.5rem;">
            <a href="${job.apply_url}" target="_blank" class="btn-apply" style="display: inline-block;">
                Apply Now →
            </a>
        </div>
    `;
    
    modal.style.display = 'block';
}

// Load Saved Jobs
async function loadSavedJobs() {
    const savedJobsList = document.getElementById('savedJobsList');
    savedJobsList.innerHTML = '<p class="loading-text">Loading saved jobs...</p>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/jobs?limit=50`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch saved jobs');
        }
        
        const data = await response.json();
        
        if (data.jobs.length === 0) {
            savedJobsList.innerHTML = '<p class="loading-text">No saved jobs found. Start a job search to save jobs!</p>';
            return;
        }
        
        savedJobsList.innerHTML = data.jobs.map(job => `
            <div class="saved-job-item">
                <div class="saved-job-info">
                    <h3>${job.title}</h3>
                    <p class="saved-job-meta">
                        ${job.company_name} • ${job.location} • 
                        Added: ${new Date(job.created_at).toLocaleDateString()}
                    </p>
                </div>
                <button class="btn-view" onclick="viewJobDetails('${job.id}')">
                    View Details
                </button>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error:', error);
        savedJobsList.innerHTML = '<p class="loading-text error">Failed to load saved jobs</p>';
    }
}

// Load Search History
async function loadSearchHistory() {
    const historyList = document.getElementById('historyList');
    historyList.innerHTML = '<p class="loading-text">Loading search history...</p>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/search-history?limit=20`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch search history');
        }
        
        const data = await response.json();
        
        if (data.history.length === 0) {
            historyList.innerHTML = '<p class="loading-text">No search history found. Start a job search!</p>';
            return;
        }
        
        historyList.innerHTML = data.history.map(record => `
            <div class="history-item">
                <div class="saved-job-info">
                    <h3>${record.user_query}</h3>
                    <p class="saved-job-meta">
                        Resume: ${record.resume_name} • 
                        ${new Date(record.timestamp).toLocaleString()}
                    </p>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error:', error);
        historyList.innerHTML = '<p class="loading-text error">Failed to load search history</p>';
    }
}

// Clear Results
clearResultsBtn.addEventListener('click', () => {
    resultsSection.style.display = 'none';
    jobSearchForm.reset();
    document.querySelector('.file-name').textContent = 'No file chosen';
});

// Refresh Buttons
refreshSavedBtn.addEventListener('click', loadSavedJobs);
refreshHistoryBtn.addEventListener('click', loadSearchHistory);

// Modal Controls
closeModal.addEventListener('click', () => {
    modal.style.display = 'none';
});

window.addEventListener('click', (e) => {
    if (e.target === modal) {
        modal.style.display = 'none';
    }
});

// Error Handling
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

function hideError() {
    errorMessage.style.display = 'none';
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Job Search Agent Frontend loaded');
    // Check if API is running
    fetch(`${API_BASE_URL}/health`)
        .then(response => response.json())
        .then(data => console.log('API Status:', data))
        .catch(error => {
            console.error('API is not running:', error);
            showError('⚠️ Backend API is not running. Please start the API server first.');
        });
});
