import os
import requests


BREVO_URL = "https://api.brevo.com/v3/smtp/email"

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_EMAIL = os.getenv("BREVO_EMAIL")


def send_enquiry_email(enquiry):

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }

    # --------------------------------
    # SUBJECT
    # --------------------------------

    subject_map = {
        "valuation": f"New Valuation Request from {enquiry.name}",
        "contact": f"New Contact Enquiry from {enquiry.name}",
        "property": f"New Property Enquiry: {enquiry.property_name or 'N/A'}",
    }

    subject = subject_map.get(
        enquiry.form_type,
        f"New Website Enquiry from {enquiry.name}"
    )

    # --------------------------------
    # HTML EMAIL
    # --------------------------------

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color:#222;">

        <h2>New Website Enquiry</h2>

        <hr>

        <p>
            <strong>Enquiry Type:</strong>
            {enquiry.get_form_type_display()}
        </p>

        <p>
            <strong>Name:</strong>
            {enquiry.name}
        </p>

        <p>
            <strong>Email:</strong>
            {enquiry.email}
        </p>

        <p>
            <strong>Phone:</strong>
            {enquiry.phone}
        </p>
    """

    # --------------------------------
    # PROPERTY TYPE
    # --------------------------------

    if enquiry.property_type:
        html += f"""
        <p>
            <strong>Property Type:</strong>
            {enquiry.property_type}
        </p>
        """

    # --------------------------------
    # PROPERTY / BLOG NAME
    # --------------------------------

    if enquiry.property_name:
        html += f"""
        <p>
            <strong>Property / Blog:</strong>
            {enquiry.property_name}
        </p>
        """

    # --------------------------------
    # SLUG
    # --------------------------------

    if enquiry.property_slug:
        html += f"""
        <p>
            <strong>Page Slug:</strong>
            {enquiry.property_slug}
        </p>
        """

    # --------------------------------
    # INTEREST
    # --------------------------------

    if enquiry.interest:
        html += f"""
        <p>
            <strong>Interest:</strong>
            {enquiry.interest}
        </p>
        """

    # --------------------------------
    # MESSAGE
    # --------------------------------

    if enquiry.message:
        html += f"""
        <p>
            <strong>Message:</strong>
        </p>

        <p>
            {enquiry.message}
        </p>
        """

    html += """
        <hr>

        <p style="font-size:12px;color:#777;">
            This enquiry was submitted from the website.
        </p>

    </body>
    </html>
    """

    # --------------------------------
    # BREVO PAYLOAD
    # --------------------------------

    payload = {
        "sender": {
            "name": "Website Enquiry",
            "email": BREVO_EMAIL,
        },

        "to": [
            {
                "email": BREVO_EMAIL,
                "name": "Site Admin",
            }
        ],

        "replyTo": {
            "email": enquiry.email,
            "name": enquiry.name,
        },

        "subject": subject,

        "htmlContent": html,
    }

    # --------------------------------
    # DEBUG
    # --------------------------------

    print("====================================")
    print("SENDING BREVO EMAIL")
    print("====================================")
    print("To:", BREVO_EMAIL)
    print("From:", BREVO_EMAIL)
    print("Reply To:", enquiry.email)
    print("Subject:", subject)
    print("Form Type:", enquiry.form_type)
    print("Enquiry ID:", enquiry.id)
    print("====================================")

    # --------------------------------
    # SEND
    # --------------------------------

    response = requests.post(
        BREVO_URL,
        json=payload,
        headers=headers,
        timeout=10,
    )

    print("========== BREVO RESPONSE ==========")
    print("Status Code:", response.status_code)
    print("Response:", response.text)
    print("====================================")

    response.raise_for_status()

    return response.json()
