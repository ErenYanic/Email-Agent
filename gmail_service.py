import pandas as pd
import base64
from dateutil.parser import parse
from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.utils import build_resource_service

# --- YENİ VE GELİŞMİŞ FONKSİYON ---
def get_email_contents(payload):
    """
    E-posta payload'ını ne kadar iç içe olursa olsun RECURSIVE (özyinelemeli) 
    olarak gezer ve tüm 'text/plain' ve 'text/html' içeriklerini bulur.
    """
    plain_text = ""
    html_text = ""

    # Eğer 'parts' varsa, her bir parçayı gezmek için kendini tekrar çağırır.
    if 'parts' in payload:
        for part in payload['parts']:
            nested_content = get_email_contents(part)
            plain_text += nested_content['text']
            html_text += nested_content['html']

    # Eğer 'parts' yoksa veya mevcut part'ın kendi body'si varsa
    elif 'body' in payload and 'data' in payload['body']:
        mime_type = payload.get('mimeType', '')
        body_data = payload['body'].get('data', '')
        if body_data:
            try:
                decoded_body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                if 'text/plain' in mime_type:
                    plain_text += decoded_body
                elif 'text/html' in mime_type:
                    html_text += decoded_body
            except Exception:
                # Base64 decode hatası olursa bu kısmı atla
                pass
                
    return {'text': plain_text.strip(), 'html': html_text.strip()}

# --- Kodun geri kalanı tamamen aynı ---

api_resource = build_resource_service()
toolkit = GmailToolkit(api_resource=api_resource)
search_tool = next((tool for tool in toolkit.get_tools() if tool.name == 'search_gmail'), None)

if not search_tool:
    raise ValueError("Arama aracı bulunamadı.")

processed_emails = []

try:
    search_params = {"query": "in:inbox", "max_results": 10}
    search_results = search_tool.run(search_params)
    
    print(f"Son {len(search_results)} e-posta detayı çekiliyor...\n")

    for summary in search_results:
        message_id = summary.get('id')
        message_detail = api_resource.users().messages().get(userId='me', id=message_id, format='full').execute()
        
        payload = message_detail.get('payload', {})
        headers = payload.get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'N/A')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'N/A')
        to = next((h['value'] for h in headers if h['name'].lower() == 'to'), 'N/A')
        cc = next((h['value'] for h in headers if h['name'].lower() == 'cc'), 'N/A')
        date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)
        
        try: email_date = parse(date_str) if date_str else None
        except: email_date = None

        labels = message_detail.get('labelIds', [])
        is_unread = 'UNREAD' in labels
        
        contents = get_email_contents(payload)
        
        has_attachment = False
        attachment_names = []
        if 'parts' in payload:
            for part in payload.get('parts', []):
                if part.get('filename'):
                    has_attachment = True
                    attachment_names.append(part.get('filename'))

        processed_emails.append({
            'id': message_id,
            'is_unread': is_unread,
            'date': email_date,
            'from': sender,
            'to': to,
            'cc': cc,                     
            'labels': labels,
            'subject': subject,
            'body_text': contents['text'],
            'body_html': contents['html'],
            'has_attachment': has_attachment,
            'attachment_names': attachment_names
        })


    if processed_emails:
        emails_df = pd.DataFrame(processed_emails)
        emails_df = emails_df.sort_values(by='date', ascending=False, na_position='last').reset_index(drop=True)

        print("--- NİHAİ E-POSTA VERİLERİ ---")
        pd.set_option('display.max_columns', 20)
        pd.set_option('display.width', 180)
        pd.set_option('display.max_colwidth', 30)
        print(emails_df[['date', 'from', 'subject', 'body_text', 'body_html']])
        print("\n'body_text' ve 'body_html' sütunlarının doluluğunu kontrol edebilirsiniz.")
        
    else:
        print("İşlenecek e-posta bulunamadı.")

except Exception as e:
    print(f"Bir hata oluştu: {e}")


# --- TEST KISMI: DATAFRAME'İ CSV'YE KAYDETME ---

csv_filename = 'fetched_emails2.csv'
emails_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')

print(f"\nDataFrame başarıyla '{csv_filename}' dosyasına kaydedildi.")
