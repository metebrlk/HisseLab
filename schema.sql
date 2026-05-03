-- ════════════════════════════════════════════════════════════
-- HisseLab SaaS — Tam Optimize Edilmiş SQL Schema (V11.1)
-- ════════════════════════════════════════════════════════════

-- ── 1. USERS TABLOSU ──────────────
CREATE TABLE IF NOT EXISTS public.users (
    id                  UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email               TEXT        NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    subscription_tier   TEXT        DEFAULT 'free' CHECK (subscription_tier IN ('free','premium')),
    telegram_chat_id    TEXT        DEFAULT '', -- Streamlit uyumluluğu için bilerek boş bırakıldı
    preferences         JSONB       DEFAULT '{}'::jsonb -- TEXT'ten JSONB'ye yükseltildi
);

-- ── 2. STRATEGIES TABLOSU ────────────────────
CREATE TABLE IF NOT EXISTS public.strategies (
    id              BIGSERIAL   PRIMARY KEY,
    user_id         UUID        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    symbol          TEXT        NOT NULL,
    indicator       TEXT        NOT NULL DEFAULT 'RSI',
    condition       TEXT        NOT NULL DEFAULT '<',
    threshold       NUMERIC     NOT NULL,
    period          JSONB       NOT NULL DEFAULT '{}'::jsonb, -- TEXT'ten JSONB'ye yükseltildi
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    total_trades    INTEGER     DEFAULT 0,
    success_rate    NUMERIC     DEFAULT 0.0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Performans Indexleri (Worker ve API için)
CREATE INDEX IF NOT EXISTS idx_strategies_active ON public.strategies (is_active, user_id);
CREATE INDEX IF NOT EXISTS idx_strategies_user ON public.strategies (user_id);

-- ── 3. SIGNAL_LOG TABLOSU ──────────────────
CREATE TABLE IF NOT EXISTS public.signal_log (
    id              BIGSERIAL   PRIMARY KEY,
    strategy_id     BIGINT      REFERENCES public.strategies(id) ON DELETE SET NULL,
    user_id         UUID        REFERENCES public.users(id) ON DELETE CASCADE,
    symbol          TEXT,
    indicator       TEXT,
    ind_value       NUMERIC,
    price           NUMERIC,
    triggered_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Performans Indexi
CREATE INDEX IF NOT EXISTS idx_signal_log_user ON public.signal_log (user_id, triggered_at DESC);

-- ── 4. TRADE_HISTORY TABLOSU ───────
CREATE TABLE IF NOT EXISTS public.trade_history (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id         UUID        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    strategy_id     BIGINT      REFERENCES public.strategies(id) ON DELETE SET NULL,
    symbol          TEXT        NOT NULL,
    trade_type      TEXT        NOT NULL CHECK (trade_type IN ('BUY','SELL')), -- Güvenlik kontrolü eklendi
    price           NUMERIC     NOT NULL,
    quantity        NUMERIC     NOT NULL,
    pnl_percentage  NUMERIC,
    executed_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Performans Indexi
CREATE INDEX IF NOT EXISTS idx_trade_history_user ON public.trade_history (user_id, executed_at DESC);

-- ── 5. GÜVENLİK DUVARI (ROW LEVEL SECURITY - RLS) ───────────
ALTER TABLE public.users         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.strategies    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trade_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signal_log    ENABLE ROW LEVEL SECURITY; -- Eksik RLS eklendi

-- Tekilleştirilmiş ve Temizlenmiş Güvenlik Kuralları (Policies)
CREATE POLICY "users_self_manage" ON public.users FOR ALL USING (auth.uid() = id) WITH CHECK (auth.uid() = id);
CREATE POLICY "strategies_self_manage" ON public.strategies FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "trade_history_self_manage" ON public.trade_history FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "signal_log_self_manage" ON public.signal_log FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- ── 6. OTOMATİK PROFİL YARATICI (Auth Trigger) ──────────────
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    INSERT INTO public.users (id, email)
    VALUES (NEW.id, NEW.email)
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();