import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.database.database import AsyncSessionLocal
from app.database.models import Category
from sqlalchemy import select

async def seed_districts():
    async with AsyncSessionLocal() as session:
        # Önce üst kategori (İlçeler) var mı bakalım
        res = await session.execute(select(Category).where(Category.slug == 'ilceler'))
        parent = res.scalar_one_or_none()
        
        if not parent:
            parent = Category(
                name="İlçeler",
                slug="ilceler",
                description="Balıkesir'in tüm ilçelerinden güncel haberler.",
                color="#495057",
                order=10,
                is_active=True,
                show_in_nav=True
            )
            session.add(parent)
            await session.commit()
            await session.refresh(parent)
            print("İlçeler (ilceler) üst kategorisi oluşturuldu.")

        # İlçe Verileri ve SEO Uyumlu Kapsamlı İçerikler
        districts_data = [
            {
                "name": "Karesi",
                "slug": "karesi",
                "color": "#c1121f",
                "seo_title": "Karesi Haberleri - Son Dakika Karesi Haber ve Gelişmeleri",
                "seo_description": "Balıkesir Karesi ilçesinden son dakika haberleri, yerel yönetim çalışmaları, asayiş, Karesi nüfus ve turizm bilgileri.",
                "description": """
                <div class="district-guide my-4">
                    <h3>Karesi: Balıkesir'in Tarihi ve Dinamik Merkezi</h3>
                    <img src="https://images.unsplash.com/photo-1549880181-56a44cf4a9a5?auto=format&fit=crop&w=800&q=80" alt="Karesi Manzarası" class="img-fluid rounded mb-3 shadow-sm" style="max-height:400px; width:100%; object-fit:cover;">
                    <p><strong>Tarihçe ve Genel Bilgiler:</strong> Karesi, Balıkesir ilinin büyükşehir olmasıyla kurulan merkez ilçelerden biridir. Adını, bölgede hüküm süren Karesi Beyliği'nden alır. Zengin tarihi dokusuyla Osmanlı mimarisinin izlerini taşır.</p>
                    <p><strong>Nüfus:</strong> 2023 verilerine göre Karesi nüfusu yaklaşık 185.000 civarındadır. Şehrin en hareketli ve ticaretin yoğun olduğu bölgelerinden birini oluşturur.</p>
                    <p><strong>Turizm ve Gezilecek Yerler:</strong> Zağnos Paşa Camii, Karesi Türbesi, Milli Kuvvetler Caddesi, Saat Kulesi ve tarihi Balıkesir Evleri mutlaka görülmesi gereken yerlerdir.</p>
                </div>
                """
            },
            {
                "name": "Altıeylül",
                "slug": "altieylul",
                "color": "#023e8a",
                "seo_title": "Altıeylül Haberleri - Güncel Altıeylül Balıkesir Haberleri",
                "seo_description": "Altıeylül haberleri, yerel etkinlikler, Altıeylül belediyesi projeleri, nüfus ve gezilecek yerler hakkında her şey.",
                "description": """
                <div class="district-guide my-4">
                    <h3>Altıeylül: Kurtuluşun ve Gelişimin Simgesi</h3>
                    <img src="https://images.unsplash.com/photo-1527038338981-645511394a5c?auto=format&fit=crop&w=800&q=80" alt="Altıeylül Manzarası" class="img-fluid rounded mb-3 shadow-sm" style="max-height:400px; width:100%; object-fit:cover;">
                    <p><strong>Tarihçe ve Genel Bilgiler:</strong> Altıeylül, ismini Balıkesir'in düşman işgalinden kurtuluş günü olan 6 Eylül'den almaktadır. Şehrin güney bölümünü kapsayan modern yüzüdür.</p>
                    <p><strong>Nüfus:</strong> İlçe nüfusu hızla gelişen konut projeleriyle birlikte 180.000'i aşmış durumdadır.</p>
                    <p><strong>Turizm ve Gezilecek Yerler:</strong> Atatürk Parkı (Eski Fuar Alanı), Hasanbaba Çarşısı çevresi ve kırsal turizme uygun yemyeşil köyleriyle öne çıkar. Ayrıca Pamukçu Termal Tesisleri sağlık turizmi açısından önemlidir.</p>
                </div>
                """
            },
            {
                "name": "Bandırma",
                "slug": "bandirma",
                "color": "#0077b6",
                "seo_title": "Bandırma Son Dakika Haberleri - Bandırma Yerel Haber",
                "seo_description": "Bandırma'dan son dakika haberler, liman kenti gelişmeleri, Bandırma nüfus, tarih ve Manyas Kuş Cenneti turizmi.",
                "description": """
                <div class="district-guide my-4">
                    <h3>Bandırma: Marmara'nın İncisi ve Liman Kenti</h3>
                    <img src="https://images.unsplash.com/photo-1558285549-2a0753063544?auto=format&fit=crop&w=800&q=80" alt="Bandırma Sahili" class="img-fluid rounded mb-3 shadow-sm" style="max-height:400px; width:100%; object-fit:cover;">
                    <p><strong>Tarihçe ve Genel Bilgiler:</strong> Bandırma, Balıkesir'in Marmara Denizi'ne kıyısı olan, sanayi, ticaret ve liman kentidir. Antik çağlara uzanan köklü bir tarihi vardır.</p>
                    <p><strong>Nüfus:</strong> 160.000'in üzerindeki nüfusuyla Balıkesir'in en büyük ilçelerinden biridir.</p>
                    <p><strong>Turizm ve Gezilecek Yerler:</strong> Manyas Kuş Cenneti Milli Parkı, Kyzikos Antik Kenti, Son Kurşun Anıtı ve Bandırma sahil bandı turistlerin uğrak noktalarıdır.</p>
                </div>
                """
            },
            {
                "name": "Edremit",
                "slug": "edremit",
                "color": "#2a9d8f",
                "seo_title": "Edremit Son Dakika Haberleri - Körfez Haberleri",
                "seo_description": "Edremit Körfezi haberleri, Kazdağları turizmi, Edremit zeytini, nüfus, asayiş ve yerel haberler.",
                "description": """
                <div class="district-guide my-4">
                    <h3>Edremit: Zeytinin ve Doğanın Başkenti</h3>
                    <img src="https://images.unsplash.com/photo-1473448912268-2022ce9509d8?auto=format&fit=crop&w=800&q=80" alt="Edremit Doğası" class="img-fluid rounded mb-3 shadow-sm" style="max-height:400px; width:100%; object-fit:cover;">
                    <p><strong>Tarihçe ve Genel Bilgiler:</strong> Edremit Körfezi'nin kalbi olan ilçe, efsanelere konu olan Kazdağları'nın (İda) eteklerinde yer alır. Zeytini ve zeytinyağı ile dünya çapında üne sahiptir.</p>
                    <p><strong>Nüfus:</strong> Yaz aylarında nüfusu milyonları bulsa da yerleşik nüfusu yaklaşık 170.000'dir.</p>
                    <p><strong>Turizm ve Gezilecek Yerler:</strong> Kazdağları Milli Parkı, Hasanboğuldu Şelalesi, Akçay ve Altınoluk plajları, Antandros Antik Kenti, Şahinderesi Kanyonu.</p>
                </div>
                """
            },
            {
                "name": "Ayvalık",
                "slug": "ayvalik",
                "color": "#e9c46a",
                "seo_title": "Ayvalık Haberleri - Ayvalık Son Dakika ve Turizm Haberleri",
                "seo_description": "Ayvalık son dakika haberleri, Cunda adası, Sarımsaklı plajı turizm gelişmeleri, Ayvalık nüfusu ve tarihi güzellikler.",
                "description": """
                <div class="district-guide my-4">
                    <h3>Ayvalık: Tarihi Evleri ve Cunda'nın Eşsiz Güzelliği</h3>
                    <img src="https://images.unsplash.com/photo-1627885542878-57e3f4214f4e?auto=format&fit=crop&w=800&q=80" alt="Ayvalık Manzarası" class="img-fluid rounded mb-3 shadow-sm" style="max-height:400px; width:100%; object-fit:cover;">
                    <p><strong>Tarihçe ve Genel Bilgiler:</strong> Rum mimarisinin en güzel örneklerini barındıran Ayvalık, Ege'nin en çok tercih edilen turizm merkezlerindendir.</p>
                    <p><strong>Nüfus:</strong> Yerleşik nüfusu 70.000 civarındadır ancak turizm sezonunda devasa bir kalabalığa ev sahipliği yapar.</p>
                    <p><strong>Turizm ve Gezilecek Yerler:</strong> Şeytan Sofrası, Cunda (Alibey) Adası, Sarımsaklı Plajları, Taksiyarhis Kilisesi, Ayvalık Tarihi Evleri ve sokakları.</p>
                </div>
                """
            },
            {
                "name": "Burhaniye",
                "slug": "burhaniye",
                "color": "#f4a261",
                "seo_title": "Burhaniye Son Dakika Haberleri - Körfezdeki Huzur",
                "seo_description": "Burhaniye ilçesi son dakika gelişmeleri, Ören plajları, turizm festivalleri, nüfus bilgileri ve Burhaniye haber.",
                "description": """
                <div class="district-guide my-4">
                    <h3>Burhaniye: Körfezin Huzur Veren Durağı</h3>
                    <img src="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80" alt="Burhaniye Sahili" class="img-fluid rounded mb-3 shadow-sm" style="max-height:400px; width:100%; object-fit:cover;">
                    <p><strong>Tarihçe ve Genel Bilgiler:</strong> Antik dönemde Adramytteion olarak bilinen bölgenin hemen yanında kurulan Burhaniye, geniş zeytinlikleri ve masmavi deniziyle bilinir.</p>
                    <p><strong>Nüfus:</strong> Yaklaşık 65.000 yerleşik nüfusu vardır.</p>
                    <p><strong>Turizm ve Gezilecek Yerler:</strong> Ören Plajı (Mavi Bayraklı), Pelitköy sahilleri, Adramytteion Antik Kenti ve tarihi meşe ağaçlarıyla kaplı Ören Meydanı.</p>
                </div>
                """
            }
        ]

        for d in districts_data:
            res = await session.execute(select(Category).where(Category.slug == d["slug"]))
            existing = res.scalar_one_or_none()
            if not existing:
                cat = Category(
                    name=d["name"],
                    slug=d["slug"],
                    color=d["color"],
                    seo_title=d["seo_title"],
                    seo_description=d["seo_description"],
                    description=d["description"],
                    parent_id=parent.id,
                    order=0,
                    is_active=True,
                    show_in_nav=False # Nav'da ilceler menüsü altında çıkacak
                )
                session.add(cat)
                print(f"Eklendi: {d['name']}")
            else:
                existing.description = d["description"]
                existing.seo_title = d["seo_title"]
                existing.seo_description = d["seo_description"]
                print(f"Güncellendi: {d['name']}")
                
        await session.commit()
        print("İlçeler başarıyla oluşturuldu/güncellendi!")

if __name__ == "__main__":
    asyncio.run(seed_districts())
