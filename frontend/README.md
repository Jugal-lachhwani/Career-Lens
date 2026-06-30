# Job Search Agent - Frontend

A modern, user-friendly web interface for the AI Job Search Agent.

## Features

✅ **Job Search Interface**
- Natural language job queries
- Resume upload (PDF)
- Real-time processing with loading states
- Beautiful results display with similarity scores

✅ **Resume Analysis Display**
- Profile summary
- Skills visualization
- Experience and education
- Projects and certifications

✅ **Job Results**
- Color-coded similarity scores (Excellent/Good/Fair/Poor)
- Required skills tags
- AI-generated feedback
- Quick apply buttons
- Full job details modal

✅ **Saved Jobs**
- View all previously analyzed jobs
- Quick access to job details
- No need to re-run analysis

✅ **Search History**
- Track past searches
- View query and resume used
- Timestamps for all searches

## Setup Instructions

### 1. Start the Backend API

First, make sure your backend API is running:

```bash
# From the project root directory
python -m src.api
```

The API should be running at: `http://localhost:8000`

### 2. Open the Frontend

Simply open the `index.html` file in your web browser:

**Option A: Double-click**
- Navigate to the `frountend` folder
- Double-click `index.html`

**Option B: Use Python HTTP Server** (Recommended)
```bash
# From the frountend directory
cd frountend
python -m http.server 3000
```
Then open: `http://localhost:3000`

**Option C: Use Live Server (VS Code)**
- Install "Live Server" extension in VS Code
- Right-click `index.html` → "Open with Live Server"

### 3. Start Using the App

1. **Enter your job query**: "Find 5 Python developer jobs in California"
2. **Upload your resume**: PDF file only
3. **Click "Search Jobs"**: Wait 30-60 seconds for AI analysis
4. **View results**: See matched jobs with similarity scores
5. **Check other tabs**: View saved jobs and search history

## File Structure

```
frountend/
├── index.html      # Main HTML structure
├── styles.css      # Complete styling
├── script.js       # All JavaScript functionality
└── README.md       # This file
```

## Configuration

To change the API URL, edit `script.js`:

```javascript
const API_BASE_URL = 'http://localhost:8000';
```

For production, change it to your deployed API URL:

```javascript
const API_BASE_URL = 'https://your-api-domain.com';
```

## Features in Detail

### Tab 1: Job Search
- Upload resume (PDF only)
- Enter natural language query
- Real-time processing indicator
- Results with similarity scores
- Resume summary extraction
- AI feedback for each job

### Tab 2: Saved Jobs
- All jobs saved in database
- Company and location info
- Date added
- View full details button
- No re-processing needed

### Tab 3: Search History
- All past search queries
- Resume file names
- Timestamps
- Track your search patterns

## Browser Support

Works on all modern browsers:
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Responsive Design

The interface adapts to:
- 💻 Desktop (1200px+)
- 📱 Tablet (768px - 1200px)
- 📱 Mobile (< 768px)

## API Endpoints Used

- `POST /process-job-search` - Submit new job search
- `GET /jobs` - Get all saved jobs
- `GET /jobs/{job_id}` - Get specific job details
- `GET /search-history` - Get search history
- `GET /health` - Check API status

## Troubleshooting

### API Not Running
**Error**: "Backend API is not running"
**Solution**: Start the API with `python -m src.api`

### CORS Issues
**Error**: "CORS policy blocked"
**Solution**: The API already has CORS enabled. Make sure you're accessing from `http://` or `https://`, not `file://`

### File Upload Fails
**Error**: "Only PDF files supported"
**Solution**: Make sure your resume is a `.pdf` file

### Results Not Showing
**Error**: Processing but no results
**Solution**: Check the browser console (F12) for errors and check API logs

## Customization

### Change Colors
Edit `styles.css` CSS variables:
```css
:root {
    --primary-color: #2563eb;  /* Change primary color */
    --success-color: #10b981;  /* Change success color */
    /* ... more colors */
}
```

### Add Features
Edit `script.js` to add new functionality:
- Export results to PDF
- Email job listings
- Set up job alerts
- Filter and sort jobs

## Next Steps

Potential enhancements:
- 🔐 User authentication
- 📧 Email job matches
- 🔔 Job alerts setup
- 📊 Analytics dashboard
- 💾 Export results
- 🔍 Advanced filters
- ⭐ Favorite jobs
- 📝 Application tracking

## Need Help?

Check the browser console (F12) for detailed error messages.
Check API logs for backend issues.

Enjoy using the AI Job Search Agent! 🚀
