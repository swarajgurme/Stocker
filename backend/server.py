from flask import Flask, request, jsonify
import pandas as pd
from prophet import Prophet
from flask_cors import CORS
from sklearn.cluster import KMeans
import numpy as np
import logging
import time
from datetime import datetime, timedelta
import os
from functools import wraps
from typing import Dict, Any, Tuple
import traceback
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# ============= LOGGING CONFIGURATION =============
# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("Stocker Application Starting")
logger.info("=" * 60)

# ============= FLASK APP INITIALIZATION =============
app = Flask(__name__)

# Enhanced CORS Configuration
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')
CORS(app, 
     origins=[origin.strip() for origin in cors_origins],
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'OPTIONS'],
     max_age=3600)

logger.info(f"CORS configured for origins: {cors_origins}")

# ============= DATA LOADING =============
try:
    logger.info("Loading historical sales data from CSV...")
    df = pd.read_csv("backend/data.csv")
    logger.info(f"CSV loaded successfully: {len(df)} records")
    
    df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
    df = df.set_index('Date', drop=True)
    
    # Calculate inventory levels
    df_inventory = df.copy()
    df_inventory['Inventory Level'] = df_inventory['EWMA'] * 1.5
    
    # Prepare category sales data
    category_sales = df.groupby(['Category', 'Store ID'])['EWMA'].sum().reset_index()
    
    logger.info(f"Data preparation complete: {len(df)} records, {len(category_sales)} category-store combinations")
except Exception as e:
    logger.error(f"Error loading data: {str(e)}\n{traceback.format_exc()}")
    raise

# ============= LABEL MAPPINGS =============
label_mappings = {
    "Store ID": {
        "S001": 0, "S002": 1, "S003": 2, "S004": 3, "S005": 4
    },
    "Product Name": {
        "Air Filter": 0, "Alternator": 1, "Battery": 2, "Brake Pad": 3, "Coolant": 4,
        "Disc Rotor": 5, "Engine Oil": 6, "Fans": 7, "Fuse": 8, "LED": 9,
        "Radiator": 10, "Rearview Mirror": 11, "Resistors": 12, "Sensor": 13,
        "Sideview Mirror": 14, "Spark Plugs": 15, "Thermostat": 16, "Water Pump": 17,
        "Windshield": 18, "Wires": 19
    },
    "Category": {
        "Accessories": 0, "Breaks": 1, "Cooling System": 2, "Electrical": 3, "Engine": 4
    },
    "Region": {
        "East": 0, "North": 1, "South": 2, "West": 3
    }
}

# ============= INPUT VALIDATION =============
VALID_STORES = {"S001", "S002", "S003", "S004", "S005"}
VALID_PRODUCTS = {
    "Air Filter", "Alternator", "Battery", "Brake Pad", "Coolant",
    "Disc Rotor", "Engine Oil", "Fans", "Fuse", "LED",
    "Radiator", "Rearview Mirror", "Resistors", "Sensor",
    "Sideview Mirror", "Spark Plugs", "Thermostat", "Water Pump",
    "Windshield", "Wires"
}
VALID_CATEGORIES = {"Accessories", "Breaks", "Cooling System", "Electrical", "Engine"}
VALID_REGIONS = {"East", "North", "South", "West"}

def validate_input(store_id: str, product_name: str, start_date: str, end_date: str) -> Tuple[bool, str]:
    """
    Validate all input parameters
    
    Args:
        store_id: Store identifier (S001-S005)
        product_name: Product name from catalog
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    # Validate store_id
    if not store_id or store_id not in VALID_STORES:
        return False, f"Invalid Store ID: {store_id}. Valid options: {sorted(VALID_STORES)}"
    
    # Validate product_name
    if not product_name or product_name not in VALID_PRODUCTS:
        return False, f"Invalid Product Name: {product_name}. Valid options: {sorted(VALID_PRODUCTS)}"
    
    # Validate date format
    try:
        start = pd.to_datetime(start_date, format='%Y-%m-%d')
        end = pd.to_datetime(end_date, format='%Y-%m-%d')
    except (ValueError, TypeError):
        return False, "Invalid date format. Use YYYY-MM-DD (e.g., 2024-01-01)"
    
    # Validate date logic
    if start > end:
        return False, "Start date must be before end date"
    
    # Validate date range
    if (end - start).days > 730:
        return False, "Date range cannot exceed 730 days (2 years)"
    
    return True, ""

# ============= PERFORMANCE MONITORING DECORATOR =============
def track_request_time(func):
    """
    Decorator to track API request execution time and log details
    
    Logs request start, completion, and execution time
    Captures exceptions with timing information
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        request_id = f"{datetime.utcnow().timestamp():.0f}"
        
        logger.info(f"[{request_id}] {request.method} {request.path} - Request started")
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Log based on execution time
            if execution_time > 5:
                logger.warning(f"[{request_id}] Request completed in {execution_time:.2f}s (slow)")
            else:
                logger.info(f"[{request_id}] Request completed in {execution_time:.2f}s")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[{request_id}] Request failed after {execution_time:.2f}s: {str(e)}")
            raise
    
    return wrapper

# ============= HEALTH CHECK ENDPOINT =============
@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring system status
    
    Returns:
        JSON with health status, uptime, data info
    """
    try:
        # Check if data is loaded
        data_status = "OK" if not df.empty else "NO_DATA"
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "data_loaded": data_status,
            "records_count": len(df),
            "stores": len(VALID_STORES),
            "products": len(VALID_PRODUCTS),
            "version": "2.0"
        }
        
        logger.info("Health check passed")
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

# ============= FORECAST ENDPOINT =============
@app.route('/forecast', methods=['POST'])
@track_request_time
def forecast_sales():
    """
    Generate 365-day sales forecast for a store-product combination
    
    Request Body:
        {
            "store_id": "S001-S005",
            "product_name": "string",
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD"
        }
    
    Returns:
        JSON with actual and predicted sales data, confidence intervals
    
    Response Codes:
        200: Success
        400: Invalid input parameters
        404: No data found
        500: Internal server error
    """
    request_id = f"{datetime.utcnow().timestamp():.0f}"
    
    try:
        # Extract JSON data
        data = request.get_json()
        
        if not data:
            logger.warning(f"[{request_id}] Empty request body")
            return jsonify({
                "status": "error",
                "error": "Request body cannot be empty",
                "code": "INVALID_INPUT",
                "timestamp": datetime.utcnow().isoformat()
            }), 400
        
        # Extract and sanitize inputs
        store_id = str(data.get("store_id", "")).strip()
        product_name = str(data.get("product_name", "")).strip()
        start_date = str(data.get("start_date", "")).strip()
        end_date = str(data.get("end_date", "")).strip()
        
        logger.info(f"[{request_id}] Forecast request: {store_id}/{product_name} ({start_date} to {end_date})")
        
        # Validate inputs (NFR-REL-002)
        is_valid, error_msg = validate_input(store_id, product_name, start_date, end_date)
        if not is_valid:
            logger.warning(f"[{request_id}] Validation failed: {error_msg}")
            return jsonify({
                "status": "error",
                "error": error_msg,
                "code": "VALIDATION_ERROR",
                "timestamp": datetime.utcnow().isoformat()
            }), 400
        
        # Encode store and product IDs
        store_id_encoded = label_mappings['Store ID'].get(store_id)
        product_name_encoded = label_mappings['Product Name'].get(product_name)
        
        # Filter data for store and product
        store_product_filter = (df["Store ID"] == store_id_encoded) & (df["Product Name"] == product_name_encoded)
        df_filtered = df[store_product_filter].copy()
        
        if df_filtered.empty:
            logger.warning(f"[{request_id}] No data available for {store_id}/{product_name}")
            return jsonify({
                "status": "error",
                "error": f"No historical data available for Store {store_id} - Product {product_name}",
                "code": "NO_DATA",
                "timestamp": datetime.utcnow().isoformat()
            }), 404
        
        # Prepare data for Prophet
        df_prophet = df_filtered.reset_index().rename(columns={'Date': 'ds', 'EWMA': 'y'})
        df_prophet['ds'] = pd.to_datetime(df_prophet['ds'])
        
        logger.info(f"[{request_id}] Training Prophet model with {len(df_prophet)} historical records")
        
        # Train Prophet model with suppressed output
        model = Prophet(interval_width=0.95, daily_seasonality=False)  # 95% confidence interval
        
        # Suppress Prophet's verbose output
        with open(os.devnull, 'w') as devnull:
            old_stdout = sys.stdout
            sys.stdout = devnull
            model.fit(df_prophet)
            sys.stdout = old_stdout
        
        logger.info(f"[{request_id}] Prophet model trained successfully")
        
        # Generate 365-day forecast
        future = model.make_future_dataframe(periods=365, freq='D')
        forecast = model.predict(future)
        
        # Filter to requested date range
        forecast_filtered = forecast[(forecast["ds"].astype(str) >= start_date) & (forecast["ds"].astype(str) <= end_date)]
        actual_filtered = df_prophet[(df_prophet["ds"].astype(str) >= start_date) & (df_prophet["ds"].astype(str) <= end_date)]
        
        logger.info(f"[{request_id}] Forecast generated: {len(forecast_filtered)} records in date range")
        
        # Format actual sales
        actual_sales = [
            {
                "date": row["ds"].strftime("%Y-%m-%d"),
                "actual": round(float(row["y"]), 2)
            }
            for _, row in actual_filtered.iterrows()
        ]
        
        # Format predicted sales with confidence intervals
        predicted_sales = [
            {
                "date": row["ds"].strftime("%Y-%m-%d"),
                "predicted": round(float(row["yhat"]), 2),
                "lower_bound": round(float(row["yhat_lower"]), 2),
                "upper_bound": round(float(row["yhat_upper"]), 2)
            }
            for _, row in forecast_filtered.iterrows()
        ]
        
        # Build standardized response (NFR-MAINT-001)
        response = {
            "status": "success",
            "data": {
                "store_id": store_id,
                "product_name": product_name,
                "forecast_period": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "actual_sales": actual_sales,
                "predicted_sales": predicted_sales,
                "metrics": {
                    "historical_records": len(actual_filtered),
                    "forecast_records": len(predicted_sales),
                    "confidence_interval": "95%"
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"[{request_id}] Forecast response prepared successfully")
        return jsonify(response), 200
        
    except pd.errors.ParserError as e:
        logger.error(f"[{request_id}] Data parsing error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "error": "Error parsing forecast data",
            "code": "PARSE_ERROR",
            "details": str(e) if os.getenv('FLASK_ENV') == 'development' else None,
            "timestamp": datetime.utcnow().isoformat()
        }), 500
        
    except Exception as e:
        logger.error(f"[{request_id}] Forecast error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "error": "An unexpected error occurred during forecasting",
            "code": "FORECAST_ERROR",
            "details": str(e) if os.getenv('FLASK_ENV') == 'development' else None,
            "timestamp": datetime.utcnow().isoformat()
        }), 500

# ============= CLUSTERING ENDPOINT =============
@app.route('/clustering', methods=['GET'])
@track_request_time
def clustering():
    """
    Perform K-means clustering on category-store sales patterns
    
    Automatically determines optimal cluster count using elbow method
    Groups data by Category and Store ID
    
    Returns:
        JSON with cluster assignments and statistics
    
    Response Codes:
        200: Success
        400: Insufficient data
        404: No data available
        500: Internal server error
    """
    request_id = f"{datetime.utcnow().timestamp():.0f}"
    
    try:
        logger.info(f"[{request_id}] Starting clustering analysis...")
        
        # Check if data is available
        if category_sales.empty:
            logger.warning(f"[{request_id}] No category sales data available")
            return jsonify({
                "status": "error",
                "error": "No data available for clustering",
                "code": "NO_DATA",
                "timestamp": datetime.utcnow().isoformat()
            }), 404
        
        # Prepare data for clustering
        X = category_sales[['EWMA']].values
        
        if len(X) < 2:
            logger.warning(f"[{request_id}] Insufficient data for clustering: {len(X)} records")
            return jsonify({
                "status": "error",
                "error": "Insufficient data for clustering (minimum 2 records required)",
                "code": "INSUFFICIENT_DATA",
                "timestamp": datetime.utcnow().isoformat()
            }), 400
        
        # Run elbow method to find optimal k (NFR-REL-001)
        logger.info(f"[{request_id}] Running elbow method analysis (k=1 to {min(6, len(X))})")
        inertia = []
        silhouette_scores = []
        
        for k in range(1, min(6, len(X) + 1)):  # Test k from 1 to min(5, data_size)
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(X)
            inertia.append(kmeans.inertia_)
        
        # Find optimal k (elbow point)
        if len(inertia) >= 2:
            # Calculate differences to find elbow
            inertia_diffs = np.diff(inertia)
            optimal_k = np.argmax(inertia_diffs) + 1
            optimal_k = min(optimal_k + 1, len(X))  # Ensure k <= data size
        else:
            optimal_k = 1
        
        logger.info(f"[{request_id}] Optimal clusters determined: k={optimal_k}")
        
        # Apply K-means with optimal k
        kmeans_final = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
        category_sales['Cluster'] = kmeans_final.fit_predict(X)
        
        # Format cluster data
        cluster_data = []
        for _, row in category_sales.iterrows():
            cluster_data.append({
                "category": str(row['Category']),
                "store_id": int(row['Store ID']),
                "sales": round(float(row['EWMA']), 2),
                "cluster": int(row['Cluster'])
            })
        
        logger.info(f"[{request_id}] Cluster assignments completed: {len(cluster_data)} records")
        
        # Calculate cluster statistics
        cluster_stats = {}
        for item in cluster_data:
            c = item['cluster']
            if c not in cluster_stats:
                cluster_stats[c] = {
                    "count": 0,
                    "total_sales": 0.0,
                    "avg_sales": 0.0
                }
            cluster_stats[c]["count"] += 1
            cluster_stats[c]["total_sales"] += item['sales']
        
        # Calculate averages
        for c in cluster_stats:
            cluster_stats[c]["avg_sales"] = round(
                cluster_stats[c]["total_sales"] / cluster_stats[c]["count"], 2
            )
        
        # Build standardized response
        response = {
            "status": "success",
            "data": {
                "optimal_clusters": optimal_k,
                "total_records": len(cluster_data),
                "clusters": cluster_data,
                "statistics": cluster_stats
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"[{request_id}] Clustering response prepared successfully")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"[{request_id}] Clustering error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "error": "An error occurred during clustering analysis",
            "code": "CLUSTERING_ERROR",
            "details": str(e) if os.getenv('FLASK_ENV') == 'development' else None,
            "timestamp": datetime.utcnow().isoformat()
        }), 500

# ============= GLOBAL ERROR HANDLERS =============
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 Not Found errors"""
    logger.warning(f"404 Error: {request.path} not found")
    return jsonify({
        "status": "error",
        "error": "Endpoint not found",
        "code": "NOT_FOUND",
        "path": request.path,
        "timestamp": datetime.utcnow().isoformat()
    }), 404

@app.errorhandler(405)
def method_not_allowed_error(error):
    """Handle 405 Method Not Allowed errors"""
    logger.warning(f"405 Error: {request.method} not allowed on {request.path}")
    return jsonify({
        "status": "error",
        "error": "Method not allowed",
        "code": "METHOD_NOT_ALLOWED",
        "method": request.method,
        "path": request.path,
        "timestamp": datetime.utcnow().isoformat()
    }), 405

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors"""
    logger.error(f"500 Error: {str(error)}\n{traceback.format_exc()}")
    return jsonify({
        "status": "error",
        "error": "Internal server error",
        "code": "INTERNAL_ERROR",
        "timestamp": datetime.utcnow().isoformat()
    }), 500

# ============= MAIN BLOCK =============
if __name__ == '__main__':
    # Load configuration from environment variables
    flask_env = os.getenv('FLASK_ENV', 'development')
    flask_debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    flask_port = int(os.getenv('FLASK_PORT', 5000))
    flask_host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    logger.info("=" * 60)
    logger.info(f"Stocker API Server Configuration")
    logger.info(f"Environment: {flask_env}")
    logger.info(f"Debug Mode: {flask_debug}")
    logger.info(f"Host: {flask_host}")
    logger.info(f"Port: {flask_port}")
    logger.info(f"Data Records: {len(df)}")
    logger.info(f"Stores: {len(VALID_STORES)}")
    logger.info(f"Products: {len(VALID_PRODUCTS)}")
    logger.info("=" * 60)
    
    # Run Flask application
    app.run(
        host=flask_host,
        port=flask_port,
        debug=flask_debug
    )
