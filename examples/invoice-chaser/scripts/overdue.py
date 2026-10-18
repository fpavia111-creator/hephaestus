import csv, sys, datetime
today = datetime.date.today()
for row in csv.DictReader(open(sys.argv[1], encoding="utf-8")):
    if datetime.date.fromisoformat(row["due"]) < today and row["paid"] != "yes":
        print(row["client"], row["amount"], row["due"])
