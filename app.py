import re
from flask import Flask, render_template, request

app = Flask(__name__)


def parse_mpesa_messages(raw_text):
    """
    Parses raw M-Pesa SMS confirmation messages using Regular Expressions.
    Handles Sent Money, Paybill, Buy Goods (Till), Received Money, Airtime, and Withdrawals.
    """
    # Split text into individual messages using the 10-character M-Pesa code + "Confirmed."
    chunks = re.split(r'(?=\b[A-Z0-9]{10}\s+Confirmed\.)', raw_text.strip())
    transactions = []

    for chunk in chunks:
        msg = " ".join(chunk.strip().split())  # Normalize newlines/extra spaces
        if not msg:
            continue

        # 1. Extract 10-character Transaction Code
        code_match = re.search(r'^([A-Z0-9]{10})\s+Confirmed\.', msg)
        if not code_match:
            continue
        code = code_match.group(1)

        # 2. Extract Amount (e.g., Ksh1,500.00 or Ksh510.00)
        amount_match = re.search(r'Ksh([\d,]+\.\d{2})', msg)
        amount = float(amount_match.group(1).replace(',', '')) if amount_match else 0.0

        # 3. Extract Transaction Cost
        cost_match = re.search(r'Transaction cost,\s*Ksh([\d,]+\.\d{2})', msg, re.IGNORECASE)
        cost = float(cost_match.group(1).replace(',', '')) if cost_match else 0.0

        # 4. Extract Date and Time (e.g., on 14/11/26 at 2:30 PM)
        datetime_match = re.search(
            r'on\s+(\d{1,2}/\d{1,2}/\d{2,4})\s+at\s+(\d{1,2}:\d{2}\s*[AP]M)',
            msg,
            re.IGNORECASE,
        )
        date_str = f"{datetime_match.group(1)} {datetime_match.group(2)}" if datetime_match else "Unknown Date"

        # 5. Determine Transaction Type & Counterparty (Recipient / Sender)
        tx_type = "Other"
        party = "N/A"
        flow = "expense"  # 'expense' or 'income'

        if "sent to" in msg:
            if "for account" in msg:
                tx_type = "Paybill"
                party_match = re.search(r'sent to\s+(.+?)\s+for account', msg)
            else:
                tx_type = "Send Money"
                party_match = re.search(r'sent to\s+(.+?)\s+on\s+\d', msg)
            party = party_match.group(1).strip() if party_match else "Recipient"

        elif "paid to" in msg:
            tx_type = "Buy Goods (Till)"
            party_match = re.search(r'paid to\s+(.+?)\.\s*on\s+\d', msg)
            if not party_match:
                party_match = re.search(r'paid to\s+(.+?)\s+on\s+\d', msg)
            party = party_match.group(1).strip() if party_match else "Merchant"

        elif "You have received" in msg:
            tx_type = "Received Money"
            flow = "income"
            party_match = re.search(r'from\s+(.+?)\s+on\s+\d', msg)
            party = party_match.group(1).strip() if party_match else "Sender"

        elif "bought" in msg and "airtime" in msg.lower():
            tx_type = "Airtime"
            party = "Safaricom Airtime"

        elif "Withdraw" in msg:
            tx_type = "Agent Withdrawal"
            party_match = re.search(r'from\s+(.+?)\s+New M-PESA', msg)
            party = party_match.group(1).strip() if party_match else "M-Pesa Agent"

        transactions.append({
            "code": code,
            "type": tx_type,
            "party": party,
            "amount": amount,
            "cost": cost,
            "date": date_str,
            "flow": flow,
        })

    return transactions


SAMPLE_SMS = """UA47K9P2L1 Confirmed. Ksh510.00 sent to SHIRLEEN NYAGA 0792886761 on 14/11/26 at 10:15 AM. New M-PESA balance is Ksh4,230.00. Transaction cost, Ksh7.00.
UA46M3X8Q9 Confirmed. Ksh1,250.00 paid to NAIVAS SUPERMARKET. on 13/11/26 at 5:42 PM. New M-PESA balance is Ksh4,747.00. Transaction cost, Ksh0.00.
UA45R1T7W4 Confirmed. You have received Ksh8,500.00 from TECH CONSULTING CLIENT 0712345678 on 12/11/26 at 11:20 AM. New M-PESA balance is Ksh5,997.00.
UA44B8N5C2 Confirmed. Ksh2,000.00 sent to KPLC PREPAID for account 142536789 on 11/11/26 at 8:05 AM. New M-PESA balance is Ksh1,497.00. Transaction cost, Ksh23.00.
UA43V6Z2M0 Confirmed. You bought Ksh100.00 of airtime on 10/11/26 at 1:10 PM. New M-PESA balance is Ksh3,520.00. Transaction cost, Ksh0.00."""


@app.route('/', methods=['GET', 'POST'])
def index():
    raw_text = SAMPLE_SMS
    if request.method == 'POST':
        raw_text = request.form.get('sms_text', '')

    transactions = parse_mpesa_messages(raw_text)

    total_spent = sum(t['amount'] for t in transactions if t['flow'] == 'expense')
    total_received = sum(t['amount'] for t in transactions if t['flow'] == 'income')
    total_fees = sum(t['cost'] for t in transactions)

    # Group expenses by category for Chart.js
    category_totals = {}
    for t in transactions:
        if t['flow'] == 'expense':
            category_totals[t['type']] = category_totals.get(t['type'], 0) + t['amount']

    return render_template(
        'index.html',
        raw_text=raw_text,
        transactions=transactions,
        total_spent=total_spent,
        total_received=total_received,
        total_fees=total_fees,
        chart_labels=list(category_totals.keys()),
        chart_values=list(category_totals.values()),
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000)