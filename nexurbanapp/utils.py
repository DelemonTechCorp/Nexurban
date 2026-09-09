import os
import requests


BREVO_URL = "https://api.brevo.com/v3/smtp/email"

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_EMAIL = os.getenv("BREVO_EMAIL")

print("BREVO_API_KEY EXISTS:", bool(BREVO_API_KEY))
print("BREVO_EMAIL VALUE:", repr(BREVO_EMAIL))


def send_enquiry_email(enquiry):
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }

    subject_map = {
        "valuation": f"New Valuation Request from {enquiry.name}",
        "contact": f"New Contact Enquiry from {enquiry.name}",
        "property": f"New Property Enquiry: {enquiry.property_name or 'N/A'}",
    }

    html = f"""
    <html>
        <body>
            <h2>New Website Enquiry</h2>

            <p><strong>Type:</strong> {enquiry.get_form_type_display()}</p>
            <p><strong>Name:</strong> {enquiry.name}</p>
            <p><strong>Email:</strong> {enquiry.email}</p>
            <p><strong>Phone:</strong> {enquiry.phone}</p>
    """

    if enquiry.property_type:
        html += f"""
            <p><strong>Property Type:</strong> {enquiry.property_type}</p>
        """

    if enquiry.property_name:
        html += f"""
            <p><strong>Property:</strong> {enquiry.property_name}</p>
        """

    if enquiry.property_slug:
        html += f"""
            <p><strong>Property Slug:</strong> {enquiry.property_slug}</p>
        """

    if enquiry.interest:
        html += f"""
            <p><strong>Interested In:</strong> {enquiry.interest}</p>
        """

    if enquiry.message:
        html += f"""
            <p><strong>Message:</strong></p>
            <p>{enquiry.message}</p>
        """

    html += """
        </body>
    </html>
    """

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
        "subject": subject_map.get(
            enquiry.form_type,
            "New Website Enquiry"
        ),
        "htmlContent": html,
    }

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
