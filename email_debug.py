import json
import base64
from langchain_community.tools.gmail.utils import build_resource_service

# --- Debugging Code ---
# This code can be used to examine the payload of a specific email.

# Step 1: Paste the ID of the problematic email here.
specific_message_id = ""  # Sample ID, use the ID of your problematic email

# Identity verification
api_resource = build_resource_service()

try:
    print(f"Examining the payload of the email with ID '{specific_message_id}'...\n")
    
    # Let's request all the details of that email.
    message_detail = api_resource.users().messages().get(
        userId='me', 
        id=specific_message_id, 
        format='full'
    ).execute()
    
    # Let's just examine the content structure (payload).
    payload = message_detail.get('payload', {})
    
    # Let's print the entire rotating payload to the screen in a readable format.
    print(json.dumps(payload, indent=2))

except Exception as e:
    print(f"An error has occurred: {e}")