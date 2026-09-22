import shutil
import os

data_dir = r"c:\Users\baban\Desktop\BALIKESİR SON DAKİKA WEB\balikesirsondakikahaber\data"
zip_path = r"c:\Users\baban\Desktop\BALIKESİR SON DAKİKA WEB\YEDEK_DATA.zip"

if os.path.exists(zip_path):
    os.remove(zip_path)

print("Yedekleme basliyor...")
try:
    shutil.make_archive(zip_path.replace(".zip", ""), 'zip', data_dir)
    print("Yedekleme tamamlandi!")
except Exception as e:
    print("Hata:", str(e))
