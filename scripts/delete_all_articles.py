import asyncio
import os
import sys
import shutil
from pathlib import Path

# Proje dizinini yola ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import delete
from app.database.database import AsyncSessionLocal
from app.database.models import Article, ArticleTag

async def main():
    print("Tüm haberler ve onlara ait etiket ilişkileri veritabanından siliniyor...")
    
    async with AsyncSessionLocal() as db:
        # 1. Önce ilişkili etiket tablolarını temizle
        await db.execute(delete(ArticleTag))
        print("- Haber-Etiket ilişkileri silindi.")
        
        # 2. Ana haberleri sil
        result = await db.execute(delete(Article))
        
        # 3. İşlemi kaydet
        await db.commit()
        print("- Tüm haber kayıtları veritabanından tamamen silindi.")
        
    # 4. İndirilmiş eski görselleri sil (Telif riski olan görseller sunucudan tamamen kaldırılsın)
    print("\nSunucudaki riskli eski görseller temizleniyor...")
    base_dir = Path(__file__).resolve().parent.parent
    media_dir = base_dir / "data" / "media" / "articles"
    
    if media_dir.exists():
        try:
            # Klasör içindeki dosyaları tek tek sil (klasör kalsın)
            for item in media_dir.iterdir():
                if item.is_file():
                    item.unlink()
            print("- Eski haber görselleri tamamen silindi.")
        except Exception as e:
            print(f"- Görseller silinirken bir hata oluştu: {e}. (Görseller silinememiş olabilir ancak sitede görünmeyecekler)")
    else:
        print("- Silinecek görsel bulunamadı.")
        
    print("\n✅ İŞLEM TAMAMLANDI: Site tamamen temizlendi. Yapay zeka ve BBC/Sputnik şimdi sıfırdan ve telifsiz olarak haber girmeye başlayacak.")

if __name__ == "__main__":
    asyncio.run(main())
