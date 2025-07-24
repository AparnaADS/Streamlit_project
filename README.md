# 📊 Profit & Loss Dashboard

A beautiful and comprehensive Streamlit application for analyzing Profit & Loss statements with interactive visualizations and detailed reporting.

## 🚀 Features

- **📊 Interactive Charts**: Beautiful visualizations using Plotly
- **📋 Detailed P&L Statements**: Formatted tables with proper currency formatting
- **📈 Key Metrics**: Important financial KPIs and ratios
- **🌊 Waterfall Charts**: Visual breakdown of profit/loss components
- **💰 Gauge Charts**: Net profit/loss indicators
- **📁 Data Export**: Download P&L data as CSV
- **🔧 Raw Data View**: Debug and inspect raw API responses
- **📱 Responsive Design**: Works on desktop and mobile devices

## 🛠️ Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (for live API access):
   Create a `.env` file in the project root with:
   ```
   ZOHO_CLIENT_ID=your_client_id
   ZOHO_CLIENT_SECRET=your_client_secret
   ZOHO_REFRESH_TOKEN=your_refresh_token
   ZOHO_ORG_ID=your_organization_id
   ZOHO_ACCESS_TOKEN=your_access_token
   ```

## 🎯 Usage

### Running the Application

```bash
streamlit run app.py
```

### Data Sources

The app supports two data sources:

1. **Live API**: Connect to Zoho Books API for real-time data
2. **Sample Data**: Use the included `profit_and_loss.json` for testing

### Navigation

The app is organized into four main tabs:

1. **📊 Overview**: Key metrics, gauge charts, and summary visualizations
2. **📋 Detailed Statement**: Complete P&L statement with proper formatting
3. **📈 Charts & Analytics**: Interactive charts and additional analytics
4. **🔧 Raw Data**: Debug information and raw JSON data

## 📁 Project Structure

```
Streamlit_project/
├── app.py                          # Main Streamlit application
├── components/                     # Reusable UI components
│   ├── __init__.py
│   ├── pnl_charts.py             # Chart components
│   ├── pnl_table.py              # Table display components
│   └── pnl_metrics.py            # Metrics and KPI components
├── profit_and_loss.json           # Sample P&L data
├── requirements.txt               # Python dependencies
└── README.md                     # This file
```

## 🎨 Components

### Charts (`components/pnl_charts.py`)
- **Summary Chart**: Bar chart showing main P&L sections
- **Gauge Chart**: Net profit/loss indicator
- **Expense Breakdown**: Pie chart of expense categories
- **Trend Chart**: Historical P&L trends

### Tables (`components/pnl_table.py`)
- **Formatted P&L Statement**: Properly formatted table with currency
- **Data Export**: CSV download functionality
- **Raw Data Display**: JSON viewer for debugging

### Metrics (`components/pnl_metrics.py`)
- **Key Performance Indicators**: Important financial metrics
- **Margin Analysis**: Profit margin calculations
- **Waterfall Chart**: Visual profit/loss breakdown

## 📊 Data Structure

The app expects P&L data in the following format:

```json
{
  "code": 0,
  "message": "success",
  "profit_and_loss": [
    {
      "name": "Gross Profit",
      "total": -3400,
      "account_transactions": [
        {
          "name": "Operating Income",
          "total": 0,
          "account_transactions": []
        },
        {
          "name": "Cost of Goods Sold",
          "total": 3400,
          "account_transactions": [
            {
              "name": "Job Costing",
              "total": 3400
            }
          ]
        }
      ]
    }
  ]
}
```

## 🎯 Key Features

### Currency Formatting
- Proper formatting with parentheses for negative values
- Thousands separators for readability
- Consistent decimal places

### Interactive Visualizations
- Hover tooltips with detailed information
- Zoom and pan capabilities
- Export charts as images

### Responsive Design
- Works on desktop and mobile devices
- Adaptive layouts for different screen sizes
- Touch-friendly controls

### Data Validation
- Error handling for API failures
- Data structure validation
- Graceful fallbacks for missing data

## 🔧 Configuration

### Environment Variables
- `ZOHO_CLIENT_ID`: Your Zoho Books API client ID
- `ZOHO_CLIENT_SECRET`: Your Zoho Books API client secret
- `ZOHO_REFRESH_TOKEN`: Your Zoho Books API refresh token
- `ZOHO_ORG_ID`: Your Zoho Books organization ID
- `ZOHO_ACCESS_TOKEN`: Your Zoho Books API access token

### Customization
- Modify chart colors in `components/pnl_charts.py`
- Adjust table styling in `components/pnl_table.py`
- Add new metrics in `components/pnl_metrics.py`

## 🚀 Deployment

### Local Development
```bash
streamlit run app.py
```

### Cloud Deployment
The app can be deployed to:
- Streamlit Cloud
- Heroku
- AWS/GCP/Azure
- Any platform supporting Streamlit

## 📈 Future Enhancements

- [ ] Historical trend analysis
- [ ] Comparative period analysis
- [ ] Budget vs actual comparisons
- [ ] Export to PDF functionality
- [ ] Email reporting
- [ ] Custom date range presets
- [ ] Multi-currency support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

For issues or questions:
1. Check the documentation
2. Review the sample data structure
3. Verify your API credentials
4. Check the console for error messages

---

**Happy analyzing! 📊✨** 