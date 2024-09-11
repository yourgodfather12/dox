import pandas as pd
import os
import hashlib
import logging
import re
import json
import threading
from datetime import datetime
from shutil import copyfile
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SpreadsheetOperations:
    def __init__(self, file_path, encryption_algorithm='sha256'):
        self.file_path = file_path
        self.encryption_algorithm = encryption_algorithm
        self.backup_file_path = f"{file_path}.backup"
        self.original_file_hash = None
        
        # Load or initialize CSV data
        self.load_or_initialize()

    def load_or_initialize(self):
        """Load the data from the file, or initialize a new DataFrame if the file doesn't exist."""
        if not os.path.exists(self.file_path):
            logging.info(f"File '{self.file_path}' not found. Initializing new spreadsheet.")
            self.data = pd.DataFrame(columns=['NAME', 'PHONE #', 'USERNAMES', 'EMAILS', 'PASSWORDS', 'BIRTHDAY', 'CITY'])
            self.save_data()
        else:
            self.data = pd.read_csv(self.file_path)
            self.original_file_hash = self.calculate_file_hash()

    def calculate_file_hash(self):
        """Calculate and return the SHA-256 hash of the file for change detection."""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'rb') as file:
                file_content = file.read()
                return hashlib.sha256(file_content).hexdigest()
        return None

    def create_backup(self):
        """Create a backup of the spreadsheet file."""
        try:
            copyfile(self.file_path, self.backup_file_path)
            logging.info(f"Backup created at '{self.backup_file_path}'.")
        except Exception as e:
            logging.error(f"Failed to create backup: {e}")

    def restore_backup(self):
        """Restore the spreadsheet from the backup."""
        if os.path.exists(self.backup_file_path):
            try:
                copyfile(self.backup_file_path, self.file_path)
                logging.info(f"Spreadsheet restored from backup.")
            except Exception as e:
                logging.error(f"Failed to restore backup: {e}")

    def save_data(self, threaded=False):
        """Save the current DataFrame back to the CSV file if there are any changes."""
        def save():
            current_hash = self.calculate_file_hash()
            if current_hash == self.original_file_hash:
                logging.info("No changes detected. Skipping save.")
                return

            try:
                self.create_backup()
                self.data.to_csv(self.file_path, index=False)
                self.original_file_hash = self.calculate_file_hash()  # Update file hash after saving
                logging.info("Data saved successfully.")
            except Exception as e:
                logging.error(f"Failed to save data to '{self.file_path}': {e}")
                self.restore_backup()

        if threaded:
            save_thread = threading.Thread(target=save)
            save_thread.start()
            save_thread.join()  # Ensure the thread finishes before returning
        else:
            save()

    def encrypt_password(self, password):
        """Encrypt the password using the configured encryption algorithm (default is SHA-256)."""
        if not password:
            return ""
        try:
            hasher = getattr(hashlib, self.encryption_algorithm)
            return hasher(password.encode()).hexdigest()
        except AttributeError:
            logging.error(f"Unsupported encryption algorithm '{self.encryption_algorithm}'")
            return ""

    def validate_fields(self, name, phone, email, password):
        """Validate fields before adding or updating a record."""
        name = str(name).strip()
        phone = str(phone).strip()
        email = str(email).strip()

        if pd.isna(name) or pd.isna(phone) or pd.isna(email):
            logging.warning("Name, Phone, and Email are required fields.")
            return False

        if not phone.isdigit():
            logging.warning("Phone number should be numeric.")
            return False

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            logging.warning("Invalid email format.")
            return False

        if password and len(password) < 6:
            logging.warning("Password should be at least 6 characters long.")
            return False

        return True

    def add_record(self, name, phone, username, email, password, birthday, city, threaded=False):
        """Add a new record to the spreadsheet."""
        if not self.validate_fields(name, phone, email, password):
            return False

        if self.record_exists(name, email):
            logging.warning(f"Record with name '{name}' or email '{email}' already exists. Skipping addition.")
            return False

        encrypted_password = self.encrypt_password(password)
        new_record = pd.DataFrame([{
            'NAME': name,
            'PHONE #': phone,
            'USERNAMES': username or "",
            'EMAILS': email,
            'PASSWORDS': encrypted_password,
            'BIRTHDAY': birthday or "",
            'CITY': city or ""
        }])
        
        self.data = pd.concat([self.data, new_record], ignore_index=True)
        self.save_data(threaded=threaded)
        logging.info(f"Record for '{name}' added successfully.")
        return True

    def record_exists(self, name, email):
        """Check if a record with the given name or email already exists."""
        return not self.data[(self.data['NAME'] == name) | (self.data['EMAILS'] == email)].empty

    def edit_record(self, name, email, updated_data, threaded=False):
        """Edit an existing record."""
        if not self.record_exists(name, email):
            logging.warning(f"No record found for '{name}' or '{email}'. Cannot update.")
            return False

        # Encrypt password if being updated
        if 'PASSWORDS' in updated_data and updated_data['PASSWORDS']:
            updated_data['PASSWORDS'] = self.encrypt_password(updated_data['PASSWORDS'])

        for column, value in updated_data.items():
            if column in self.data.columns and value is not None:
                self.data.loc[(self.data['NAME'] == name) & (self.data['EMAILS'] == email), column] = value

        self.save_data(threaded=threaded)
        logging.info(f"Record for '{name}' updated successfully.")
        return True

    def search_record(self, name=None, email=None, city=None, birthday_range=None):
        """Search for a record by name, email, city, or birthday range."""
        query = self.data
        if name:
            query = query[query['NAME'] == name]
        if email:
            query = query[query['EMAILS'] == email]
        if city:
            query = query[query['CITY'] == city]
        if birthday_range:
            start_date, end_date = birthday_range
            query = query[(query['BIRTHDAY'] >= start_date) & (query['BIRTHDAY'] <= end_date)]

        if not query.empty:
            logging.info(f"Records found matching the search criteria.")
            return query
        else:
            logging.warning("No records found matching the search criteria.")
            return None

    def delete_record(self, name, email, threaded=False):
        """Delete a record from the spreadsheet."""
        if not self.record_exists(name, email):
            logging.warning(f"No record found for '{name}' or '{email}'. Cannot delete.")
            return False

        self.data = self.data[~((self.data['NAME'] == name) & (self.data['EMAILS'] == email))]
        self.save_data(threaded=threaded)
        logging.info(f"Record for '{name}' deleted successfully.")
        return True

    def batch_insert(self, records, threaded=False):
        """Batch insert multiple records."""
        # Add validation for each record
        valid_records = []
        for record in records:
            if self.validate_fields(record.get('NAME'), record.get('PHONE #'), record.get('EMAILS'), record.get('PASSWORDS')):
                record['PASSWORDS'] = self.encrypt_password(record['PASSWORDS'])
                valid_records.append(record)

        if not valid_records:
            logging.warning("No valid records to insert.")
            return False

        new_records = pd.DataFrame(valid_records)
        self.data = pd.concat([self.data, new_records], ignore_index=True)
        self.save_data(threaded=threaded)
        logging.info(f"Batch insertion of {len(valid_records)} records completed successfully.")
        return True

    def export_data(self, file_type='csv'):
        """Export data to the specified file type (csv, excel, or json)."""
        try:
            if file_type == 'csv':
                self.data.to_csv(self.file_path, index=False)
            elif file_type == 'excel':
                self.data.to_excel(self.file_path.replace(".csv", ".xlsx"), index=False)
            elif file_type == 'json':
                self.data.to_json(self.file_path.replace(".csv", ".json"), orient='records')
            else:
                logging.error(f"Unsupported file type '{file_type}' for export.")
                return False
            logging.info(f"Data exported successfully to {file_type}.")
            return True
        except Exception as e:
            logging.error(f"Failed to export data: {e}")
            return False

    def import_data(self, file_path, file_type='csv'):
        """Import data from a file (csv, excel, or json)."""
        try:
            if file_type == 'csv':
                imported_data = pd.read_csv(file_path)
            elif file_type == 'excel':
                imported_data = pd.read_excel(file_path)
            elif file_type == 'json':
                imported_data = pd.read_json(file_path)
            else:
                logging.error(f"Unsupported file type '{file_type}' for import.")
                return False

            self.data = pd.concat([self.data, imported_data], ignore_index=True)
            self.save_data()
            logging.info(f"Data imported successfully from {file_path}.")
            return True
        except Exception as e:
            logging.error(f"Failed to import data from '{file_path}': {e}")
            return False
