import json
import base64
from langchain_community.tools.gmail.utils import build_resource_service

# --- Hata Ayıklama Kodu ---

# 1. Adım: Buraya sorunlu e-postanın ID'sini yapıştırın
specific_message_id = ""  # Örnek ID, sorunlu e-postanızın ID'sini kullanın

# Kimlik doğrulama
api_resource = build_resource_service()

try:
    print(f"'{specific_message_id}' ID'li e-postanın payload'u inceleniyor...\n")
    
    # O e-postanın tüm detaylarını isteyelim
    message_detail = api_resource.users().messages().get(
        userId='me', 
        id=specific_message_id, 
        format='full'
    ).execute()
    
    # Sadece içerik yapısını (payload) inceleyelim
    payload = message_detail.get('payload', {})
    
    # Dönen payload'un tamamını, okunaklı bir formatta ekrana basalım
    print(json.dumps(payload, indent=2))

except Exception as e:
    print(f"Bir hata oluştu: {e}")