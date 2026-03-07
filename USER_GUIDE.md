# Business Analyzer - User Guide

Complete guide to using all features of the Business Analyzer application.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Transaction Management](#transaction-management)
4. [Business Management](#business-management)
5. [Inventory Management](#inventory-management)
6. [Analytics & Reporting](#analytics--reporting)
7. [Forecasting](#forecasting)
8. [Report Generation](#report-generation)
9. [Admin Features](#admin-features)
10. [Tips & Best Practices](#tips--best-practices)

---

## Getting Started

### Creating an Account

1. Click **Sign Up** on the home page
2. Fill in the registration form:
   - **Username**: Unique identifier (no spaces)
   - **Email**: Valid email address
   - **Password**: Secure password
   - **Role**: Select your role
     - **Owner**: Full access to all features
     - **Accountant**: Can manage transactions and view reports
     - **Staff**: Read-only access to transactions
3. Click **Sign Up**
4. You'll be redirected to the login page

### Logging In

1. Click **Login**
2. Enter your username and password
3. Click **Login**
4. You'll be taken to the Dashboard

### First-Time Setup

After logging in for the first time:

1. **Create a Business Profile**
   - Navigate to "Businesses" in the sidebar
   - Click "Add New Business"
   - Enter business details
   - Your first business becomes active automatically

2. **Configure Settings** (Optional)
   - Go to Profile → Update currency symbol
   - Set default reorder levels for inventory

---

## Dashboard Overview

The Dashboard is your command center, showing:

### Key Metrics
- **Transactions**: Total number of transactions
- **Total Sales**: Sum of all sales revenue
- **Net Profit**: Sales minus expenses

### Active Business Selector
- Switch between multiple businesses
- Changes apply immediately to all views

### Quick Actions
- View transaction summary
- Access frequently used features
- Monitor business health at a glance

---

## Transaction Management

### Adding Transactions Manually

1. Click **Add Tx** in the sidebar
2. Fill in the transaction form:
   - **Type**: Sales or Expense
   - **Amount**: Transaction value (supports decimals)
   - **Category**: Classification (e.g., "Electronics", "Utilities")
   - **Description**: Optional details
   - **Date**: Transaction date (defaults to today)
3. Click **Add**

**Tips:**
- Use consistent category names for better analytics
- Add descriptions for easier tracking
- Backdate transactions if needed

### Viewing Transactions

1. Click **Transactions** in the sidebar
2. View all transactions in a table format
3. Features:
   - **Sort**: Click column headers
   - **Edit**: Modify transaction details (Owner/Accountant only)
   - **Delete**: Remove transactions (Owner only)
   - **Download**: Export as CSV

### Editing Transactions

**Permissions Required**: Owner or Accountant

1. Go to **Transactions**
2. Click on any cell to edit (except ID and Date)
3. Modify values:
   - Change type (Sales/Expense)
   - Update amount
   - Edit category or description
4. Click **Save Changes**

### Importing Transactions from CSV

1. Click **Import** in the sidebar
2. Click **Choose CSV** and select your file
3. Preview the data
4. Map columns:
   - **Amount column**: Required (contains transaction amounts)
   - **Type column**: Optional (Sales/Expense)
   - **Category column**: Optional
   - **Description column**: Optional
5. Select **Default type** if Type column not mapped
6. Click **IMPORT**
7. Review import results (success/error counts)

**CSV Format Example:**
```csv
Amount,Type,Category,Description
1500.00,Sales,Electronics,Laptop sale
250.50,Expense,Utilities,Monthly electricity
```

**Import Tips:**
- Remove currency symbols (₹, $) from amounts
- Use UTF-8 encoding
- Ensure Amount column has valid numbers
- Check for empty rows

---

## Business Management

### Creating a Business

1. Navigate to **Businesses**
2. Expand "Add New Business"
3. Fill in details:
   - **Business Name**: Required
   - **Type**: Optional (e.g., "Retail", "Services")
   - **Address**: Optional
   - **Phone**: Optional
4. Click **Create**

### Managing Multiple Businesses

**Switching Active Business:**
1. Go to **Dashboard**
2. Use the "Select business" dropdown
3. All data views update automatically

**Editing Business Details:**
1. Go to **Businesses**
2. Find the business you want to edit
3. Click **Edit**
4. Update information
5. Click **Update**

**Deleting a Business:**
1. Go to **Businesses**
2. Click **Delete** (only for non-active businesses)
3. Confirm deletion
4. **Warning**: This deletes all associated transactions and inventory

---

## Inventory Management

### Adding Products

1. Navigate to **Inventory**
2. Click **Add Product** tab
3. Fill in product details:
   - **Product Name**: Required
   - **SKU**: Unique identifier (optional but recommended)
   - **Initial Quantity**: Starting stock level
   - **Cost Price**: What you pay per unit
   - **Selling Price**: What you charge per unit
   - **Reorder Level**: Alert threshold
   - **Category**: Product classification
4. Click **Add Product**

### Viewing Inventory

The **Products** tab shows:
- Product name and SKU
- Current quantity
- Cost and selling prices
- Reorder level
- Stock value (quantity × cost price)

**Low Stock Alerts:**
- Red banner appears when products fall below reorder level
- Click to view which products need restocking

### Recording Stock Movements

1. Go to **Inventory** → **Movement** tab
2. Select product from dropdown
3. View current stock level
4. Choose movement type:
   - **Purchase**: Adding stock (increases quantity)
   - **Sale**: Selling stock (decreases quantity)
   - **Adjustment**: Manual correction
5. Enter quantity
6. For purchases: Enter unit cost (updates average cost)
7. For sales: Enter unit price
8. Add reference number (optional, e.g., invoice number)
9. Add notes (optional)
10. Click **Record Movement**

**Movement Types Explained:**

**Purchase:**
- Increases inventory
- Updates average cost price
- Use when receiving new stock

**Sale:**
- Decreases inventory
- Records unit price
- Checks for sufficient stock
- Use when selling products

**Adjustment:**
- Sets quantity to exact value
- Use for inventory corrections
- Use for damaged/lost items

### Viewing Movement History

1. Go to **Inventory** → **History** tab
2. View last 100 movements
3. See:
   - Date and time
   - Product name
   - Movement type
   - Quantity changed
   - Unit cost/price
   - Notes

---

## Analytics & Reporting

### Sales Dashboard

**Location**: Sidebar → **Sales**

**Features:**
- Sales by category (bar chart)
- Expenses by category (bar chart)
- Monthly trend (line chart)
- Summary metrics

**Use Cases:**
- Identify top-selling categories
- Track expense patterns
- Monitor monthly performance

### Profit Dashboard

**Location**: Sidebar → **Profit**

**Metrics Displayed:**
- **Gross Profit**: Revenue - COGS
- **Net Profit**: Gross Profit - Expenses
- **Gross Margin**: (Gross Profit / Revenue) × 100
- **Net Margin**: (Net Profit / Revenue) × 100

**Charts:**
- Current period overview (bar chart)
- 6-month trend (line chart)
- Monthly margin percentage (bar chart)

### Sales Trends

**Location**: Sidebar → **Trends**

**Features:**
- View by Daily, Weekly, or Monthly
- Interactive line chart
- Summary statistics:
  - Total sales
  - Average per period
  - Number of periods

**Use Cases:**
- Identify seasonal patterns
- Track growth over time
- Spot anomalies

### Profit Margins

**Location**: Sidebar → **Margins**

**Features:**
- Sales vs Expenses comparison
- Margin percentage overlay
- Resample by Daily/Weekly/Monthly
- Summary metrics

**Use Cases:**
- Monitor profitability trends
- Identify periods with low margins
- Compare revenue and costs

### Expense Categories

**Location**: Sidebar → **Categories**

**Features:**
- Expense breakdown by category (pie chart)
- Sales breakdown by category (bar chart)
- Filter by time period:
  - All time
  - Last 30 days
  - Last 7 days
  - This year

**Use Cases:**
- Identify major expense categories
- Budget planning
- Cost reduction opportunities

### COGS Analysis

**Location**: Sidebar → **COGS**

**Features:**
- Monthly revenue vs COGS
- Gross profit calculation
- Margin percentage trend
- Summary metrics

**Use Cases:**
- Understand product profitability
- Track cost efficiency
- Optimize pricing strategy

---

## Forecasting

**Location**: Sidebar → **Forecast**

### Understanding Forecasting

The app uses AI to predict future sales or profit based on historical data.

**Methods:**
1. **Facebook Prophet**: Advanced forecasting with seasonality
2. **Linear Regression**: Simple trend-based fallback

### Using the Forecasting Tool

1. Navigate to **Forecast**
2. Review data availability:
   - Green checkmark (✓): Enough data
   - Red X (✗): Insufficient data (need 3+ points)
3. Select options:
   - **Forecast**: Sales or Profit
   - **Frequency**: Daily, Weekly, or Monthly
   - **Horizon**: How far to predict
4. Click **Generate Forecast**

### Interpreting Results

**Chart Elements:**
- **Blue line**: Historical actual data
- **Orange dashed line**: Predicted values
- **Shaded area**: Confidence interval (uncertainty range)

**Metrics:**
- **Next Period Prediction**: Forecasted value for next period

**Forecast Table:**
- Date/period
- Predicted value (yhat)
- Lower bound (yhat_lower)
- Upper bound (yhat_upper)

### Forecasting Requirements

**Minimum Data:**
- Daily: 3+ days with transactions
- Weekly: 3+ weeks with transactions
- Monthly: 3+ months with transactions

**Data Quality Tips:**
- More data = better predictions
- Consistent data entry improves accuracy
- Spread transactions across multiple dates
- Avoid large gaps in data

---

## Report Generation

**Location**: Sidebar → **Generate Report**

### Creating Reports

1. Navigate to **Generate Report**
2. Select date range:
   - Start Date
   - End Date
3. Choose format:
   - **Excel**: Multi-sheet workbook
   - **PDF**: Professional formatted document
4. Options:
   - Include Inventory Data (checkbox)
5. Click **Generate Report**
6. Download the report

### Excel Report Contents

**Sheets:**
1. **Summary**: Transaction totals by type
2. **Transactions**: Detailed transaction list
3. **Inventory**: Current product stock
4. **Report Info**: Metadata (period, generation date)

**Use Cases:**
- Financial analysis in Excel
- Data manipulation
- Custom charts

### PDF Report Contents

**Sections:**
1. Report header with period
2. Summary table
3. Transaction details (first 20)
4. Inventory listing
5. Page numbers

**Use Cases:**
- Sharing with stakeholders
- Bank submissions
- Investor presentations
- Archival

### Email Reports

1. Check "Send report via email"
2. Enter recipient email address
3. Generate report
4. Report is emailed automatically

**Requirements:**
- Local SMTP server on port 25
- Valid sender email (your registered email)

---

## Admin Features

**Access**: Owner role only

**Location**: Sidebar → **Admin Dashboard**

### System Statistics

**Overview Cards:**
- Total Users
- Total Businesses
- Total Transactions
- Total Products

### User Management Tab

**Features:**
- View all users with statistics
- See business and transaction counts
- Delete users (except yourself)

**Deleting Users:**
1. Find user in list
2. Click **Delete**
3. Confirm deletion
4. User and all their data are removed

### System Health Tab

**Metrics:**
- Daily transaction volume (last 30 days)
- Category completeness percentage
- Top users by transaction count

**Use Cases:**
- Monitor system usage
- Identify data quality issues
- Track active users

### System Settings Tab

**Configurable Options:**
- **Currency Symbol**: Change display currency (₹, $, €, etc.)
- **Default Reorder Level**: Set default for new products

**Applying Settings:**
1. Update values
2. Click **Save Settings**
3. Settings apply immediately

---

## Tips & Best Practices

### Transaction Management

✓ **Use consistent category names**
- "Utilities" not "utilities" or "Utility"
- Create a category list and stick to it

✓ **Add descriptions for large transactions**
- Helps with auditing
- Easier to remember context

✓ **Regular data entry**
- Enter transactions daily
- Reduces errors and omissions

✓ **Backup before bulk imports**
- Test with small CSV first
- Verify data before large imports

### Inventory Management

✓ **Use SKUs consistently**
- Helps prevent duplicates
- Makes tracking easier

✓ **Set realistic reorder levels**
- Based on lead time and sales velocity
- Review and adjust periodically

✓ **Record movements immediately**
- Don't wait until end of day
- Maintains accurate stock levels

✓ **Regular stock audits**
- Use adjustment movements to correct discrepancies
- Compare physical count with system

### Analytics & Forecasting

✓ **Review trends weekly**
- Spot issues early
- Identify opportunities

✓ **Use multiple time periods**
- Daily for recent trends
- Monthly for long-term patterns

✓ **Maintain consistent data entry for forecasting**
- Forecasts need regular data
- Gaps reduce accuracy

✓ **Compare forecasts with actuals**
- Learn from differences
- Adjust business strategies

### Reporting

✓ **Generate reports regularly**
- Monthly for management review
- Quarterly for stakeholders

✓ **Use date ranges strategically**
- Fiscal periods
- Comparison periods (YoY, QoQ)

✓ **Keep report archives**
- Historical reference
- Audit trail

### Security

✓ **Use strong passwords**
- Mix of letters, numbers, symbols
- Change periodically

✓ **Assign appropriate roles**
- Staff: Read-only
- Accountant: Transaction management
- Owner: Full access

✓ **Regular backups**
- Weekly database backups
- Store in secure location

✓ **Log out when done**
- Especially on shared computers
- Protects sensitive data

### Performance

✓ **Archive old data periodically**
- Export to CSV
- Remove from active database

✓ **Limit large imports**
- Break into smaller batches
- Monitor progress

✓ **Use filters and date ranges**
- Don't load all data at once
- Improves responsiveness

---

## Keyboard Shortcuts

While in the application:

- **Ctrl/Cmd + R**: Refresh page
- **Ctrl/Cmd + F**: Find in page
- **Tab**: Navigate between fields
- **Enter**: Submit forms (when in input field)

---

## Common Workflows

### Daily Operations

1. Log in
2. Check Dashboard for overview
3. Add today's transactions
4. Review low stock alerts
5. Record any inventory movements
6. Log out

### Weekly Review

1. View Sales Trends (weekly view)
2. Check Profit Margins
3. Review Expense Categories
4. Generate weekly report
5. Adjust inventory reorder levels if needed

### Monthly Close

1. Generate monthly report (Excel)
2. Review Profit Dashboard
3. Check COGS Analysis
4. Run forecast for next month
5. Archive report
6. Backup databases

### Quarterly Analysis

1. Generate quarterly report (PDF)
2. Review all analytics pages
3. Compare with previous quarter
4. Update forecasts
5. Present to stakeholders

---

## Troubleshooting

### "No active business" warning

**Solution**: Go to Businesses and create or select a business

### Forecast shows "Not enough data"

**Solution**: Add more transactions spread across multiple dates

### Import fails with errors

**Solution**: 
- Check CSV format
- Remove currency symbols
- Ensure Amount column has valid numbers

### Charts not displaying

**Solution**:
- Refresh the page
- Clear browser cache
- Try a different browser

### Can't edit transactions

**Solution**: Check your role (must be Owner or Accountant)

---

## Getting More Help

- Review the [SETUP_GUIDE.md](SETUP_GUIDE.md) for installation issues
- Check [API_REFERENCE.md](API_REFERENCE.md) for technical details
- Examine error messages in the browser console (F12)

---

**Happy analyzing!** Use this guide as a reference while exploring the Business Analyzer application.
