from app import parse_mpesa_messages


def test_mpesa_parsing():
  sample_sms = (
      "UA47K9P2L1 Confirmed. Ksh510.00 sent to SHIRLEEN NYAGA 0792886761 on"
      " 14/11/26 at 10:15 AM. New M-PESA balance is Ksh4,230.00. Transaction"
      " cost, Ksh7.00."
  )

  transactions = parse_mpesa_messages(sample_sms)

  assert len(transactions) == 1, "Should find exactly 1 transaction"
  assert transactions[0]["code"] == "UA47K9P2L1", "Transaction code should match"
  assert transactions[0]["amount"] == 510.00, "Amount should be 510.00"
  assert transactions[0]["cost"] == 7.00, "Cost should be 7.00"

  print("✅ Success! All M-Pesa parser unit tests passed.")


if __name__ == "__main__":
  test_mpesa_parsing()
