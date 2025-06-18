import freesound
import os

# 🔑 API klíč
API_KEY = "VV7pMu2KzRHPQkBZAFeSg96sH4hPdHi6OMryNnCc"

client = freesound.FreesoundClient()
client.set_token(API_KEY, "token")

# 📁 Cílová složka
output_dir = "freesound_gunshots"
os.makedirs(output_dir, exist_ok=True)

# 🔍 Vyhledání výsledků (BEZ filtru, pro jistotu)
pager = client.text_search(query="gunshot", page_size=15)

print("🔍 Výpis výsledků:\n")
for i, sound in enumerate(pager):
    print(f"[{i+1}] {sound.name} (ID: {sound.id}) | Licence: {sound.license}")
    try:
        # 🟢 Vytažení jména a cesty k souboru
        filename = f"{sound.id}_{sound.name.replace(' ', '_').replace('/', '_')}.mp3"
        filepath = os.path.join(output_dir, filename)

        # ⬇️ Stažení náhledu (preview MP3)
        preview_url = sound.previews.preview_lq_mp3
        import urllib.request
        urllib.request.urlretrieve(preview_url, filepath)
        print(f"   ✅ Uloženo jako {filename}")
    except Exception as e:
        print(f"   ❌ Chyba: {e}")

print("\n✅ Hotovo!")