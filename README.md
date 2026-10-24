# İnşirah — namaz vakitleri verisi

İnşirah iOS uygulamasının kullandığı namaz vakitlerini her hafta yayımlar.

- **Kaynak:** Diyanet İşleri Başkanlığı'nın yayımladığı vakitler, [ezanvakti.emushaf.net](https://ezanvakti.emushaf.net) aracılığıyla (Diyanet'in ilçe numaraları; vakit hesaplanmaz).
- **Doğrulama:** Her çalıştırmada 15 ilçe, bağımsız ikinci bir kaynakla ([ezanvakti.imsakiyem.com](https://ezanvakti.imsakiyem.com)) karşılaştırılır. Tek dakika fark varsa hiçbir şey yayımlanmaz.
- **Yayın:** GitHub Pages, `https://mikehrmantraut.github.io/insirahapptimer/v1/`
  - `places.json`: `[{"id", "name", "state"}]` (869 yer; büyükşehirlerin merkez ilçeleri il adıyla tek kayıttır)
  - `times/<id>.json`: `{"place", "updatedAt", "source", "days": [{"date", "imsak", "gunes", "ogle", "ikindi", "aksam", "yatsi", "hijri"}]}`

Görev her pazartesi 04:00'te (Türkiye) çalışır; Actions sekmesinden elle de çalıştırılabilir.

Yerelde deneme: `python3 -I scripts/fetch_prayer_times.py site/v1` · Testler: `python3 -I -m unittest discover -s scripts -p 'test_*.py'`
