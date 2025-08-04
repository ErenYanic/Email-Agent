import pandas as pd
import base64
from dateutil.parser import parse
from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.utils import build_resource_service

# --- NEW AND ENHANCED FUNCTION ---
def get_email_contents(payload):

    """
    Recursively traverses the email payload structure, regardless of how deeply nested it is,
    and extracts all 'text/plain' and 'text/html' content parts.
    
    Args:
        payload: Email payload dictionary from Gmail API
        
    Returns:
        dict: Dictionary containing 'text' and 'html' content strings
    """

    plain_text = ""
    html_text = ""

    # If 'parts' exists, recursively traverse each part by calling itself
    if 'parts' in payload:
        for part in payload['parts']:
            nested_content = get_email_contents(part)
            plain_text += nested_content['text']
            html_text += nested_content['html']

    # If no 'parts' exist or the current part has its own body content
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
                # Skip this part if base64 decode error occurs
                pass
                
    return {'text': plain_text.strip(), 'html': html_text.strip()}

# --- MAIN CODE TO FETCH AND PROCESS EMAILS ---

# Build Gmail API resource service and initialise toolkit
api_resource = build_resource_service()
toolkit = GmailToolkit(api_resource=api_resource)
search_tool = next((tool for tool in toolkit.get_tools() if tool.name == 'search_gmail'), None)

if not search_tool:
    raise ValueError("Search tool not found. Ensure the GmailToolkit is correctly initialized.")

processed_emails = []

try:
    # Search for emails in inbox with maximum 10 results
    search_params = {"query": "in:inbox", "max_results": 10}
    search_results = search_tool.run(search_params)
    
    print(f"Fetching details for the last {len(search_results)} emails...\n")

    # Process each email in search results
    for summary in search_results:
        message_id = summary.get('id')
        message_detail = api_resource.users().messages().get(userId='me', id=message_id, format='full').execute()
        
        payload = message_detail.get('payload', {})
        headers = payload.get('headers', [])
        
        # Extract email headers using generator expressions for efficiency
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'N/A')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'N/A')
        to = next((h['value'] for h in headers if h['name'].lower() == 'to'), 'N/A')
        cc = next((h['value'] for h in headers if h['name'].lower() == 'cc'), 'N/A')
        date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)
        
        # Parse email date with error handling
        try: 
            email_date = parse(date_str) if date_str else None
        except: 
            email_date = None

        # Check email labels and unread status
        labels = message_detail.get('labelIds', [])
        is_unread = 'UNREAD' in labels
        
        # Extract email contents using the recursive function        
        contents = get_email_contents(payload)
        
        # Check for attachments and collect attachment names
        has_attachment = False
        attachment_names = []
        if 'parts' in payload:
            for part in payload.get('parts', []):
                if part.get('filename'):
                    has_attachment = True
                    attachment_names.append(part.get('filename'))

        # Append processed email data to list
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

    # Create DataFrame and display results if emails were processed
    if processed_emails:
        emails_df = pd.DataFrame(processed_emails)
        emails_df = emails_df.sort_values(by='date', ascending=False, na_position='last').reset_index(drop=True)

        print("--- FINAL EMAIL DATA ---")
        # Set pandas display options for better readability
        pd.set_option('display.max_columns', 20)
        pd.set_option('display.width', 180)
        pd.set_option('display.max_colwidth', 30)
        print(emails_df[['id', 'date', 'from', 'subject', 'body_text', 'body_html']])
        print("\nYou can check the completeness of 'body_text' and 'body_html' columns.")
        
    else:
        print("No emails found to process.")

except Exception as e:
    print(f"An error occurred: {e}")


# --- TEST SECTION: SAVING DATAFRAME TO CSV ---
if 'emails_df' in locals():
    print("\nSaving DataFrame to CSV file...")

    csv_filename = 'fetched_emails.csv'
    emails_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')

    print(f"\nDataFrame successfully saved to '{csv_filename}' file.")

else:
    print("\nNo emails processed, skipping CSV save.")

