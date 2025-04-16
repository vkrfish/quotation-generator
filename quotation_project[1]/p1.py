import os
import smtplib
import mysql.connector
from dotenv import load_dotenv
from pydantic import BaseModel
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF

# Load environment variables
if os.path.exists(".env"):
    load_dotenv()
else:
    print("Warning: .env file not found. Using default values if set.")

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "Vasanth@10906"),
    "database": os.getenv("DB_NAME", "MySQL"),
}
try:
    print("🔄 Connecting to database...")
    connection = mysql.connector.connect(**DB_CONFIG)

    if connection.is_connected():
        print("✅ Connected to database successfully!")
        cursor = connection.cursor()
        cursor.execute("SHOW DATABASES;")  # Check available databases
        for db in cursor.fetchall():
            print(f"📌 Found database: {db[0]}")  # Print available databases

    connection.close()

except mysql.connector.Error as e:
    print("❌ Database Connection Error:", e)

# Email Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "your_email@example.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "your_password")


# Define Quotation Structure
class QuotationResponse(BaseModel):
    customer_name: str
    email: str
    phone: str
    t_shirt_type: str
    quantity: int
    price_per_unit: float
    total_price: float
    estimated_delivery: str


def save_to_database(quotation):
    try:
        print("🔄 Attempting to connect to MySQL database...")  # Debug message
        connection = mysql.connector.connect(**DB_CONFIG)

        if connection.is_connected():
            print("✅ Successfully connected to the database!")

        cursor = connection.cursor()
        cursor.execute("SHOW TABLES LIKE 'quotations'")
        result = cursor.fetchone()

        if not result:
            print("❌ Table 'quotations' does not exist!")
            return None

        query = """
        INSERT INTO quotations (customer_name, email, phone, t_shirt_type, quantity, price_per_unit, total_price, estimated_delivery)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            quotation.customer_name,
            quotation.email,
            quotation.phone,
            quotation.t_shirt_type,
            quotation.quantity,
            quotation.price_per_unit,
            quotation.total_price,
            quotation.estimated_delivery,
        )

        cursor.execute(query, values)
        connection.commit()
        quotation_id = cursor.lastrowid
        print(f"✅ Quotation saved in the database with ID: {quotation_id}")

        cursor.close()
        connection.close()

        return quotation_id

    except mysql.connector.Error as e:
        print("❌ Database Connection Error:", e)
        return None


# Pricing Logic
def calculate_price(t_shirt_type, quantity):
    base_prices = {"Basic Cotton": 10.0, "Premium Cotton": 15.0, "Polyester": 12.0, "Custom Design": 20.0}
    price_per_unit = base_prices.get(t_shirt_type, 10.0)
    total_price = price_per_unit * quantity
    return price_per_unit, total_price


# Generate Quotation PDF
def generate_pdf(quotation):
    directory = "quotations"
    os.makedirs(directory, exist_ok=True)  # Ensure the folder exists

    # Sanitize the filename (remove spaces and special characters)
    safe_name = quotation.customer_name.replace(" ", "_").replace("/", "_")
    file_path = os.path.join(directory, f"{safe_name}_Quotation.pdf")

    # Check if the file exists and remove it to avoid permission errors
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Existing PDF deleted: {file_path}")
        except PermissionError:
            print(f"Permission error while deleting {file_path}. Close the file if it's open.")
            return None

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, "T-Shirt Printing Co. - Quotation", ln=True, align="C")
        pdf.ln(10)
        pdf.cell(200, 10, f"Customer: {quotation.customer_name}", ln=True)
        pdf.cell(200, 10, f"Email: {quotation.email}", ln=True)
        pdf.cell(200, 10, f"Phone: {quotation.phone}", ln=True)
        pdf.cell(200, 10, f"T-Shirt Type: {quotation.t_shirt_type}", ln=True)
        pdf.cell(200, 10, f"Quantity: {quotation.quantity}", ln=True)
        pdf.cell(200, 10, f"Price per Unit: ${quotation.price_per_unit}", ln=True)
        pdf.cell(200, 10, f"Total Price: ${quotation.total_price}", ln=True)
        pdf.cell(200, 10, f"Estimated Delivery: {quotation.estimated_delivery}", ln=True)

        pdf.output(file_path)
        print(f"PDF generated: {file_path}")
        return file_path

    except PermissionError:
        print(f"Permission error while writing to {file_path}. Try running as administrator.")
        return None


# Send Email with Quotation
def send_email(quotation, pdf_path):
    if pdf_path is None:
        print("Skipping email sending due to PDF generation failure.")
        return

    recipient = quotation.email  # Use email from QuotationResponse object
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = recipient
        msg["Subject"] = f"Quotation for {quotation.customer_name}"

        # Email body
        body = f"Dear {quotation.customer_name},\n\nPlease find attached your quotation.\n\nBest regards,\nT-Shirt Printing Co."
        msg.attach(MIMEText(body, "plain"))

        # Attach the PDF file automatically
        with open(pdf_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(pdf_path)}")
            msg.attach(part)

        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, recipient, msg.as_string())
        server.quit()
        print(f"✅ Email with PDF sent successfully to {recipient}.")

    except Exception as e:
        print("❌ Email Error:", e)


# Test database connection
def test_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("✅ Connected to MySQL database successfully.")
        connection.close()
    except mysql.connector.Error as e:
        print("❌ MySQL Connection Error:", e)


# Example execution
def main():
    test_quotation = QuotationResponse(
        customer_name="John Doe",
        email="vkr10906@gmail.com",  # ✅ The email will be sent here automatically
        phone="1234567890",
        t_shirt_type="Premium Cotton",
        quantity=10,
        price_per_unit=15.0,
        total_price=150.0,
        estimated_delivery="5-7 days"
    )

    pdf_path = generate_pdf(test_quotation)  # Generate the PDF
    send_email(test_quotation, pdf_path)  # Automatically send the email with the attached PDF


if __name__ == "__main__":
    main()

