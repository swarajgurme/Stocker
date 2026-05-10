import { useEffect, useState, useCallback } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { forecastAPI, STORES } from "../services/apiClient";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function PredictionChart() {
  const [searchParams] = useSearchParams();
  const { store } = useParams();

  const [forecastData, setForecastData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedInterval, setSelectedInterval] = useState("weekly");
  const [showPredicted, setShowPredicted] = useState(true);
  const [showMin, setShowMin] = useState(true);
  const [showMax, setShowMax] = useState(true);

  const product = searchParams.get("product") || "None";
  const startDate = searchParams.get("startDate") || "";
  const endDate = searchParams.get("endDate") || "";

  const fetchForecast = useCallback(async () => {
    if (!product || product === "None" || !startDate || !endDate) {
      setForecastData(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await forecastAPI.generate({
        store_id: store,
        product_name: product,
        start_date: startDate,
        end_date: endDate,
        horizon_days: 365,
        model_type: "prophet"
      });

      setForecastData({
        store_id: store,
        product_name: product,
        ...result.data
      });
    } catch (err) {
      console.error("Forecast error:", err);
      setError(err.message || "Failed to load forecast");
    } finally {
      setLoading(false);
    }
  }, [store, product, startDate, endDate]);

  useEffect(() => {
    fetchForecast();
  }, [fetchForecast]);

  const filterDates = (allDates, interval) => {
    if (!allDates || allDates.length === 0) return [];

    switch (interval) {
      case "weekly":
        return allDates.filter((_, index) => index % 7 === 0);
      case "monthly":
        return allDates.filter(date => new Date(date).getDate() === 1);
      case "quarterly":
        return allDates.filter(date => {
          const month = new Date(date).getMonth();
          return month === 0 || month === 3 || month === 6 || month === 9;
        });
      default:
        return allDates;
    }
  };

  // const getYAxisLimits = () => {
  //   if (!forecastData || !forecastData.predicted_sales) return {};
  
  //   const allValues = [
  //     ...(showPredicted ? forecastData.predicted_sales.map(item => item.predicted) : []),
  //     ...(showMin ? forecastData.predicted_sales.map(item => item.lower_bound) : []),
  //     ...(showMax ? forecastData.predicted_sales.map(item => item.upper_bound) : []),
  //     ...(forecastData.actual_sales?.map(item => item.actual) || [])
  //   ];
  
  //   const minLimit = Math.min(...allValues) * 0.9;
  //   const maxLimit = Math.max(...allValues) * 1.1;
  
  //   return { min: Math.max(minLimit, 0), max: maxLimit };
  // };
  

  const prepareChartData = () => {
    if (!forecastData || !forecastData.predicted_sales || product === "None") return null;

    const allDates = forecastData.predicted_sales.map(item => item.date);
    const filteredDates = filterDates(allDates, selectedInterval);

    const getFilteredData = key =>
      forecastData.predicted_sales
        .filter(item => filteredDates.includes(item.date))
        .map(item => item[key]);

    const predictedValues = getFilteredData("predicted");
    const minRange = getFilteredData("lower_bound");
    const maxRange = getFilteredData("upper_bound");

    const actualSales = forecastData.predicted_sales
      .filter(item => filteredDates.includes(item.date))
      .map(item => {
        const actualEntry = forecastData.actual_sales?.find(a => a.date === item.date);
        return actualEntry ? actualEntry.actual : null;
      });

    const datasets = [];

    datasets.push({
      label: "Actual Sales",
      data: actualSales,
      borderColor: "rgb(255, 99, 132)",
      backgroundColor: "rgba(255, 99, 132, 0.1)",
      tension: 0.4,
      pointRadius: 3,
      pointBackgroundColor: "rgb(255, 99, 132)",
      fill: false,
    });

    if (showPredicted) {
      datasets.push({
        label: "Predicted Sales",
        data: predictedValues,
        borderColor: "rgb(75, 192, 192)",
        backgroundColor: "rgba(75, 192, 192, 0.1)",
        tension: 0.4,
        pointRadius: 0,
        fill: true,
      });
    }

    if (showMin) {
      datasets.push({
        label: "Minimum Required Units",
        data: minRange,
        borderColor: "rgb(255, 206, 86)",
        backgroundColor: "rgba(255, 206, 86, 0.1)",
        tension: 0.4,
        pointRadius: 0,
        fill: true,
      });
    }

    if (showMax) {
      datasets.push({
        label: "Maximum Required Units",
        data: maxRange,
        borderColor: "rgb(54, 162, 235)",
        backgroundColor: "rgba(54, 162, 235, 0.1)",
        tension: 0.4,
        pointRadius: 0,
        fill: true,
      });
    }
    return {
      labels: filteredDates,
      datasets: datasets,
    };
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { position: "top" },
      title: {
        display: true,
        text: `Sales Forecast for ${product} in ${store}`,
        font: { size: 18 },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: function (tooltipItem) {
            return `${tooltipItem.dataset.label}: ${tooltipItem.raw.toFixed(2)}`;
          }
        }
      },
    },
    scales: {
      x: {
        title: { display: true, text: "Date" },
        grid: { display: false },
      },
      y: {
        title: { display: true, text: "Sales" },
        grid: { color: "rgba(200, 200, 200, 0.3)" },
        // ...getYAxisLimits()
      },
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false,
    }
  };

  const calculateFutureUnits = () => {
    if (!forecastData || !forecastData.predicted_sales || product === "None") return null;
    const today = new Date("2024-01-01");
    if (new Date(endDate) <= today) return null;

    const futureSales = forecastData.predicted_sales.filter(item => new Date(item.date) >= today && new Date(item.date) <= new Date(endDate));
    if (futureSales.length === 0) return null;

    var minRequiredUnits = futureSales.reduce((sum, item) => sum + item.lower_bound, 0);
    var maxRequiredUnits = futureSales.reduce((sum, item) => sum + item.upper_bound, 0);    

    minRequiredUnits += minRequiredUnits * 0.1;
    maxRequiredUnits += maxRequiredUnits * 0.1;

    if (minRequiredUnits < 0) minRequiredUnits = 0;
    if (maxRequiredUnits < 0) maxRequiredUnits = 0;

    return { minRequiredUnits, maxRequiredUnits };
  };

  const futureUnits = calculateFutureUnits();

  // Render loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#31837A] mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading forecast...</p>
        </div>
      </div>
    );
  }

  // Render error
  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-xl">
        <div className="flex items-center">
          <svg className="w-6 h-6 text-red-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <h3 className="text-lg font-semibold text-red-800">Error Loading Forecast</h3>
        </div>
        <p className="mt-2 text-red-700">{error}</p>
        <button
          onClick={fetchForecast}
          className="mt-4 px-4 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200 transition"
        >
          Retry
        </button>
      </div>
    );
  }

  // Render no data yet
  if (!forecastData || !product || product === "None") {
    return (
      <div className="m-4 p-6 rounded-xl bg-gray-100 border border-gray-200 text-center">
        <p className="text-gray-500">Select a store and product to view forecast</p>
      </div>
    );
  }


  return (
    <div className="m-4 p-6 rounded-xl bg-white shadow-md border border-gray-200 flex flex-col gap-8">
      <div className="flex-1 space-y-4">
        <div className="flex items-center space-x-3">
          <label htmlFor="interval" className="text-lg font-semibold">Interval:</label>
          <select
            id="interval"
            value={selectedInterval}
            onChange={e => setSelectedInterval(e.target.value)}
            className="p-2 border rounded-md outline-none focus:ring-2 focus:ring-[#31837A]"
          >
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
          </select>

          <div className="flex items-center space-x-3">
            <input
              type="checkbox"
              id="predicted"
              checked={showPredicted}
              onChange={(e) => setShowPredicted(e.target.checked)}
            />
            <label htmlFor="predicted" className="text-sm">
              Predicted Sales
            </label>
            <input
              type="checkbox"
              id="min"
              checked={showMin}
              onChange={(e) => setShowMin(e.target.checked)}
            />
            <label htmlFor="min" className="text-sm">
              Minimum Required Units
            </label>
            <input
              type="checkbox"
              id="max"
              checked={showMax}
              onChange={(e) => setShowMax(e.target.checked)}
            />
            <label htmlFor="max" className="text-sm">
              Maximum Required Units
            </label>
          </div>
        </div>

        { product!="None" && forecastData && prepareChartData() &&(
          <div className="flex-1 p-6 rounded-lg shadow-md bg-gradient-to-r from-[#4CAF50] to-[#31837A] text-white space-y-4">
          <h2 className="text-2xl font-bold flex justify-center">Forecast Summary</h2>

          <div className="flex justify-center space-x-100">
            <div>
              <div><p className="font-semibold">Product: {product}</p></div>
              <div><p className="font-semibold">Store Location: {store}</p></div>
              <div><p className="font-semibold">Start Date: {startDate}</p></div>
              <div><p className="font-semibold">End Date: {endDate}</p></div>
            </div>
            <div>
              <div><p className="font-semibold">Forecast Interval: {selectedInterval}</p></div>
              <div>
                <p className="font-semibold">Min Required Units: {futureUnits ? Math.round(futureUnits.minRequiredUnits) : "N/A"} units</p>
              </div>
              <div>
                <p className="font-semibold">Max Required Units: {futureUnits ? Math.round(futureUnits.maxRequiredUnits) : "N/A"} units</p>
              </div>
            </div>
          </div>
          </div>
        )}

        {forecastData && prepareChartData() && (
          <Line
            className="min-w-[1080px] max-h-[500px] animate-fadeIn"
            data={prepareChartData()}
            options={chartOptions}
          />
        )}
      </div>
    </div>
  );
}
