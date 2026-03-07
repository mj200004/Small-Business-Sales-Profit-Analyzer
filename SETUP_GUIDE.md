# Business Analyzer - Complete Setup Guide

This guide will walk you through setting up the Business Analyzer application from scratch.

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10/11, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Python**: Version 3.8 or higher
- **RAM**: 2GB minimum (4GB recommended)
- **Disk Space**: 500MB free space
- **Browser**: Modern web browser (Chrome, Firefox, Safari, Edge)

### Recommended Requirements
- **Python**: Version 3.10 or higher
- **RAM**: 4GB or more
- **Internet**: For initial package installation

## Step-by-Step Installation

### 1. Install Python

#### Windows
1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run the installer
3. **Important**: Check "Add Python to PATH" during installation
4. Verify installation:
```bash
python --version
```

#### macOS
```bash
# Using Homebrew
brew install python3

# Verify
python3 --version
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3 python3-pip

# Verify
python3 --version
```

### 2. Download the Application

Extract the project files to a directory of your choice, for example:
- Windows: `C:\BusinessAnalyzer`
- macOS/Linux: `~/BusinessAnalyzer`

### 3. Install Dependencies

Open a terminal/command prompt in the project directory and run:

```bash
# Navigate to project directory
cd path/to/BusinessAnalyzer

# Install all required packages
pip install -r requirements.txt
```

#### If Prophet Installation Fails

Prophet can be tricky to install. Try these alternatives:

**Option 1: Install with conda**
```bash
conda install -c conda-forge prophet
```

**Option 2: Use the app without Prophet**
The application will automatically fall back to linear regression forecasting if Prophet is not available.

### 4. Verify Installation

Check that all packages are installed:

```bash
pip list
```

You should see packages like:
- streamlit
- pandas
- plotly
- bcrypt
- pyjwt
- scikit-learn
- openpyxl
- fpdf2

### 5. Initialize Databases

The application will automatically create the required databases on first run. However, you can verify they exist:

```bash
# Run the app once to create databases
streamlit run streamlit_app.py
```

This will create:
- `USER.db` - User authentication database
- `BUSINESS.db` - Business data database

### 6. Configure Application (Optional)

#### Change Default Port

If port 8501 is already in use:

```bash
streamlit run streamlit_app.py --server.port 8502
```

#### Set JWT Secret Key

For production, set a secure JWT secret:

**Windows:**
```bash
set JWT_SECRET_KEY=your-very-secure-random-key-here
streamlit run streamlit_app.py
```

**macOS/Linux:**
```bash
export JWT_SECRET_KEY=your-very-secure-random-key-here
streamlit run streamlit_app.py
```

#### Configure Email (Optional)

For email report delivery, you need a local SMTP server:

**Windows:**
- Install [hMailServer](https://www.hmailserver.com/) or similar
- Configure to listen on localhost:25

**Linux:**
```bash
sudo apt install postfix
sudo systemctl start postfix
```

**macOS:**
```bash
sudo postfix start
```

## First Run

### 1. Start the Application

```bash
streamlit run streamlit_app.py
```

You should see output like:
```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://192.168.1.x:8501
```

### 2. Access the Application

Open your browser and navigate to `http://localhost:8501`

### 3. Create Your First Account

1. Click "Sign Up"
2. Enter:
   - Username (unique)
   - Email address
   - Password (minimum 6 characters recommended)
   - Confirm password
   - Select role: "Owner" for full access
3. Click "Sign Up"

### 4. Login

1. Click "Login"
2. Enter your username and password
3. Click "Login"

### 5. Create Your First Business

1. Navigate to "Businesses" in the sidebar
2. Click "Add New Business"
3. Fill in:
   - Business Name (required)
   - Business Type (optional)
   - Address (optional)
   - Phone (optional)
4. Click "Create"

Your first business will automatically be set as active.

### 6. Add Your First Transaction

1. Click "Add Tx" in the sidebar
2. Select Type: "Sales" or "Expense"
3. Enter Amount
4. Add Category (e.g., "Electronics", "Utilities")
5. Add Description (optional)
6. Select Date
7. Click "Add"

## Testing the Application

### Test Data Import

Create a test CSV file (`test_data.csv`):

```csv
Amount,Type,Category,Description
1500.00,Sales,Electronics,Laptop sale
2500.00,Sales,Electronics,Desktop sale
250.50,Expense,Utilities,Electricity bill
180.00,Expense,Supplies,Office supplies
3200.00,Sales,Services,Consulting service
```

Import steps:
1. Go to "Import" in sidebar
2. Upload `test_data.csv`
3. Map columns (Amount → Amount, Type → Type, etc.)
4. Click "IMPORT"

### Test Inventory Management

1. Go to "Inventory" in sidebar
2. Click "Add Product" tab
3. Add a test product:
   - Product Name: "Test Laptop"
   - SKU: "LAP001"
   - Initial Quantity: 10
   - Cost Price: 800
   - Selling Price: 1200
   - Reorder Level: 5
   - Category: Electronics
4. Click "Add Product"

### Test Analytics

1. Navigate to "Trends" to view sales trends
2. Check "Forecast" for AI predictions (requires 3+ data points)
3. View "Profit Dashboard" for financial metrics

### Test Report Generation

1. Go to "Generate Report"
2. Select date range
3. Choose format (Excel or PDF)
4. Click "Generate Report"
5. Download the report

## Common Issues and Solutions

### Issue: "ModuleNotFoundError"
**Solution**: Reinstall requirements
```bash
pip install -r requirements.txt --force-reinstall
```

### Issue: "Database is locked"
**Solution**: Close all instances of the app and restart
```bash
# Kill all streamlit processes
pkill -f streamlit
# Restart
streamlit run streamlit_app.py
```

### Issue: "Port 8501 already in use"
**Solution**: Use a different port
```bash
streamlit run streamlit_app.py --server.port 8502
```

### Issue: Prophet installation fails
**Solution**: The app works without Prophet using linear regression fallback. To install Prophet:
```bash
# Try with conda
conda install -c conda-forge prophet

# Or use pip with specific version
pip install prophet==1.1.1
```

### Issue: Charts not displaying
**Solution**: Clear browser cache or try a different browser

### Issue: CSV import fails
**Solution**: 
- Ensure CSV is UTF-8 encoded
- Check that Amount column contains valid numbers
- Remove any currency symbols from the CSV

## Performance Tuning

### For Large Datasets (10,000+ transactions)

1. **Increase memory limit:**
```bash
streamlit run streamlit_app.py --server.maxUploadSize 200
```

2. **Use database indexing:**
The app automatically creates indexes, but you can verify:
```bash
sqlite3 BUSINESS.db
.schema transactions
```

3. **Limit data display:**
Modify queries to use LIMIT clauses for initial views

### For Multiple Users

Consider deploying with:
- **Streamlit Cloud**: Free hosting for public apps
- **Docker**: Containerized deployment
- **Cloud VPS**: AWS, DigitalOcean, etc.

## Backup and Maintenance

### Backup Databases

**Windows:**
```bash
copy USER.db USER_backup_%date%.db
copy BUSINESS.db BUSINESS_backup_%date%.db
```

**macOS/Linux:**
```bash
cp USER.db USER_backup_$(date +%Y%m%d).db
cp BUSINESS.db BUSINESS_backup_$(date +%Y%m%d).db
```

### Automated Backup Script

Create `backup.sh` (Linux/macOS):
```bash
#!/bin/bash
BACKUP_DIR="./backups"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
cp USER.db "$BACKUP_DIR/USER_$DATE.db"
cp BUSINESS.db "$BACKUP_DIR/BUSINESS_$DATE.db"
echo "Backup completed: $DATE"
```

Make executable and run:
```bash
chmod +x backup.sh
./backup.sh
```

### Database Maintenance

Periodically optimize databases:
```bash
sqlite3 USER.db "VACUUM;"
sqlite3 BUSINESS.db "VACUUM;"
```

## Upgrading

To upgrade to a new version:

1. Backup your databases
2. Download new version files
3. Replace `streamlit_app.py` and other Python files
4. Update dependencies:
```bash
pip install -r requirements.txt --upgrade
```
5. Restart the application

## Security Recommendations

1. **Change JWT Secret**: Set a strong, random JWT_SECRET_KEY environment variable
2. **Use HTTPS**: Deploy behind a reverse proxy with SSL/TLS
3. **Regular Backups**: Automate database backups
4. **Update Dependencies**: Keep packages up to date
5. **Strong Passwords**: Enforce password policies for users
6. **Access Control**: Use appropriate user roles

## Getting Help

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review error messages in the terminal
3. Check Streamlit logs: `~/.streamlit/logs/`
4. Verify all dependencies are installed correctly
5. Try with a fresh database (backup first!)

## Next Steps

After successful setup:

1. Read the [USER_GUIDE.md](USER_GUIDE.md) for detailed feature documentation
2. Review [API_REFERENCE.md](API_REFERENCE.md) for technical details
3. Explore the application features systematically
4. Import your actual business data
5. Set up regular backup procedures

---

**Setup Complete!** 
