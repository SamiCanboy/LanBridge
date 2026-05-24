# ⬡ LanBridge

**LanBridge**, yerel ağınızdaki (LAN) cihazlar arasında metin, dosya ve görselleri anında aktarmanızı sağlayan bulutsuz, ücretsiz ve açık kaynaklı bir P2P (Peer-to-Peer) pano köprüsü uygulamasıdır.

Windows ↔ macOS, Windows ↔ Windows veya macOS ↔ macOS arasında sorunsuzca çalışır. Bir cihazda kopyaladığınız herhangi bir içeriği (metin, görsel veya dosya),
diğer cihazın panosuna (clipboard) anında aktarır. Böylece tek yapmanız gereken hedef cihazda `Ctrl+V` veya `Cmd+V` kombinasyonlarını kullanmaktır.
Gelen tüm dosya ve görseller arka planda otomatik olarak diske de kaydedilir.

---

## ✨ Özellikler

* **Bulutsuz ve Yerel Ağ Tabanlı:** Verileriniz internete çıkmaz, harici sunucuya gitmez. Tamamen yerel ağınız (Wi-Fi veya Ethernet) üzerinden doğrudan ve şifresiz aktarılır.
* **Akıllı Pano Senkronizasyonu:**
  * **Metin (Text):** Bir PC'de kopyalanan metin, anında diğer PC'nin panosuna düşer.
  * **Görsel (Image):** Ekran görüntüsü aldığınızda ya da bir görsel kopyaladığınızda, karşı cihazın panosuna doğrudan kopyalanır (anında yapıştırmaya hazır olur).
  * **Dosya (File):** Kopyalanan dosyalar için karşı cihazda akıllı bir onay paneli belirir.
* **Sürükle & Bırak Desteği:** Göndermek istediğiniz dosyaları uygulamanın arayüzündeki kutuya sürükleyerek saniyeler içinde karşıya iletebilirsiniz.
* **Otomatik Disk Kaydı:** Alınan tüm dosyalar ve görseller, kullanıcının ana dizinindeki `LanBridge_Alinanlar` klasöründe güvenle depolanır.
* **Arka Plan ve Ayrılma Modu (Detach):** Uygulama başlatıldığında terminali meşgul etmez, arka planda sessizce çalışmaya devam eder.

---

## 🛠 Kurulum ve Gereksinimler

LanBridge'in çalışabilmesi için sisteminizde **Python 3** yüklü olmalıdır.

### 1. Python Kontrolü
Terminal (macOS) veya Komut İstemcisi'ni (Windows CMD) açıp Python'ın yüklü olduğunu doğrulayın:

**Windows için:**
```cmd
python --version
```
**macOS için:**
```Bash
python3 --version
```
### 2. Bağımlılıkların Kurulması
Windows CMD ekranı # karakterini yorum satırı olarak algılamadığı için toplu kopyalamalarda hata vermektedir. Ayrıca Windows'ta python3/pip3 yerine python/pip kullanımı varsayılandır.

Sisteminiz için uygun olan bloktaki komutların tamamını kopyalayıp terminalinize yapıştırarak kurulumu hatasız tamamlayabilirsiniz:

**🪟 Windows Kurulum Komutları
Aşağıdaki komut satırlarını Komut İstemcisi'ne (CMD) yapıştırıp çalıştırın:**

```
python -m pip install --upgrade pip
pip install pyperclip Pillow pywin32 pystray
```

**🍎 macOS Kurulum Komutları
Aşağıdaki komut satırlarını Terminal (Terminal.app) ekranına yapıştırıp çalıştırın:**

```Bash
python3 -m pip install --upgrade pip
pip3 install pyperclip Pillow pyobjc-framework-Cocoa pystray
```
Not: Sürükle-bırak özelliğinin tam performanslı çalışabilmesi ve arayüz hatalarının önlenmesi için yukarıdaki paketlere ek olarak tkinterdnd2 kütüphanesi de kurulum listesine dahil edilmiştir.

**🚀 Kullanım
Bu depoyu (repository) cihazınıza indirin veya klonlayın.
Dosyaların bulunduğu klasöre terminal veya CMD üzerinden gidin:**
```
cd 'klasorun_yolu'
```
Uygulamayı her iki cihazda da başlatın:

**Windows için:**
```
python lanbridge.py
```
**macOS için:**
```
python3 lanbridge.py
```
LanBridge aynı ağdaki diğer cihazları otomatik olarak keşfedecek ve ONLINE durumuna geçecektir. Bir cihazda kopyaladığınız her şey anında diğerine akacaktır!

**⚠️ Önemli Uyarılar ve Güvenlik**
**Büyük Dosya Koruması: Kotanızı veya RAM'inizi doldurmamak adına, uygulama 50 MB üzerindeki pano dosyalarında sizden arayüz üzerinden onay bekler.**

**Ağ Güvenliği: LanBridge, yerel ağ içi P2P (soket bağlantısı) kullandığı için verileri şifrelemeden iletir. Bu nedenle halka açık güvensiz Wi-Fi ağlarında**
**(kafe, kütüphane vb.) uygulamayı açık bırakmamanız, yalnızca ev veya güvenli ofis ağlarında kullanmanız önerilir.**
