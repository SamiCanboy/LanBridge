# ⬡ LanBridge

**LanBridge**, yerel ağınızdaki (LAN) cihazlar arasında metin, dosya ve görselleri anında aktarmanızı sağlayan bulutsuz, ücretsiz ve açık kaynaklı bir P2P (Peer-to-Peer) köprü uygulamasıdır. 

Windows ↔ macOS, Windows ↔ Windows veya macOS ↔ macOS arasında sorunsuzca çalışır. Bir cihazda kopyaladığınız herhangi bir içeriği (metin, görsel veya dosya), diğer cihazın panosuna (clipboard) anında aktarır ve anında yapıştırıp (`Ctrl+V` / `Cmd+V`) kullanmanıza olanak tanır. Gelen dosyalar ve görseller ayrıca bilgisayarınızda otomatik olarak kaydedilir.

## ✨ Özellikler

* **Bulutsuz ve Yerel:** İnternet bağlantısına veya harici bir sunucuya ihtiyaç duymaz. Tüm veri transferi sadece yerel ağınız üzerinden şifresiz/doğrudan gerçekleşir.
* **Anında Pano (Clipboard) Senkronizasyonu:**
  * **Metin:** Bir bilgisayarda kopyalanan metin, anında diğerinin panosuna düşer.
  * **Görsel:** Ekran görüntüsü veya kopyalanan bir görsel, karşı cihaza aktarılır ve doğrudan panoya kopyalanır.
* **Otomatik Kayıt:** Alınan dosyalar ve görseller otomatik olarak ana dizindeki `LanBridge_Alinanlar` klasörüne kaydedilir.
* **Sürükle & Bırak Desteği:** Göndermek istediğiniz dosyaları uygulamanın arayüzüne sürükleyerek anında transfer edebilirsiniz.
* **Arka Planda Çalışma:** Sizi rahatsız etmeden işini yapar, cihazları otomatik olarak bulur ve eşleşir.

---

## 🛠 Kurulum ve Gereksinimler

LanBridge'in çalışabilmesi için cihazınızda **Python 3** yüklü olmalıdır. 

### 1. Python Kontrolü
Terminal (macOS) veya Komut İstemcisi'ni (Windows CMD) açın ve aşağıdaki kodu yazarak Python'ın yüklü olup olmadığını kontrol edin:
```bash
python --version
# veya
python3 --version
