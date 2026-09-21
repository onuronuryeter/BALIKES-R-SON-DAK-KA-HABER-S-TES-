import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.services.relevance_engine import evaluate_relevance

def run_test_case(name, title, content, expected_high=False, expected_zero=False):
    score, regions, category = evaluate_relevance(title, content)
    
    if expected_high:
        passed = score >= 50
        status = "PASS" if passed else "FAIL"
        print(f"{name} - Skor: {score} | Beklenen: HIGH MATCH (>=50) | {status}")
    elif expected_zero:
        passed = score < 20 # Sadece genel ulusal kelimelerden düşük skor alabilir
        status = "PASS" if passed else "FAIL"
        print(f"{name} - Skor: {score} | Beklenen: NO MATCH / WEAK (<20) | {status}")
    else:
        passed = True
        status = "PASS"
        print(f"{name} - Skor: {score} | Bölgeler: {regions} | Kat: {category}")
        
    return passed

def test_relevance():
    print("==================================================")
    print("RELEVANCE ENGINE TEST")
    print("==================================================")
    
    results = []
    
    # A) Aynı olay / benzer başlık
    t_a = "Balıkesir Büyükşehir Belediyesi'nden yeni yatırım"
    c_a = "Başkan Yücel Yılmaz, Karesi ve Altıeylül ilçelerinde yeni projeleri duyurdu."
    results.append(run_test_case("A) Balıkesir Haber", t_a, c_a, expected_high=True))
    
    # B) Aynı şehir / farklı olay (Relevance için sadece Balıkesir olması yeterlidir, event olayı duplicate'tedir)
    t_b = "Bandırma'da trafik kazası"
    c_b = "Bandırma ilçesinde meydana gelen kazada 2 kişi yaralandı."
    results.append(run_test_case("B) İlçe Haberi", t_b, c_b, expected_high=True))

    # C) İstanbul (İlgisiz)
    t_c = "İstanbul'da trafik kazası"
    c_c = "E-5 karayolunda meydana gelen kazada 2 kişi yaralandı."
    results.append(run_test_case("C) İstanbul Haber", t_c, c_c, expected_zero=True))
    
    # D) Ulusal Haber
    t_d = "Ekonomide yeni enflasyon verileri açıklandı"
    c_d = "Merkez bankası faiz oranlarını sabit tuttuğunu duyurdu."
    results.append(run_test_case("D) Ulusal Ekonomi", t_d, c_d, expected_high=True))

    print("==================================================")
    if all(results):
        print("RELEVANCE TEST: PASS")
        sys.exit(0)
    else:
        print("RELEVANCE TEST: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    test_relevance()
