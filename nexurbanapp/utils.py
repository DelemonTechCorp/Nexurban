import os
import requests
import re


ROMAN = re.compile(r"\b(Ii|Iii|Iv|Vi|Vii|Viii|Ix)\b")

ABBREVIATIONS = {
    "Mohammed Bin Rashid Al Maktoum City": "MBR City",
    "Mohammed Bin Rashid City": "MBR City",
}


def _shorten(text):
    for long_name, short_name in ABBREVIATIONS.items():
        text = text.replace(long_name, short_name)
    return text


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

    # ---------------- SEO TITLES ----------------

SEO_SUFFIX = " | Nexurban Properties"
SEO_SUFFIX_SHORT = " | Nexurban"
SEO_MAX = 60


def _fix_text(text):
    """Encoding kedukal thiruthum (Dâ€™azur, ÙÙAzizi pole)."""
    text = (text or "").strip()
    try:
        text = text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    text = " ".join(text.replace("\u00d9", "").split())
    text = re.sub(r"\s+,", ",", text)
    text = ROMAN.sub(lambda m: m.group(1).upper(), text)
    return text


def _fit(options, fallback, suffixes=(SEO_SUFFIX, SEO_SUFFIX_SHORT)):
    for suffix in suffixes:
        for t in options:
            if len(t + suffix) <= SEO_MAX:
                return t + suffix

    last = suffixes[-1]
    room = SEO_MAX - len(last)
    cut = fallback[:room].rsplit(" ", 1)[0].rstrip(" ,-")
    return cut + last


def build_property_title(name, area=""):
    name = _fix_text(name)
    area = _fix_text(area)

    short = _shorten(name)

    options = []
    for n in dict.fromkeys((name, short)):
        if area:
            options.append(f"{n} for Sale in {area}, Dubai, Prices")
            options.append(f"{n} for Sale in {area}, Dubai")
        options.append(f"{n} for Sale in Dubai, Prices & Payment Plan")
        options.append(f"{n} for Sale in Dubai")
    options += [name, short]

    if "," in short:
        options.append(short.split(",", 1)[1].strip())

    return _fit(options, short, suffixes=(SEO_SUFFIX,))
   


def build_area_title(area_name):
    area_name = _fix_text(area_name)
    return _fit(
        [
            f"{area_name} Properties for Sale & Rent in Dubai",
            f"{area_name} Properties for Sale & Rent",
            f"{area_name} Properties for Sale",
            area_name,
        ],
        area_name,
    )
