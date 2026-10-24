"""fetch_prayer_times.py dönüşümlerinin testi. Çalıştırma: python3 -I -m unittest discover -s scripts -p 'test_*.py'"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fetch_prayer_times as f  # noqa: E402

# ezanvakti.emushaf.net /vakitler yanıtından bir satır (Diyanet alan adlarıyla).
SAMPLE = {
    "Imsak": "05:53", "Gunes": "07:18", "Ogle": "12:53", "Ikindi": "15:49", "Aksam": "18:19", "Yatsi": "19:38",
    "HicriTarihUzun": "13 Cemaziyelevvel 1448",
    "MiladiTarihKisa": "24.10.2026",
    "MiladiTarihUzunIso8601": "2026-10-24T00:00:00.0000000+03:00",
}


class Tests(unittest.TestCase):
    def test_turkish_title(self):
        self.assertEqual(f.turkish_title("KADIKÖY"), "Kadıköy")
        self.assertEqual(f.turkish_title("İSTANBUL"), "İstanbul")
        self.assertEqual(f.turkish_title("ISPARTA"), "Isparta")
        self.assertEqual(f.turkish_title("AFYONKARAHİSAR"), "Afyonkarahisar")
        self.assertEqual(f.turkish_title("19 MAYIS"), "19 Mayıs")

    def test_convert_day(self):
        self.assertEqual(f.convert_day(SAMPLE), {
            "date": "2026-10-24", "imsak": "05:53", "gunes": "07:18", "ogle": "12:53",
            "ikindi": "15:49", "aksam": "18:19", "yatsi": "19:38", "hijri": "13 Cemaziyelevvel 1448",
        })

    def test_bad_time_is_rejected(self):
        with self.assertRaises(ValueError):
            f.convert_day({**SAMPLE, "Ikindi": "25:99"})
        with self.assertRaises(KeyError):
            f.convert_day({k: v for k, v in SAMPLE.items() if k != "Yatsi"})

    def test_place_file_sorts_days(self):
        later = {**SAMPLE, "MiladiTarihUzunIso8601": "2026-10-25T00:00:00.0000000+03:00"}
        payload = f.place_file({"id": 1, "name": "X", "state": "Y"}, [later, SAMPLE], "now")
        self.assertEqual([d["date"] for d in payload["days"]], ["2026-10-24", "2026-10-25"])
        self.assertEqual(payload["source"], "Diyanet İşleri Başkanlığı")
        with self.assertRaises(ValueError):
            f.place_file({"id": 1, "name": "X", "state": "Y"}, [], "now")

    def test_turkish_sort(self):
        names = ["Şile", "Çatalca", "İstanbul", "Sancaktepe", "Avcılar", "Ilgaz"]
        self.assertEqual(sorted(names, key=f.turkish_key), ["Avcılar", "Çatalca", "Ilgaz", "İstanbul", "Sancaktepe", "Şile"])

    def test_second_source_mismatch_is_reported(self):
        days = [f.convert_day(SAMPLE)]
        same = {"data": [{"date": "2026-10-24T00:00:00.000Z", "times": {k: days[0][k] for k in f.FIELDS.values()}}]}
        original = f.get_json
        try:
            f.get_json = lambda url: same
            self.assertEqual(f.check_against_second_source(9541, days), [])
            same["data"][0]["times"]["aksam"] = "18:20"
            self.assertEqual(f.check_against_second_source(9541, days), ["2026-10-24"])
            f.get_json = lambda url: {"data": []}
            with self.assertRaises(RuntimeError):
                f.check_against_second_source(9541, days)
        finally:
            f.get_json = original


if __name__ == "__main__":
    unittest.main()
