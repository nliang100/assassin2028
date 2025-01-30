import os
from flask import Flask, request, render_template, redirect, url_for, send_file
import pandas as pd
import smtplib
from email.message import EmailMessage
import ssl

app = Flask(__name__)

# Path to store the uploaded CSV
UPLOAD_FOLDER = "uploaded_data"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the folder exists
CSV_FILE = os.path.join(UPLOAD_FOLDER, "player_data.csv")

# Global variables to store player data and filename
data = None
uploaded_file = None  # Global variable to track the uploaded file name

EMAIL_SENDER = 'PA28Assassinate@gmail.com'  # Replace with your email
EMAIL_PASSWORD = 'nsxu guco edsv nwzb'  # Replace with your app password


@app.route('/')
def index():
    """
    Displays the home page with options to upload a dataset, view player data, or process kills.
    Shows the current dataset name if it exists.
    """
    global data, uploaded_file
    if os.path.exists(CSV_FILE):
        if data is None:  # Load the dataset if not already loaded
            data = pd.read_csv(CSV_FILE)
        if not uploaded_file:  # Set uploaded_file if not already set
            uploaded_file = os.path.basename(CSV_FILE)
    return render_template(
        'index.html',
        data=data.to_html() if data is not None else None,
        uploaded_file=uploaded_file
    )


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Handles dataset uploads, saves the uploaded file, and updates the in-memory dataset.
    """
    global data, uploaded_file
    file = request.files['file']
    if file:
        # Save the uploaded file and update the global filename variable
        uploaded_file = file.filename
        file.save(CSV_FILE)
        data = pd.read_csv(CSV_FILE)  # Load the new data into memory
    return render_template(
        'upload_success.html',
        data=data.to_html(),
        uploaded_file=uploaded_file
    )


@app.route('/kill', methods=['POST'])
def process_kill():
    """
    Handles kill submissions, updates the dataset, and notifies the killer of their next target.
    """
    global data
    if data is None:
        return "No data available. Please upload a dataset first."

    killer = request.form['killer']
    if killer not in data['Names'].values:
        return "Killer not found in the dataset."

    data.reset_index(drop=True, inplace=True)
    killer_index = data.index[data['Names'] == killer][0]
    victim_index = (killer_index + 1) % len(data)  # The victim is the next in the row
    victim = data.iloc[victim_index]

    # Find the next target after the victim
    next_target_index = (victim_index + 1) % len(data)
    next_target = data.iloc[next_target_index]

    # Remove the victim
    data.drop(index=victim_index, inplace=True)
    data.reset_index(drop=True, inplace=True)

    # Save the updated dataset
    data.to_csv(CSV_FILE, index=False)

    # Send email to the killer about their next target
    killer_email = data.loc[data['Names'] == killer, 'Emails'].values[0]
    send_email(killer, next_target['Names'], killer_email)

    return render_template(
        'kill_confirmation.html',
        killer=killer,
        next_target=next_target['Names']
    )


@app.route('/data')
def view_data():
    """
    Displays the current dataset as an HTML table.
    """
    global data
    if data is None:
        return "No data available. Please upload a dataset first."
    return render_template('data.html', data=data.to_html())


def send_email(killer_name, target_name, recipient_email):
    """
    Sends an email to the killer with the name of their next target.
    """
    subject = 'Your Next Assassin Target'
    body = f"Hi {killer_name},\n\nYour next target is {target_name}. Have fun and good luck!"

    em = EmailMessage()
    em['From'] = EMAIL_SENDER
    em['To'] = recipient_email
    em['Subject'] = subject
    em.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(em)

@app.route('/send_initial_emails', methods=['POST'])
def send_initial_emails():
    global data

    if data is None or data.empty:
        return "No data available. Please upload a dataset first."

    # Assign each player their target (next player in the list, circular)
    for i in range(len(data)):
        killer_name = data.iloc[i]['Names']
        killer_email = data.iloc[i]['Emails']
        target_name = data.iloc[(i + 1) % len(data)]['Names']  # Circular assignment

        # Send email to each player with their target
        send_email(killer_name, target_name, killer_email)

    return render_template('emails_sent.html')  # Display success page


if __name__ == "__main__":
    app.run(debug=False)
