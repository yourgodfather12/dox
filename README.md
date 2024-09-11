# Futuristic Data Management Tool

This is a Python-based data management tool with a sleek, modern GUI. It allows users to add, search, edit, delete, and view records with ease. The tool integrates with an SQLite database and provides import/export functionality using CSV and Excel files.

## Features

- Add, search, and edit records (name, phone, email, username, etc.).
- Delete records with a confirmation dialog.
- Import records from a CSV file and export to Excel.
- Data validation for fields like email, phone number, and password.
- Pagination for viewing large sets of records.
- Auto-save feature to restore draft inputs.
- Dashboard that provides insights into the data (records by city, birth year, etc.).

## Requirements

- Python 3.x
- PyQt5
- SQLAlchemy
- Pandas

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/data-management-tool.git
Install the required Python packages:

bash
Copy code
pip install -r requirements.txt
Run the tool:

bash
Copy code
python main.py
Usage
Add a Record: Fill in the required fields (Name, Phone, Email) and click "Add Record".
Search a Record: Use the search bar to filter records by name, phone, or email.
Edit a Record: Double-click on a record to open the edit dialog.
Delete a Record: Select a record and click "Delete Record" to remove it.
Import/Export: Use the "Import from CSV" and "Export to Excel" buttons to manage your data.
Dashboard: Click "Show Dashboard" to view a breakdown of records by city, birth year, and more.
License
This project is licensed under the MIT License.
