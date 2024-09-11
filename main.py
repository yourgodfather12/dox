import logging
import os
import sys
import re
import pandas as pd
import asyncio
from collections import Counter
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QMainWindow, QLineEdit, QPushButton, QLabel, QStatusBar, QTableWidget, \
    QTableWidgetItem, QFileDialog, QHeaderView, QAbstractItemView, QProgressBar, QDialog, QMessageBox, \
    QVBoxLayout, QHBoxLayout, QWidget, QGridLayout, QGroupBox

from sqlalchemy.exc import IntegrityError
from database import Record, add_record, get_all_records, update_record, search_records, delete_record


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Futuristic Data Management Tool")
        self.setGeometry(100, 100, 1200, 700)

        # Load the stylesheet from 'assets/css/'
        self.load_stylesheet()

        self.initUI()
        self.autosave_draft()  # Automatically restore drafts if available

        self.page_size = 10  # Number of records per page
        self.current_page = 0  # Track current page

    def load_stylesheet(self):
        """
        Load the 'red_black_silver.qss' stylesheet from the 'assets/css/' directory.
        """
        qss_path = os.path.join(os.path.dirname(__file__), "assets", "css", "red_black_silver.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r") as file:
                self.setStyleSheet(file.read())
        else:
            QMessageBox.warning(self, "File Not Found",
                                "Stylesheet 'red_black_silver.qss' not found. Proceeding without it.")
            print("Stylesheet not found. Proceeding without it.")

    def initUI(self):
        self.font = QFont("Poppins", 12)
        self.setFont(self.font)

        # Main layout
        main_layout = QVBoxLayout()

        # Title
        title_label = QLabel("Add or Search Records")
        title_label.setFont(QFont("Poppins", 20, QFont.Bold))
        main_layout.addWidget(title_label)

        # Input Fields Layout
        self.create_input_fields(main_layout)

        # Buttons Layout
        self.create_buttons(main_layout)

        # Table for Records
        self.create_table(main_layout)

        # Pagination and Search
        self.create_pagination_and_search(main_layout)

        # Progress Bar for import/export processes
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Status Bar
        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)

        # Set the central widget and main layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def create_input_fields(self, layout):
        input_group = QGroupBox("Input Fields")
        grid_layout = QGridLayout()

        self.name_input = self.create_input("Enter Name")
        self.phone_input = self.create_input("Enter Phone")
        self.email_input = self.create_input("Enter Email")
        self.username_input = self.create_input("Enter Username")
        self.password_input = self.create_input("Enter Password", echo=True)
        self.birthday_input = self.create_input("Enter Birthday (YYYY-MM-DD)")
        self.city_input = self.create_input("Enter City")

        # Add widgets to grid
        grid_layout.addWidget(QLabel("Name"), 0, 0)
        grid_layout.addWidget(self.name_input, 0, 1)

        grid_layout.addWidget(QLabel("Phone"), 0, 2)
        grid_layout.addWidget(self.phone_input, 0, 3)

        grid_layout.addWidget(QLabel("Email"), 1, 0)
        grid_layout.addWidget(self.email_input, 1, 1)

        grid_layout.addWidget(QLabel("Username"), 1, 2)
        grid_layout.addWidget(self.username_input, 1, 3)

        grid_layout.addWidget(QLabel("Password"), 2, 0)
        grid_layout.addWidget(self.password_input, 2, 1)

        grid_layout.addWidget(QLabel("Birthday"), 2, 2)
        grid_layout.addWidget(self.birthday_input, 2, 3)

        grid_layout.addWidget(QLabel("City"), 3, 0)
        grid_layout.addWidget(self.city_input, 3, 1)

        input_group.setLayout(grid_layout)
        layout.addWidget(input_group)

    def create_input(self, placeholder, echo=False):
        input_field = QLineEdit(self)
        input_field.setPlaceholderText(placeholder)
        input_field.setFont(QFont("Poppins", 14))
        if echo:
            input_field.setEchoMode(QLineEdit.Password)  # Password field for secure input
        return input_field

    def create_buttons(self, layout):
        button_layout = QHBoxLayout()

        self.add_button = self.create_button("Add Record", self.add_record)
        self.search_button = self.create_button("Search Record", self.search_record)
        self.dashboard_button = self.create_button("Show Dashboard", self.show_dashboard)
        self.clear_button = self.create_button("Clear Form", self.clear_inputs)
        self.view_button = self.create_button("View All Records", self.update_records_table)
        self.export_button = self.create_button("Export to Excel", self.export_to_excel)
        self.import_button = self.create_button("Import from CSV", self.import_from_csv)
        self.delete_button = self.create_button("Delete Record", self.delete_record)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.search_button)
        button_layout.addWidget(self.dashboard_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.view_button)
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)

    def create_button(self, text, callback):
        button = QPushButton(text, self)
        button.setFont(QFont("Poppins", 14))
        button.clicked.connect(callback)
        return button

    def create_table(self, layout):
        self.records_table = QTableWidget(self)
        self.records_table.setColumnCount(7)
        self.records_table.setHorizontalHeaderLabels(
            ['Name', 'Phone', 'Email', 'Username', 'Password', 'Birthday', 'City'])
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.records_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.records_table.doubleClicked.connect(self.open_edit_dialog)

        layout.addWidget(self.records_table)

    def create_pagination_and_search(self, layout):
        pagination_layout = QHBoxLayout()

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search records...")
        self.search_input.setFont(QFont("Poppins", 14))
        self.search_input.textChanged.connect(self.filter_records)

        self.previous_button = self.create_button("Previous", self.previous_page)
        self.next_button = self.create_button("Next", self.next_page)

        pagination_layout.addWidget(self.search_input)
        pagination_layout.addWidget(self.previous_button)
        pagination_layout.addWidget(self.next_button)

        layout.addLayout(pagination_layout)

    def show_dashboard(self):
        records = asyncio.run(get_all_records())

        if not records:
            QMessageBox.information(self, "Dashboard", "No records available to display.")
            return

        # Total number of records
        total_records = len(records)

        # Count records by city
        cities = [record.city for record in records if record.city]
        city_count = Counter(cities)

        # Count records by birth year (assuming 'birthday' is stored as YYYY-MM-DD)
        birthdays = [record.birthday for record in records if record.birthday]
        years = [bd.split("-")[0] for bd in birthdays if len(bd) >= 4]  # Extract only the year
        year_count = Counter(years)

        # Count records by phone, email, and username (to identify duplicates)
        phones = [record.phone for record in records if record.phone]
        emails = [record.email for record in records if record.email]
        usernames = [record.username for record in records if record.username]

        phone_count = Counter(phones)
        email_count = Counter(emails)
        username_count = Counter(usernames)

        # Format the dashboard information
        dashboard_info = f"Total Records: {total_records}\n\n"

        dashboard_info += "Records by City:\n"
        for city, count in city_count.items():
            dashboard_info += f"  {city}: {count}\n"

        dashboard_info += "\nRecords by Birth Year:\n"
        for year, count in year_count.items():
            dashboard_info += f"  {year}: {count}\n"

        dashboard_info += "\nRecords by Phone (duplicates):\n"
        for phone, count in phone_count.items():
            dashboard_info += f"  {phone}: {count}\n"

        dashboard_info += "\nRecords by Email (duplicates):\n"
        for email, count in email_count.items():
            dashboard_info += f"  {email}: {count}\n"

        dashboard_info += "\nRecords by Username (duplicates):\n"
        for username, count in username_count.items():
            dashboard_info += f"  {username}: {count}\n"

        # Show dashboard information in a message box
        QMessageBox.information(self, "Dashboard", dashboard_info)

    def add_record(self):
        name = self.name_input.text()
        phone = self.phone_input.text()
        email = self.email_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        birthday = self.birthday_input.text()
        city = self.city_input.text()

        # Validate required fields
        if not name or not phone or not email:
            QMessageBox.warning(self, "Validation Error", "Name, Phone, and Email are required.")
            return

        # Additional validation for numeric phone
        if not phone.isdigit():
            QMessageBox.warning(self, "Validation Error", "Phone number should be numeric.")
            return

        # Additional validation for valid email format
        if not self.is_valid_email(email):
            QMessageBox.warning(self, "Validation Error", "Please enter a valid email address.")
            return

        # Check for duplicates before adding
        existing_records = asyncio.run(search_records(f"{name} {phone} {email}"))
        if existing_records:
            QMessageBox.warning(self, "Duplicate Entry", "A record with similar details already exists.")
            return

        # Create a Record object and add to the database
        record = {
            'name': name,
            'phone': phone,
            'email': email,
            'username': username,
            'password': password,
            'birthday': birthday,
            'city': city
        }

        try:
            asyncio.run(add_record(record))
            self.statusBar.showMessage(f"Record for {name} added successfully.", 5000)
            self.clear_inputs()
            self.update_records_table()
        except IntegrityError as e:
            self.statusBar.showMessage(f"Error adding record: {str(e)}", 5000)
            print(f"IntegrityError: {e}")

    def search_record(self):
        search_term = self.search_input.text().lower()
        filtered_records = []

        records = asyncio.run(get_all_records())  # Fetch all records asynchronously
        for record in records:
            if (search_term in record.name.lower() or
                    search_term in record.phone.lower() or
                    search_term in record.email.lower()):
                filtered_records.append(record)

        # Update the table with the filtered records
        self.records_table.setRowCount(len(filtered_records))
        for i, record in enumerate(filtered_records):
            self.records_table.setItem(i, 0, QTableWidgetItem(record.name))
            self.records_table.setItem(i, 1, QTableWidgetItem(record.phone))
            self.records_table.setItem(i, 2, QTableWidgetItem(record.email))
            self.records_table.setItem(i, 3, QTableWidgetItem(record.username))
            self.records_table.setItem(i, 4, QTableWidgetItem(record.password))
            self.records_table.setItem(i, 5, QTableWidgetItem(record.birthday))
            self.records_table.setItem(i, 6, QTableWidgetItem(record.city))

    def delete_record(self):
        """
        Deletes the selected record from the database and the table.
        """
        row = self.records_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection Error", "Please select a record to delete.")
            return

        name = self.records_table.item(row, 0).text()  # Assuming name is a unique identifier
        phone = self.records_table.item(row, 1).text()
        email = self.records_table.item(row, 2).text()

        confirm = QMessageBox.question(self, 'Delete Confirmation',
                                       f"Are you sure you want to delete the record for {name}?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                asyncio.run(delete_record(name, phone, email))
                self.records_table.removeRow(row)
                self.statusBar.showMessage(f"Record for {name} deleted successfully.", 5000)
            except Exception as e:
                self.statusBar.showMessage(f"Error deleting record: {str(e)}", 5000)
        else:
            self.statusBar.showMessage(f"Deletion of {name} cancelled.", 5000)

    def clear_inputs(self):
        for input_field in [self.name_input, self.phone_input, self.email_input, self.username_input,
                            self.password_input, self.birthday_input, self.city_input]:
            input_field.clear()
        self.statusBar.showMessage("Form cleared.", 2000)

    def open_edit_dialog(self):
        row = self.records_table.currentRow()
        if row >= 0:
            dialog = EditDialog(self, row, self.records_table)
            dialog.exec_()

    def export_to_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export to Excel", "", "Excel Files (*.xlsx)")
        if file_path:
            records = asyncio.run(get_all_records())
            df = pd.DataFrame([vars(record) for record in records])
            df.to_excel(file_path, index=False)
            self.statusBar.showMessage(f"Data exported to {file_path}", 5000)

    def import_from_csv(self):
        """
        Import records from a CSV file, handling column name variations and normalizing them.
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Import from CSV", "", "CSV Files (*.csv)")
        if file_path:
            column_mapping = {
                'NAME': 'Name',
                'PHONE #': 'Phone',
                'USERNAMES': 'Username',
                'EMAILS': 'Email',
                'PASSWORDS': 'Password',
                'BIRTHDAY': 'Birthday',
                'CITY': 'City'
            }

            chunk_size = 1000  # Number of rows to process in each chunk
            total_rows = sum(1 for _ in open(file_path)) - 1  # Subtract 1 for header
            self.progress_bar.setValue(0)

            try:
                for chunk in pd.read_csv(file_path, chunksize=chunk_size):
                    chunk.rename(columns=column_mapping, inplace=True)

                    required_columns = ['Name', 'Phone', 'Email', 'Username', 'Password', 'Birthday', 'City']
                    missing_columns = [col for col in required_columns if col not in chunk.columns]

                    if missing_columns:
                        QMessageBox.critical(self, "Missing Columns",
                                             f"The following required columns are missing: {', '.join(missing_columns)}")
                        return

                    for i, row in chunk.iterrows():
                        existing_records = asyncio.run(search_records(f"{row['Name']} {row['Phone']} {row['Email']}"))
                        if existing_records:
                            continue  # Skip adding if the record already exists

                        record = Record(
                            name=row['Name'],
                            phone=row['Phone'],
                            email=row['Email'],
                            username=row['Username'],
                            password=row['Password'],
                            birthday=row['Birthday'],
                            city=row['City']
                        )
                        asyncio.run(add_record(record))

                    current_rows = min(chunk_size, len(chunk))
                    self.progress_bar.setValue(
                        min(100, (self.progress_bar.value() + (current_rows / total_rows) * 100))
                    )

                self.statusBar.showMessage(f"Data imported from {file_path}", 5000)
                self.update_records_table()
            except Exception as e:
                self.statusBar.showMessage(f"Error importing data: {str(e)}", 5000)
                logging.error(f"Error importing data: {str(e)}")

    async def view_records(self):
        # Await the asynchronous function to fetch records
        records = await get_all_records()

        paginated_records = records[self.current_page * self.page_size: (self.current_page + 1) * self.page_size]
        self.records_table.setRowCount(len(paginated_records))
        for i, record in enumerate(paginated_records):
            self.records_table.setItem(i, 0, QTableWidgetItem(record.name))
            self.records_table.setItem(i, 1, QTableWidgetItem(record.phone))
            self.records_table.setItem(i, 2, QTableWidgetItem(record.email))
            self.records_table.setItem(i, 3, QTableWidgetItem(record.username))
            self.records_table.setItem(i, 4, QTableWidgetItem(record.password))  # Show plaintext password
            self.records_table.setItem(i, 5, QTableWidgetItem(record.birthday))
            self.records_table.setItem(i, 6, QTableWidgetItem(record.city))

    def update_records_table(self):
        """
        Wraps the async call to `view_records` and runs it in the event loop.
        """
        asyncio.run(self.view_records())  # Use asyncio.run to handle the async method in PyQt

    def previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_records_table()

    def next_page(self):
        if len(asyncio.run(get_all_records())) > (self.current_page + 1) * self.page_size:
            self.current_page += 1
            self.update_records_table()

    def filter_records(self, text):
        for i in range(self.records_table.rowCount()):
            match = False
            for j in range(self.records_table.columnCount()):
                if text.lower() in self.records_table.item(i, j).text().lower():
                    match = True
            self.records_table.setRowHidden(i, not match)

    def autosave_draft(self):
        try:
            with open("draft.txt", "r") as file:
                data = file.readlines()
                if len(data) == 7:
                    self.name_input.setText(data[0].strip())
                    self.phone_input.setText(data[1].strip())
                    self.email_input.setText(data[2].strip())
                    self.username_input.setText(data[3].strip())
                    self.password_input.setText(data[4].strip())
                    self.birthday_input.setText(data[5].strip())
                    self.city_input.setText(data[6].strip())
        except FileNotFoundError:
            pass

    def save_draft(self):
        with open("draft.txt", "w") as file:
            file.writelines([
                self.name_input.text() + '\n',
                self.phone_input.text() + '\n',
                self.email_input.text() + '\n',
                self.username_input.text() + '\n',
                self.password_input.text() + '\n',
                self.birthday_input.text() + '\n',
                self.city_input.text() + '\n',
            ])

    def is_valid_email(self, email):
        return re.match(r"[^@]+@[^@]+\.[^@]+", email)


class EditDialog(QDialog):
    def __init__(self, parent=None, row=None, table=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Record")
        self.setGeometry(300, 150, 400, 300)
        self.setModal(True)

        self.row = row
        self.table = table

        # Inputs to edit
        self.name_input = QLineEdit(self)
        self.name_input.setText(table.item(row, 0).text())
        self.name_input.setGeometry(20, 50, 200, 40)

        # Add fields for phone, email, etc.
        self.phone_input = QLineEdit(self)
        self.phone_input.setText(table.item(row, 1).text())
        self.phone_input.setGeometry(20, 100, 200, 40)

        self.email_input = QLineEdit(self)
        self.email_input.setText(table.item(row, 2).text())
        self.email_input.setGeometry(20, 150, 200, 40)

        self.password_input = QLineEdit(self)
        self.password_input.setText(table.item(row, 4).text())  # Show plaintext password
        self.password_input.setGeometry(20, 200, 200, 40)

        self.submit_button = QPushButton("Submit", self)
        self.submit_button.setGeometry(150, 250, 100, 40)
        self.submit_button.clicked.connect(self.submit_changes)

    def submit_changes(self):
        # Update the table
        self.table.setItem(self.row, 0, QTableWidgetItem(self.name_input.text()))
        self.table.setItem(self.row, 1, QTableWidgetItem(self.phone_input.text()))
        self.table.setItem(self.row, 2, QTableWidgetItem(self.email_input.text()))
        self.table.setItem(self.row, 4, QTableWidgetItem(self.password_input.text()))  # Update plaintext password

        # Save changes to database
        record_id = self.row + 1  # Assuming row index matches record ID
        updated_data = {
            'name': self.name_input.text(),
            'phone': self.phone_input.text(),
            'email': self.email_input.text(),
            'password': self.password_input.text()
        }
        asyncio.run(update_record(record_id, updated_data))

        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    app.aboutToQuit.connect(window.save_draft)  # Autosave on app exit
    window.show()
    sys.exit(app.exec_())
