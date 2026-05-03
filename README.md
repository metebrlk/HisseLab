# HisseLab: Algoritmik Trading & Karar Destek Sistemi 📈

HisseLab, Borsa İstanbul (BIST), kripto paralar ve global piyasalar (S&P 500, DAX) için geliştirilmiş, gerçek zamanlı veri analizi ve algoritmik trade imkanı sunan kapsamlı bir Python web uygulamasıdır. 

Sistem, yatırımcılara 20'den fazla teknik indikatörle kendi stratejilerini kurma, geçmişe dönük (backtest) deneme yapma, canlı piyasada sanal portföy (paper trading) yönetme ve Telegram üzerinden anlık sinyal bildirimleri alma imkanı sağlar.

## 🚀 Öne Çıkan Özellikler

*   **Çoklu Piyasa Desteği:** BIST'teki tüm hisseler, popüler kripto paralar (USD pariteleri), S&P 500, DAX ve emtialar tek bir platformda.
*   **Gelişmiş TradingView Entegrasyonu:** Kesintisiz çalışan, profesyonel TradingView Advanced Real-Time Chart widget'ı.
*   **20+ Profesyonel İndikatör:** RSI, MACD, Ichimoku Cloud, Bollinger Bands, Parabolic SAR, Keltner Channel vb.
*   **Detaylı Backtest Motoru:** 
    *   Tarih aralığına göre milimetrik filtreleme.
    *   Dinamik Kâr Al (Take Profit) ve Zarar Durdur (Stop Loss) seviyeleri.
    *   Kazanma oranı (Win Rate), Max Drawdown ve portföy gelişimi analizi.
*   **Sanal Portföy (Paper Trading):** 
    *   Gelen sinyallerle sanal (100.000$) bakiye ile alım/satım yapabilme.
    *   Sabit Kasa (Fixed Position Sizing) ve Maliyet Düşürme (DCA) desteği.
    *   Anlık fiyata göre güncellenen canlı Kâr/Zarar (PnL) tablosu.
*   **Canlı Bot & Bildirim Sistemi:** Kurulan stratejilerin piyasa taraması ve şartlar oluştuğunda anında **Telegram** bildirimi gönderimi.
*   **Supabase Entegrasyonu:** PostgreSQL tabanlı Supabase ile güvenli kullanıcı kimlik doğrulaması (Auth) ve RLS korumalı strateji yönetimi.
*   **Modern ve Dinamik Arayüz:** Streamlit kısıtlamalarını aşan, CSS ve özel JS enjeksiyonlarıyla güçlendirilmiş karanlık tema tasarımı.

## 🛠️ Kullanılan Teknolojiler & Mimari

*   **Backend & Data Science:** Python, Pandas, Numpy, yfinance
*   **Frontend & UI:** Streamlit, Streamlit Components, Plotly, Lightweight Charts
*   **Veritabanı & Auth:** Supabase (PostgreSQL), JSONB
*   **Bildirim Entegrasyonu:** Telegram Bot API

## 📋 Kurulum ve Çalıştırma

Projeyi kendi bilgisayarınızda çalıştırmak için aşağıdaki adımları izleyin:

**1. Depoyu Klonlayın:**
```bash
git clone https://github.com/[KULLANICI_ADINIZ]/hisselab.git
cd hisselab
```

**2. Gerekli Kütüphaneleri Yükleyin:**
```bash
pip install -r requirements.txt
```

**3. Çevre Değişkenlerini Ayarlayın:**
Ana dizinde bir `.env` dosyası oluşturun ve aşağıdaki bilgileri ekleyin:
```env
SUPABASE_URL=[SİZİN_SUPABASE_URL_ADRESİNİZ]
SUPABASE_KEY=[SİZİN_SUPABASE_ANON_KEY_ADRESİNİZ]
TELEGRAM_BOT_TOKEN=[SİZİN_TELEGRAM_BOT_TOKEN_ADRESİNİZ]
```

**4. Veritabanını Kurun (Supabase):**
`schema.sql` dosyasındaki SQL komutlarını Supabase SQL Editor'de çalıştırarak gerekli tabloları (`users`, `strategies`, `paper_portfolio`) ve RLS politikalarını oluşturun.

**5. Uygulamayı Başlatın:**
```bash
streamlit run app.py
```

## 📸 Ekran Görüntüleri

Dashboard Görünümü <img width="1882" height="851" alt="Ekran görüntüsü 2026-05-03 164700" src="https://github.com/user-attachments/assets/13a80c54-0799-4d7f-8ec2-7c8c76043d0b" /><img width="1866" height="905" alt="Ekran görüntüsü 2026-05-03 170243" src="https://github.com/user-attachments/assets/bf34eb7d-e0f4-49bd-b49c-d5d147b0949f" />
Backtest Görünümü <img width="1875" height="882" alt="Ekran görüntüsü 2026-05-03 170405" src="https://github.com/user-attachments/assets/b06d6706-14da-4fec-bc98-a330f7562e5b" />


## 👨‍💻 Geliştirici Notu

Bu proje, finansal piyasalardaki veri yoğunluklu operasyonların, modern web teknolojileri ve güçlü bir veritabanı mimarisi (Supabase) ile nasıl uçtan uca (Full-Stack) bir çözüme dönüştürülebileceğini göstermek amacıyla geliştirilmiştir. Sistemin backtest motoru; zaman dilimi (timezone) farklılıkları, 'lookahead bias' hataları ve durum/kesişim (state vs. crossover) mantıkları gibi algoritmik trade alanındaki kritik mühendislik problemlerini aşacak şekilde özel olarak tasarlanmıştır.
