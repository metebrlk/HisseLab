<img width="1875" height="882" alt="Ekran görüntüsü 2026-05-03 170405" src="https://github.com/user-attachments/assets/02d40cb7-3d6e-4cff-8b30-d8e21fee16b7" />
# HisseLab: Algoritmik Trading & Karar Destek Sistemi 📈
HisseLab, Borsa İstanbul (BIST), kripto paralar ve global piyasalar (S&P 500, DAX) için geliştirilmiş, gerçek zamanlı veri analizi ve algoritmik trade imkanı sunan kapsamlı bir Python web uygulamasıdır.

Sistem, yatırımcılara 20'den fazla teknik indikatörle kendi stratejilerini kurma, geçmişe dönük (backtest) deneme yapma, canlı piyasada sanal portföy (paper trading) yönetme ve Telegram üzerinden anlık sinyal bildirimleri alma imkanı sağlar.

🚀 Öne Çıkan Özellikler
Çoklu Piyasa Desteği: BIST'teki tüm hisseler, popüler kripto paralar (USD pariteleri), S&P 500, DAX ve emtialar tek bir platformda.

Gelişmiş TradingView Entegrasyonu: Kesintisiz çalışan, profesyonel TradingView Advanced Real-Time Chart widget'ı (Özel JS entegrasyonu).

20+ Profesyonel İndikatör: RSI, MACD, Ichimoku Cloud, Bollinger Bands, Parabolic SAR, Keltner Channel ve daha fazlası. (Durum kontrolü ve kesişim - Crossover mantıkları dahil).

Detaylı Backtest Motoru:

Tarih aralığına göre milimetrik filtreleme.

Dinamik Kâr Al (Take Profit) ve Zarar Durdur (Stop Loss) seviyeleri.

Kazanma oranı (Win Rate), Max Drawdown ve portföy gelişimi (Equity Curve) analizi.

Gerçekleşen işlemlerin loglandığı "Trade Journal" (İşlem Günlüğü).

Sanal Portföy (Paper Trading):

Gelen sinyallerle veya manuel olarak sanal (100.000$) bakiye ile alım/satım yapabilme.

Sabit Kasa (Fixed Position Sizing - örn: her işlemde 1000$ alım) ve Maliyet Düşürme (DCA) desteği.

Anlık fiyata göre güncellenen canlı Kâr/Zarar (PnL) tablosu.

Canlı Bot & Bildirim Sistemi: Kurulan stratejilerin piyasa taraması ve şartlar oluştuğunda anında Telegram bildirimi gönderimi.

Supabase Entegrasyonu: PostgreSQL tabanlı Supabase ile güvenli kullanıcı kimlik doğrulaması (Auth), RLS (Row Level Security) korumalı portföy ve strateji yönetimi.

Modern ve Dinamik Arayüz: Streamlit kısıtlamalarını aşan, CSS ve özel JS enjeksiyonlarıyla güçlendirilmiş, karanlık tema tabanlı, tepkisel (responsive) tasarım.

🛠️ Kullanılan Teknolojiler & Mimari
Backend & Data Science: Python, Pandas, Numpy, yfinance

Frontend & UI: Streamlit, Streamlit Components (Özel JS/HTML Enjeksiyonu), Plotly, Lightweight Charts

Veritabanı & Auth: Supabase (PostgreSQL), JSONB (Karmaşık strateji parametrelerinin saklanması için)

Bildirim Entegrasyonu: Telegram Bot API

📋 Kurulum ve Çalıştırma
Projeyi kendi bilgisayarınızda çalıştırmak için aşağıdaki adımları izleyin:

1. Depoyu Klonlayın:

Bash
git clone https://github.com/[KULLANICI_ADINIZ]/hisselab.git
cd hisselab
2. Gerekli Kütüphaneleri Yükleyin:

Bash
pip install -r requirements.txt
3. Çevre Değişkenlerini Ayarlayın:
Ana dizinde bir .env dosyası oluşturun ve aşağıdaki bilgileri ekleyin:

Kod snippet'i
SUPABASE_URL=sizin_supabase_url_adresiniz
SUPABASE_KEY=sizin_supabase_anon_key_adresiniz
TELEGRAM_BOT_TOKEN=sizin_telegram_bot_token_adresiniz
4. Veritabanını Kurun (Supabase):
schema.sql dosyasındaki SQL komutlarını Supabase SQL Editor'de çalıştırarak gerekli tabloları (users, strategies, paper_portfolio) ve RLS politikalarını oluşturun.

5. Uygulamayı Başlatın:

Bash
streamlit run app.py
