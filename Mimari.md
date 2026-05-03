#### BACKEND



1\. Ana Dilimiz: Python (Değişmez Kural)

Backend tarafında dili değiştirmek gibi bir lükse veya ihtiyaca sahip değiliz. Finansal hesaplamalar, Pandas/Numpy kullanımı ve yfinance entegrasyonu için dünyada Python'dan daha iyi bir ekosistem yok. Yazdığın o 20+ indikatör ve backtest motoru Python'da kalmak zorunda.



2\. Backend Çatısı (Framework): Neden FastAPI Seçmeliyiz?

Streamlit'in arayüz özelliklerini çöpe attığımızda, Python kodlarımızı internete açacak (Frontend ile konuşturacak) bir çatıya ihtiyacımız var.



Kesin Kararımız: FastAPI.



Neden Kullanacağız? Adı üstünde, inanılmaz hızlıdır. Modern web'in standardı olan Asenkron (Asynchronous) yapıyı destekler. Frontend'den gelen istekleri sıraya sokup sistemi kilitlemez. Ayrıca yazdığın kodlar için otomatik olarak "Swagger" adında çok şık bir API dokümantasyonu oluşturur (Frontend'i yazarken çok işimize yarayacak).



Alternatifleri Nelerdi, Neden Eledik?



Flask: Çok eskidir ve varsayılan olarak senkron (tek işlemciyi meşgul eden) çalışır. 1000 kullanıcı aynı anda grafiğe tıklarsa Flask boğulur.



Django: Çok güçlüdür ama bir o kadar da hantal ve "kuralları olan" bir devdir. Kendi veritabanı yönetim sistemi (ORM) vardır. Ancak biz halihazırda mükemmel bir şekilde Supabase kullanıyoruz. Django'nun hantallığına ihtiyacımız yok.



3\. Gelecekte Bizi Bekleyen Avantajlar

Tam Bağımsızlık (Decoupling): Backend sadece veri hesaplayıp JSON fırlatan bir fabrikaya dönüşecek. Yarın öbür gün "Ben bunun mobil uygulamasını (iOS/Android) da yapacağım" dersen, Backend koduna tek bir satır bile dokunmayacaksın. Telefonlar doğrudan bu FastAPI motoruna bağlanacak.



Kaynak Tüketiminin Düşmesi: Streamlit her tıklamada tüm sayfayı baştan çalıştırdığı için işlemciyi (CPU) ağlatır. FastAPI ise sadece o an istenen fonksiyonu (örneğin sadece RSI hesaplamasını) çalıştırır. Sunucu maliyetlerin dramatik şekilde düşer.



4\. Yaşayacağımız Dezavantajlar ve Potansiyel Krizler

Geçiş yaparken ve sonrasında başımızı ağrıtacak teknik gerçekler şunlar:



CORS (Cross-Origin Resource Sharing) Belası: Streamlit'te her şey tek sunucudaydı. Şimdi Frontend ayrı bir sunucuda (örn: Vercel), Backend ayrı bir sunucuda (örn: Render) olacak. Tarayıcılar güvenlik gereği iki farklı sunucunun konuşmasını engellemeye çalışır. Bunu FastAPI tarafında özel güvenlik ayarları yazarak aşacağız.



yfinance Darboğazı (Kritik): FastAPI saniyede 10.000 isteği alacak kadar hızlıdır ancak yfinance kütüphanesi çok yavaştır. 50 kişi aynı anda "Backtest" tuşuna basarsa, yfinance Yahoo'dan veriyi çekene kadar FastAPI istekleri bekletmek zorunda kalır. Bu durum ileride bizi ücretli ve profesyonel bir veri sağlayıcı API'sine (Alpaca, Finnhub veya Matriks) geçmeye zorlayacak.



Zaman Aşımı (Timeout) Sorunu: Backtest işlemlerin bazen 5-10 saniye sürebilir. Standart web isteklerinde (HTTP) bir işlem 10 saniyeyi geçerse tarayıcı "Sunucu yanıt vermiyor" deyip bağlantıyı koparır. İleride çok ağır tarama (screener) işlemleri yaparsak, bunları arka planda çalıştıran "Background Tasks" (Celery/Redis) gibi yapılar kurmamız gerekecek.





#### FRONTEND



1\. Ana Teknolojimiz: React ve Next.js

Şu an dünyadaki modern SaaS (Abonelik tabanlı yazılım) projelerinin %90'ı bu ikiliyle yazılıyor.



React.js: Kullanıcı arayüzünü (UI) Lego parçaları gibi inşa etmeni sağlayan kütüphane.



Next.js: React'in üzerine kurulan, sayfalar arası geçişleri, arama motoru optimizasyonunu (SEO) ve hız optimizasyonunu otomatik yapan çatı (Framework).



Neden Bunu Seçiyoruz?

Streamlit'te her tıklamada o 3000 satırlık dosya baştan aşağı okunuyordu. React'te ise sayfa asla yenilenmez (Single Page Application). Kullanıcı sol menüden "İndikatörler" tabına tıkladığında, sayfanın sadece o %10'luk kısmı değişir, grafiğin olduğu %90'lık kısım sabit kalır. Bu, masaüstü uygulaması akıcılığı sağlar.



2\. Bizi Bekleyen Büyük Avantajlar

Lightweight Charts'ın Ana Vatanı: Seninle günlerce Streamlit iframe'leri, 0px çökme hataları ve siyah ekranlarla boğuştuk. Neden? Çünkü JS kütüphanesini Python içine zorla gömmeye çalışıyorduk. React'e geçtiğimizde Lightweight Charts kendi evinde çalışacak. Hata yok, çökme yok, pürüzsüz 60 FPS grafik deneyimi var.



Kusursuz Tasarım (Tailwind CSS \& Shadcn UI): app.py içine yazdığımız o devasa, karmaşık CSS bloklarından kurtulacağız. Modern araçlarla çok daha şık, TradingView veya Binance kalitesinde butonlar, açılır menüler (dropdown) ve bildirimler (toast) yapacağız.



Gerçek Zamanlı Veri (WebSockets): İleride "Fiyatlar kripto borsasındaki gibi saniyede 10 kere yanıp sönsün" dersen, bu yapı Next.js ile çok kolaydır. Streamlit'te bunu yapmak neredeyse imkansızdır.



3\. Yaşayacağımız Dezavantajlar ve Potansiyel Krizler

Sana dürüst davranmalıyım; bu geçiş bir "kopyala-yapıştır" işlemi değil, yeni bir dil ve zihniyet öğrenme sürecidir.



Dil Değişikliği (JavaScript/TypeScript): Artık ön yüzde Python yazmayacaksın. Değişkenleri, döngüleri ve fonksiyonları JavaScript (veya TypeScript) ile yazman gerekecek. Python'un o sade sözdiziminden (syntax) çıkmak ilk başta biraz baş ağrıtabilir.



State Management (Durum Yönetimi) Belası: Streamlit'te st.session\_state yazıp her yerden ulaştığımız o kolay veri hafızası, React'te biraz daha karışıktır. Kullanıcının temasını, portföyünü ve seçtiği hisseyi sayfalar arasında taşımak için useState, useEffect veya Zustand gibi kavramları öğrenmemiz gerekecek.



API Bağlantısı: Streamlit'te veriyi Python'da çekip hemen alt satırda ekrana basıyorduk. Artık Frontend (Next.js), Backend'e (FastAPI) bir haberci (HTTP Request - fetch veya axios) gönderecek, "Bana ASELSAN verisini ver" diyecek. Gelen JSON yanıtını bekleyip, çözüp öyle ekrana çizecek. Bu, iki sistemin birbiriyle konuşmasını sağlama (Entegrasyon) işidir.



Mimarinin Büyük Resmi (Özet)

Eğer bu yola girersek sistemimiz şu 3 ayaktan oluşacak:



Frontend (Vercel'de çalışır): Next.js (Sadece ekranı çizer, butona basılınca Backend'e istek atar).



Backend (Render'da çalışır): FastAPI (Veriyi hesaplar, yfinance ile konuşur, indikatörleri oluşturur).



Veritabanı (Supabase): (Kullanıcı girişleri, stratejiler ve temaları tutar - Buradaki yapımız zaten hazır).

