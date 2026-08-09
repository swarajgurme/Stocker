"""
Report Service
Generates PDF and Excel reports using report templates
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd
from sqlalchemy import func

from models import Sale, Product, Forecast, InventoryLevel

logger = logging.getLogger(__name__)

# Optional: WeasyPrint for PDF generation
# from weasyprint import HTML, CSS

# Optional: openpyxl for Excel
# from openpyxl import Workbook
# from openpyxl.styles import Font, PatternFill, Alignment

reports_dir = 'reports'
os.makedirs(reports_dir, exist_ok=True)


class ReportService:
    """Service for generating business reports"""

    def __init__(self):
        self.reports_dir = reports_dir

    def generate_report(
        self,
        report_type: str,
        format,
        store_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_forecasts: bool = True,
        include_inventory: bool = True,
        user_id: Optional[int] = None
    ) -> str:
        """
        Generate a report file

        Args:
            report_type: Type of report (executive_summary, forecast, inventory, cluster)
            format: PDF, Excel, or CSV
            store_id: Optional store filter
            start_date, end_date: Date range for data
            include_forecasts: Include forecast data
            include_inventory: Include inventory data
            user_id: User requesting the report

        Returns:
            File path to generated report
        """
        logger.info(f"Generating {report_type} report in {format.value} format")

        # Generate unique filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{report_type}_{timestamp}.{format.value}"
        filepath = os.path.join(self.reports_dir, filename)

        # Gather data
        data = self._collect_report_data(
            report_type=report_type,
            store_id=store_id,
            start_date=start_date,
            end_date=end_date,
            include_forecasts=include_forecasts,
            include_inventory=include_inventory,
        )

        # Generate based on format
        if format.value == 'pdf':
            self._generate_pdf(data, filepath, report_type)
        elif format.value == 'excel':
            self._generate_excel(data, filepath, report_type)
        elif format.value == 'csv':
            self._generate_csv(data, filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Report generated: {filepath}")
        return filepath

    def _collect_report_data(
        self,
        report_type: str,
        store_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_forecasts: bool = True,
        include_inventory: bool = True,
    ) -> Dict:
        """Collect all data needed for the report"""
        from database import get_db_session

        data = {
            "generated_at": datetime.utcnow().isoformat(),
            "report_type": report_type,
            "filters": {"store_id": store_id, "date_range": f"{start_date} to {end_date}"}
        }

        with get_db_session() as db:
            # Revenue/sales summary
            sales_query = db.query(
                func.sum(Sale.revenue).label('total_revenue'),
                func.sum(Sale.quantity).label('total_units')
            )
            if store_id:
                sales_query = sales_query.filter(Sale.store_id == store_id)
            if start_date and end_date:
                sales_query = sales_query.filter(
                    Sale.sale_date.between(
                        datetime.strptime(start_date, '%Y-%m-%d').date(),
                        datetime.strptime(end_date, '%Y-%m-%d').date()
                    )
                )
            summary = sales_query.first()
            data["summary"] = {
                "total_revenue": round(float(summary.total_revenue or 0), 2),
                "total_units": int(summary.total_units or 0)
            }

            # Category performance
            cat_query = db.query(
                Product.category,
                func.sum(Sale.revenue).label('revenue'),
                func.sum(Sale.quantity).label('units')
            ).join(Product, Sale.product_id == Product.id)
            if store_id:
                cat_query = cat_query.filter(Sale.store_id == store_id)
            if start_date and end_date:
                cat_query = cat_query.filter(
                    Sale.sale_date.between(
                        datetime.strptime(start_date, '%Y-%m-%d').date(),
                        datetime.strptime(end_date, '%Y-%m-%d').date()
                    )
                )
            cat_query = cat_query.group_by(Product.category).order_by(func.sum(Sale.revenue).desc())

            data["by_category"] = [{
                "category": row.category,
                "revenue": round(float(row.revenue or 0), 2),
                "units": int(row.units or 0)
            } for row in cat_query.all()]

            if include_inventory:
                alert_count = db.query(InventoryLevel).filter(
                    InventoryLevel.current_stock < InventoryLevel.safety_stock
                ).count()
                avg_stock = db.query(func.avg(InventoryLevel.current_stock)).scalar() or 0
                data["inventory"] = {
                    "critical_alerts": alert_count,
                    "avg_stock_level": round(float(avg_stock), 2),
                }

            if include_forecasts:
                avg_mape = db.query(func.avg(Forecast.mape)).filter(
                    Forecast.created_at >= datetime.utcnow() - timedelta(days=30),
                    Forecast.status == 'completed'
                ).scalar()
                data["forecast_accuracy"] = {
                    "avg_mape": round(float(avg_mape or 0), 2)
                }

        return data

    def _generate_pdf(self, data: Dict, filepath: str, report_type: str):
        """Generate PDF report (requires WeasyPrint)"""
        try:
            from weasyprint import HTML, CSS

            # Generate HTML first (simple template)
            html_content = self._generate_html(data, report_type)

            HTML(string=html_content).write_pdf(
                filepath,
                stylesheets=[CSS(string='''
                    @page { size: A4; margin: 1cm; }
                    body { font-family: Arial, sans-serif; }
                    h1 { color: #31837A; }
                    table { width: 100%; border-collapse: collapse; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                ''')]
            )
        except ImportError:
            logger.warning("WeasyPrint not installed, generating CSV instead")
            self._generate_csv(data, filepath.replace('.pdf', '.csv'))

    def _generate_excel(self, data: Dict, filepath: str, report_type: str):
        """Generate Excel report"""
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Report Summary"

            # Header
            ws['A1'] = f"Stocker Enterprise Report - {report_type.replace('_', ' ').title()}"
            ws['A1'].font = Font(bold=True, size=14, color='31837A')
            ws.merge_cells('A1:D1')
            ws['A2'] = f"Generated: {data['generated_at']}"
            ws['A2'].font = Font(italic=True, size=10)
            ws.merge_cells('A2:D2')

            # Summary table
            ws['A4'] = "Metric"
            ws['B4'] = "Value"
            ws['A4'].font = Font(bold=True)
            ws['B4'].font = Font(bold=True)

            ws['A5'] = "Total Revenue"
            ws['B5'] = data['summary']['total_revenue']
            ws['A6'] = "Total Units Sold"
            ws['B6'] = data['summary']['total_units']

            # Category breakdown
            if data.get('by_category'):
                ws['A8'] = "Category Performance"
                ws['A8'].font = Font(bold=True)
                ws['A9'] = "Category"
                ws['B9'] = "Revenue"
                ws['C9'] = "Units"
                row = 10
                for cat in data['by_category']:
                    ws[f'A{row}'] = cat['category']
                    ws[f'B{row}'] = cat['revenue']
                    ws[f'C{row}'] = cat['units']
                    row += 1

            wb.save(filepath)
            logger.info(f"Excel report saved: {filepath}")

        except ImportError:
            logger.warning("openpyxl not installed, generating CSV")
            self._generate_csv(data, filepath.replace('.xlsx', '.csv'))

    def _generate_csv(self, data: Dict, filepath: str):
        """Generate CSV report"""
        lines = [
            ["report", "Stocker Enterprise"],
            ["generated_at", data["generated_at"]],
            ["total_revenue", data["summary"]["total_revenue"]],
            ["total_units", data["summary"]["total_units"]],
            [],
            ["category", "revenue", "units"],
        ]
        for cat in data.get("by_category", []):
            lines.append([cat["category"], cat["revenue"], cat["units"]])
        pd.DataFrame(lines).to_csv(filepath, index=False, header=False)
        logger.info(f"CSV report saved: {filepath}")

    def _generate_html(self, data: Dict, report_type: str) -> str:
        """Generate HTML content for PDF"""
        html = f"""
        <html><head><title>Stocker Report</title></head><body>
        <h1>Stocker Enterprise Report - {report_type.replace('_', ' ').title()}</h1>
        <p><em>Generated: {data['generated_at']}</em></p>

        <h2>Summary</h2>
        <p>Total Revenue: ${data['summary']['total_revenue']:,.2f}</p>
        <p>Total Units Sold: {data['summary']['total_units']:,}</p>

        <h2>Category Performance</h2>
        <table>
            <tr><th>Category</th><th>Revenue</th><th>Units</th></tr>
        """
        for cat in data.get('by_category', []):
            html += f"<tr><td>{cat['category']}</td><td>${cat['revenue']:,.2f}</td><td>{cat['units']}</td></tr>"

        html += "</table></body></html>"
        return html

    @staticmethod
    def calculate_next_run(frequency: str, cron_expr: Optional[str] = None) -> Optional[datetime]:
        """Calculate next run datetime based on frequency"""
        now = datetime.utcnow()

        if cron_expr:
            # Use croniter if available
            try:
                from croniter import croniter
                return croniter(cron_expr, now).get_next(datetime)
            except ImportError:
                pass

        # Fallback simple schedule
        frequency = frequency.lower()
        if frequency == 'daily':
            return now + timedelta(days=1)
        elif frequency == 'weekly':
            return now + timedelta(weeks=1)
        elif frequency == 'monthly':
            # Add 1 month
            month = now.month + 1
            year = now.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            return now.replace(year=year, month=month)
        else:
            return None
