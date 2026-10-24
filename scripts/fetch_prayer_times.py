#!/usr/bin/env python3
"""Diyanet'in yayımladığı namaz vakitlerini Türkiye'deki bütün ilçeler için çekip statik JSON üretir.

Kaynak: ezanvakti.emushaf.net. Diyanet'in vakitlerini, Diyanet'in ilçe numaraları ve alan adlarıyla
olduğu gibi dağıtan açık bir API'dir; vakit hesaplamaz. Doğrulama: her çalıştırmada bir grup ilçe,
birbirinden bağımsız ikinci bir dağıtıcıyla (ezanvakti.imsakiyem.com) karşılaştırılır. Tek bir dakika
farkı bile görev hata verir ve hiçbir şey yayımlanmaz.

Uygulama bu API'lere hiçbir zaman doğrudan bağlanmaz: veriyi bu görev çeker ve GitHub Pages'te barındırır.
Uygulama yalnızca seçilen ilçenin dosyasını indirir.

Kullanım (GitHub Actions'ta haftada bir):  python3 -I scripts/fetch_prayer_times.py out/

Çıktı:
  out/places.json            [{"id", "name", "state"}]  (il ve ilçe adları Türkçe büyük/küçük harfe çevrilir)
  out/times/<ilçe id>.json   {"place", "updatedAt", "source", "days": [{"date", "imsak", ..., "hijri"}]}
"""
import datetime
import json
import pathlib
import random
import sys
import time
import urllib.request

BASE = "https://ezanvakti.emushaf.net"
CHECK_BASE = "https://ezanvakti.imsakiyem.com/api/prayer-times"
TURKEY_COUNTRY_ID = 2
FIELDS = {"Imsak": "imsak", "Gunes": "gunes", "Ogle": "ogle", "Ikindi": "ikindi", "Aksam": "aksam", "Yatsi": "yatsi"}
SOURCE = "Diyanet İşleri Başkanlığı"
# Her çalıştırmada mutlaka karşılaştırılan ilçeler (İstanbul, Ankara, İzmir merkez) ve rastgele seçilecek ek ilçe sayısı.
CHECK_ALWAYS = [9541, 9206, 9560]
CHECK_RANDOM = 12


def turkish_title(text):
    """'KADIKÖY' -> 'Kadıköy', 'İSTANBUL' -> 'İstanbul' (Python'un title() işlevi I/İ harflerini bozar)."""
    def lower(s):
        return s.replace("I", "ı").replace("İ", "i").lower()

    def upper(c):
        return {"i": "İ", "ı": "I"}.get(c, c.upper())

    words = []
    for word in text.strip().split():
        low = lower(word)
        words.append(upper(low[0]) + low[1:] if low else low)
    return " ".join(words)


def turkish_key(text):
    """Türk alfabesine göre sıralama anahtarı (Python'un varsayılan sıralaması Ç, İ, Ö, Ş, Ü'yü sona atar)."""
    alphabet = "abcçdefgğhıijklmnoöprsştuüvyz"
    return [alphabet.index(c) if c in alphabet else 100 + ord(c) for c in text.replace("I", "ı").replace("İ", "i").lower()]


def convert_day(row):
    """API'nin günlük satırını uygulamanın biçimine çevirir; eksik ya da bozuk alan varsa hata verir."""
    day = {"date": row["MiladiTarihUzunIso8601"][:10]}
    datetime.date.fromisoformat(day["date"])
    for api_key, key in FIELDS.items():
        value = row[api_key]
        datetime.datetime.strptime(value, "%H:%M")
        day[key] = value
    day["hijri"] = row.get("HicriTarihUzun") or ""
    return day


def place_file(place, rows, now):
    days = sorted((convert_day(r) for r in rows), key=lambda d: d["date"])
    if not days:
        raise ValueError(f"{place['id']} için vakit yok")
    return {"place": place, "updatedAt": now, "source": SOURCE, "days": days}


def get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Insirah-vakit-gorevi"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


def check_against_second_source(place_id, days):
    """İkinci dağıtıcıyla ortak günleri karşılaştırır; farklı günlerin listesini döner."""
    data = get_json(f"{CHECK_BASE}/{place_id}")["data"]
    other = {d["date"][:10]: d["times"] for d in data}
    keys = list(FIELDS.values())
    common = [d for d in days if d["date"] in other]
    if not common:
        raise RuntimeError(f"{place_id}: ikinci kaynakla ortak gün yok")
    return [d["date"] for d in common if [d[k] for k in keys] != [other[d["date"]][k] for k in keys]]


def main():
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()

    places = []
    for state in get_json(f"{BASE}/sehirler/{TURKEY_COUNTRY_ID}"):
        for city in get_json(f"{BASE}/ilceler/{state['SehirID']}"):
            places.append({"id": int(city["IlceID"]), "name": turkish_title(city["IlceAdi"]), "state": turkish_title(state["SehirAdi"])})
        time.sleep(0.2)
    # Diyanet'in listesinde 869 yer var: büyükşehirlerin merkez ilçeleri il adıyla tek kayıttır (ör. "İstanbul").
    if len(places) < 850:
        sys.exit(f"Yalnızca {len(places)} ilçe geldi; beklenen yaklaşık 869. Hiçbir dosya yazılmadı.")

    print(f"{len(places)} yer bulundu; vakitler çekiliyor…", flush=True)
    files, failures = {}, []
    for index, place in enumerate(places, 1):
        if index % 100 == 0:
            print(f"  {index}/{len(places)}", flush=True)
        try:
            files[place["id"]] = place_file(place, get_json(f"{BASE}/vakitler/{place['id']}"), now)
        except Exception as error:  # Bir ilçenin hatası diğerlerini durdurmasın; uygulama o ilçe için önbelleğini kullanır.
            failures.append(f"{place['id']} {place['name']}: {error}")
        time.sleep(0.3)
    if len(failures) > len(places) // 10:
        sys.exit("İlçelerin %10'undan fazlası başarısız oldu. Hiçbir dosya yazılmadı.\n" + "\n".join(failures[:50]))

    # Yayımlamadan önce doğrulama: tek fark bile görevi durdurur.
    sample = [i for i in CHECK_ALWAYS if i in files]
    sample += random.sample([i for i in files if i not in sample], min(CHECK_RANDOM, len(files) - len(sample)))
    mismatches = []
    for place_id in sample:
        bad = check_against_second_source(place_id, files[place_id]["days"])
        if bad:
            mismatches.append(f"{place_id}: {', '.join(bad[:5])}")
        time.sleep(0.3)
    if mismatches:
        sys.exit("İki kaynak arasında vakit farkı var; hiçbir dosya yazılmadı:\n" + "\n".join(mismatches))

    (out / "times").mkdir(parents=True, exist_ok=True)
    for place_id, payload in files.items():
        (out / "times" / f"{place_id}.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (out / "places.json").write_text(json.dumps(sorted(places, key=lambda p: (turkish_key(p["state"]), turkish_key(p["name"]))), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(places)} ilçe, {len(files)} vakit dosyası, {len(sample)} ilçe ikinci kaynakla doğrulandı.")
    if failures:
        print("Hatalar:\n" + "\n".join(failures[:50]))


if __name__ == "__main__":
    main()
