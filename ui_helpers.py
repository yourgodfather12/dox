import tkinter as tk
from tkinter import messagebox, ttk
from spreadsheet_operations import SpreadsheetOperations
import re
import threading

class UIHelpers:
    def __init__(self, root, spreadsheet_operations):
        self.root = root
        self.root.title("Data Management System")
        self.root.geometry("500x500")

        self.spreadsheet_operations = spreadsheet_operations

        # Create a modern style using ttk
        style = ttk.Style()
        style.configure("TLabel", font=("Poppins", 12))
        style.configure("TButton", font=("Poppins", 12))
        style.configure("TEntry", font=("Poppins", 12))

        # Input fields with validation
        self.create_input_fields()

        # Buttons
        self.add_button = ttk.Button(root, text="Add Record", command=lambda: threading.Thread(target=self.add_record).start())
        self.add_button.grid(row=7, column=0, pady=10)

        self.edit_button = ttk.Button(root, text="Edit Record", command=lambda: threading.Thread(target=self.edit_record).start())
        self.edit_button.grid(row=7, column=1, pady=10)

        self.search_button = ttk.Button(root, text="Search Record", command=self.search_record)
        self.search_button.grid(row=8, column=0, pady=10)

        self.clear_button = ttk.Button(root, text="Clear Fields", command=self.clear_fields)
        self.clear_button.grid(row=8, column=1, pady=10)

        # Progress bar for feedback
        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.grid(row=9, columnspan=2, pady=10)

    def create_input_fields(self):
        """Create input fields with labels."""
        self.name_label = ttk.Label(self.root, text="Name")
        self.name_label.grid(row=0, column=0)
        self.name_entry = ttk.Entry(self.root)
        self.name_entry.grid(row=0, column=1)

        self.phone_label = ttk.Label(self.root, text="Phone #")
        self.phone_label.grid(row=1, column=0)
        self.phone_entry = ttk.Entry(self.root)
        self.phone_entry.grid(row=1, column=1)

        self.username_label = ttk.Label(self.root, text="Username")
        self.username_label.grid(row=2, column=0)
        self.username_entry = ttk.Entry(self.root)
        self.username_entry.grid(row=2, column=1)

        self.email_label = ttk.Label(self.root, text="Email")
        self.email_label.grid(row=3, column=0)
        self.email_entry = ttk.Entry(self.root)
        self.email_entry.grid(row=3, column=1)

        self.password_label = ttk.Label(self.root, text="Password")
        self.password_label.grid(row=4, column=0)
        self.password_entry = ttk.Entry(self.root, show="*")
        self.password_entry.grid(row=4, column=1)

        self.birthday_label = ttk.Label(self.root, text="Birthday")
        self.birthday_label.grid(row=5, column=0)
        self.birthday_entry = ttk.Entry(self.root)
        self.birthday_entry.grid(row=5, column=1)

        self.city_label = ttk.Label(self.root, text="City")
        self.city_label.grid(row=6, column=0)
        self.city_entry = ttk.Entry(self.root)
        self.city_entry.grid(row=6, column=1)

    def validate_inputs(self, name, phone, email, password):
        """Validate the input fields before submitting."""
        if not name:
            messagebox.showerror("Validation Error", "Name is required.")
            return False

        phone_pattern = re.compile(r"^\+?[0-9]{10,15}$")
        if not phone_pattern.match(phone):
            messagebox.showerror("Validation Error", "Invalid phone number.")
            return False

        email_pattern = re.compile(r"[^@]+@[^@]+\.[^@]+")
        if not email_pattern.match(email):
            messagebox.showerror("Validation Error", "Invalid email address.")
            return False

        if password and len(password) < 8:
            messagebox.showerror("Validation Error", "Password must be at least 8 characters long.")
            return False

        return True

    def clear_fields(self):
        """Clear all input fields."""
        self.name_entry.delete(0, tk.END)
        self.phone_entry.delete(0, tk.END)
        self.username_entry.delete(0, tk.END)
        self.email_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.birthday_entry.delete(0, tk.END)
        self.city_entry.delete(0, tk.END)

    def add_record(self):
        """Add a new record to the spreadsheet."""
        name = self.name_entry.get()
        phone = self.phone_entry.get()
        username = self.username_entry.get()
        email = self.email_entry.get()
        password = self.password_entry.get()
        birthday = self.birthday_entry.get()
        city = self.city_entry.get()

        if self.validate_inputs(name, phone, email, password):
            self.progress.start(10)  # Start the progress bar
            success = self.spreadsheet_operations.add_record(
                name, phone, username, email, password, birthday, city
            )
            self.progress.stop()  # Stop the progress bar

            if success:
                messagebox.showinfo("Success", f"Record for '{name}' added successfully!")
                self.clear_fields()  # Clear the fields after successful addition
            else:
                messagebox.showwarning("Duplicate", f"Record for '{name}' already exists.")
        else:
            self.progress.stop()  # Stop progress if validation fails

    def edit_record(self):
        """Edit an existing record."""
        name = self.name_entry.get()
        phone = self.phone_entry.get()
        username = self.username_entry.get()
        email = self.email_entry.get()
        password = self.password_entry.get()
        birthday = self.birthday_entry.get()
        city = self.city_entry.get()

        if self.validate_inputs(name, phone, email, password):
            updated_data = {
                'PHONE #': phone,
                'USERNAMES': username,
                'EMAILS': email,
                'PASSWORDS': password,
                'BIRTHDAY': birthday,
                'CITY': city
            }

            self.progress.start(10)  # Start the progress bar
            success = self.spreadsheet_operations.edit_record(name, email, updated_data)
            self.progress.stop()  # Stop the progress bar

            if success:
                messagebox.showinfo("Success", f"Record for '{name}' updated successfully!")
                self.clear_fields()  # Clear the fields after successful editing
            else:
                messagebox.showerror("Error", f"No record found for '{name}' to update.")
        else:
            self.progress.stop()  # Stop progress if validation fails

    def search_record(self):
        """Search for a record by name."""
        name = self.name_entry.get()

        if name:
            record = self.spreadsheet_operations.search_record(name=name)
            if record is not None:
                # Display found record in input fields
                self.name_entry.delete(0, tk.END)
                self.name_entry.insert(0, record.iloc[0]['NAME'])

                self.phone_entry.delete(0, tk.END)
                self.phone_entry.insert(0, record.iloc[0]['PHONE #'])

                self.username_entry.delete(0, tk.END)
                self.username_entry.insert(0, record.iloc[0]['USERNAMES'])

                self.email_entry.delete(0, tk.END)
                self.email_entry.insert(0, record.iloc[0]['EMAILS'])

                self.password_entry.delete(0, tk.END)
                self.password_entry.insert(0, record.iloc[0]['PASSWORDS'])

                self.birthday_entry.delete(0, tk.END)
                self.birthday_entry.insert(0, record.iloc[0]['BIRTHDAY'])

                self.city_entry.delete(0, tk.END)
                self.city_entry.insert(0, record.iloc[0]['CITY'])
            else:
                messagebox.showwarning("Not Found", f"No record found for '{name}'.")
        else:
            messagebox.showerror("Error", "Name is required for search.")


if __name__ == "__main__":
    spreadsheet_operations = SpreadsheetOperations("data.csv")
    root = tk.Tk()
    ui = UIHelpers(root, spreadsheet_operations)
    root.mainloop()
