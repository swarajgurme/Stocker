# CDK: Sales Forecasting & Cluster Analysis

A full-stack application for automotive parts sales forecasting and cluster analysis using Prophet and scikit-learn machine learning models.

## 📋 Project Overview

This project provides:
- **Time Series Forecasting**: Predict future sales using Facebook Prophet
- **Cluster Analysis**: Identify sales patterns across categories and stores using K-means
- **Interactive Dashboard**: React-based frontend with chart visualizations

## 🗂️ Project Structure

```
CDK/
├── backend/                    # Flask API server
│   ├── server.py              # Main Flask application
│   ├── data.csv               # Historical sales data
│   ├── requirements.txt        # Python dependencies
│   ├── README.md              # Backend documentation
│   └── .gitignore             # Git ignore rules
├── frontend/                   # React + Vite application
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── layouts/           # Layout components
│   │   ├── main.jsx           # Entry point
│   │   └── index.css          # Styles
│   ├── package.json           # Node dependencies
│   ├── vite.config.js         # Vite configuration
│   └── README.md              # Frontend documentation
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

## 🚀 Quick Start

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the server:
```bash
python server.py
```

Server runs on `http://localhost:5000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

Frontend runs on `http://localhost:5173` (or configured Vite port)

## 📚 Documentation

- **[Backend API Documentation](./backend/README.md)** - API endpoints, parameters, and responses
- **[Frontend README](./frontend/README.md)** - Frontend setup and build instructions

## 🛠️ Tech Stack

### Backend
- **Framework**: Flask 3.0
- **Forecasting**: Facebook Prophet 1.1
- **ML/Clustering**: scikit-learn 1.3
- **Data Processing**: pandas 2.1, numpy 1.24
- **CORS**: flask-cors 4.0

### Frontend
- **UI Framework**: React 19
- **Build Tool**: Vite 6.2
- **Routing**: React Router 7.3
- **Charting**: Chart.js 4.4, react-chartjs-2 5.3
- **Styling**: Tailwind CSS 4.0
- **Date Picker**: react-datepicker 8.1
- **Animation**: Framer Motion 12.4

## 📊 Features

### Sales Forecasting
- Predict sales for specific store and product combinations
- 365-day forecast with confidence intervals
- Historical data comparison

### Cluster Analysis
- Automatic optimal cluster detection (elbow method)
- Category-based sales pattern identification
- Multi-store comparison

### Interactive Dashboard
- Store selection interface
- Dynamic chart visualizations
- Date range filtering
- Cluster visualization

## 🔧 Environment Variables

Create a `.env` file from `.env.example`:

```env
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_PORT=5000
VITE_API_URL=http://localhost:5000
```

## 📝 Data Format

The application works with historical sales data in CSV format with the following fields:
- Date
- Store ID (S001-S005)
- Product Name (20 auto parts)
- Category (Accessories, Breaks, Cooling System, Electrical, Engine)
- Region (East, North, South, West)
- EWMA (Exponentially Weighted Moving Average)

## 🔄 API Flow

1. **Frontend** → Sends forecast request to backend
2. **Backend** → Processes with Prophet model
3. **Backend** → Returns forecast data with confidence intervals
4. **Frontend** → Displays predictions in interactive charts

## 📦 Build & Deploy

### Build Frontend
```bash
cd frontend
npm run build
```

### Production Checklist
- [ ] Set `FLASK_DEBUG=False` in backend
- [ ] Set `FLASK_ENV=production` in backend
- [ ] Configure proper CORS origins
- [ ] Set up database/persistent storage
- [ ] Add authentication if needed
- [ ] Enable HTTPS
- [ ] Set up logging and monitoring

## 🐛 Common Issues

**Backend path error for data.csv**: Update the path in `server.py` if running from different directory
**CORS errors**: Ensure backend CORS is configured for frontend URL
**Module not found**: Verify all requirements are installed with `pip install -r requirements.txt`

## 📞 Support

For issues with specific endpoints, see [Backend API Documentation](./backend/README.md)

## 📄 License

[Add your license here]
