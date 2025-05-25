from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import gspread

# 👇 שם קובץ ה-JSON שלך
SERVICE_ACCOUNT_FILE = "service_account_sheets.json"

# 👇 Spreadsheet ID מתוך כתובת ה-URL של הגיליון
SPREADSHEET_ID = "1_yk6pCp9wTraN9kaTnvIixAhkARAyILPfaokhxdHZgQ"

# 👇 הרשאות (scopes) לכל השירותים
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents.readonly"
]

# 📌 טוען האישורים
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE,
                                              scopes=SCOPES)

# 📄 Sheets API – חיבור לגיליון
try:
  client = gspread.authorize(creds)
  sheet = client.open_by_key(SPREADSHEET_ID).sheet1
  print("✅ Google Sheets API מחובר – שם הגיליון:", sheet.title)
except Exception as e:
  print("❌ שגיאה בחיבור ל-Google Sheets:", e)
  exit()

# 📁 Drive API – בדיקת חיבור
try:
  drive_service = build("drive", "v3", credentials=creds)
  files = drive_service.files().list(pageSize=1).execute().get("files", [])
  print("✅ Google Drive API מחובר – לדוגמה:",
        files[0]["name"] if files else "אין קבצים")
except Exception as e:
  print("❌ שגיאה בחיבור ל-Google Drive:", e)

# 📄 Docs API – חיבור ושאיבה
try:
  docs_service = build("docs", "v1", credentials=creds)
  rows = sheet.get_all_records()

  print("\n📚 מציאת מסמכים מתוך עמודת 'קישור למאמר':\n")
  for index, row in enumerate(rows,
                              start=2):  # מתחיל משורה 2 (שורה 1 היא הכותרת)
    url = row.get("קישור למאמר")  # שם העמודה המדויק בגיליון שלך
    if url and "docs.google.com" in url:
      try:
        doc_id = url.split("/d/")[1].split("/")[0]
        doc = docs_service.documents().get(documentId=doc_id).execute()
        print(f"✅ [{index}] שם המסמך:", doc["title"])
      except Exception as doc_err:
        print(f"❌ [{index}] שגיאה במסמך:", doc_err)
    else:
      print(f"⚠️ [{index}] אין קישור למסמך בשורה זו")

except Exception as e:
  print("❌ שגיאה כללית בחיבור ל-Google Docs:", e)
