# CDK Backend API

Sales forecasting and cluster analysis backend service built with Flask, Prophet, and scikit-learn.

## Setup & Installation

### Prerequisites
- Python 3.8+
- pip

### Installation

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python server.py
```

The server will run on `http://localhost:5000` by default.

## API Endpoints

### 1. Sales Forecast
**POST** `/forecast`

Generates sales forecasts using Facebook Prophet for a specific store and product.

**Request Body:**
```json
{
  "store_id": "S001",
  "product_name": "Battery",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

**Response:**
```json
{
  "store_id": "S001",
  "product_name": "Battery",
  "actual_sales": [
    {"date": "2024-01-01", "actual": 15.5}
  ],
  "predicted_sales": [
    {
      "date": "2024-01-02",
      "predicted": 16.2,
      "lower_bound": 14.1,
      "upper_bound": 18.3
    }
  ]
}
```

**Parameters:**
- `store_id`: Store identifier (S001-S005)
- `product_name`: Product name (see Products list below)
- `start_date`: Forecast start date (YYYY-MM-DD)
- `end_date`: Forecast end date (YYYY-MM-DD)

### 2. Cluster Analysis
**GET** `/clustering`

Performs K-means clustering on category sales data to identify sales patterns.

**Response:**
```json
{
  "clusters": [
    {
      "category": "Electrical",
      "store_id": 0,
      "sales": 1250.5,
      "cluster": 1
    }
  ]
}
```

## Data Reference

### Stores
- S001, S002, S003, S004, S005

### Products
Air Filter, Alternator, Battery, Brake Pad, Coolant, Disc Rotor, Engine Oil, Fans, Fuse, LED, Radiator, Rearview Mirror, Resistors, Sensor, Sideview Mirror, Spark Plugs, Thermostat, Water Pump, Windshield, Wires

### Categories
- Accessories
- Breaks
- Cooling System
- Electrical
- Engine

### Regions
- East, North, South, West

## Data Source
- `data.csv`: Contains historical sales data with EWMA (Exponentially Weighted Moving Average) calculations

## Error Handling
- **400 Bad Request**: Invalid Store ID or Product Name
- **404 Not Found**: No data available for the requested store and product
- **500 Internal Server Error**: Server-side processing error

## Environment Variables
Create a `.env` file in the backend directory (see `.env.example`):
```
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_PORT=5000
```

## Architecture
- **Flask**: REST API framework with CORS support
- **Prophet**: Time series forecasting for sales predictions
- **scikit-learn**: KMeans clustering for sales pattern analysis
- **pandas**: Data manipulation and processing
