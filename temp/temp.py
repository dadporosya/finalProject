import json
import math as _math
from googleapiclient.discovery import build
from google.oauth2 import service_account

print("🚀 СТАРТ")

# === НАСТРОЙКИ ===
SCOPES = ['https://www.googleapis.com/auth/androidpublisher']
SERVICE_ACCOUNT_FILE = 'service-account.json'
PACKAGE_NAME = 'com.Polus.ColouredDoors'

# ─── БАЗОВАЯ ЦЕНА И КУРСЫ ─────────────────────────────────────────────────────
#
#  Вся система строится от цены в EUR.
#  USD и прочие валюты пересчитываются от неё автоматически.
#
# ─────────────────────────────────────────────────────────────────────────────

TARGET_PRICE_EUR = 99.99   # ← Главная переменная. Всё считается от неё.

EUR_TO_USD_RATE  = 1.16    # Курс EUR→USD (1 EUR = X USD). Обновляй вручную
                            # при сильных изменениях курса (~раз в квартал).

USD_MARKUP       = 0.06    # Наценка для USD и привязанных к нему валют (+6%).
                            # Компенсирует волатильность USD и делает
                            # USD-цену немного выше EUR-цены.

# Для API Google Play нужен USD без наценки — чтобы остальные валюты
# масштабировались от реального EUR, а не от завышенного USD.
TARGET_PRICE_USD = TARGET_PRICE_EUR * EUR_TO_USD_RATE

print(f"   Базовая цена: €{TARGET_PRICE_EUR:.2f}")
print(f"   Курс EUR→USD: {EUR_TO_USD_RATE}  |  Наценка USD: +{int(USD_MARKUP*100)}%")
print(f"   Цена для API: ${TARGET_PRICE_USD:.4f}  |  "
      f"USD итог (до тира): ${TARGET_PRICE_EUR * EUR_TO_USD_RATE * (1 + USD_MARKUP):.2f}")

# ─── ЦЕНОВЫЕ ТИРЫ ─────────────────────────────────────────────────────────────
#
#  Чтобы изменить скидку/наценку — меняй только TIER_MULTIPLIERS.
#  Чтобы переместить страну — просто перенеси код в другой тир.
#  Страны не в списке автоматически получают TIER2 (базовая цена).
#
#  TIER1 → +20%   богатые страны
#  TIER2 →   0%   базовая цена (по умолчанию)
#  TIER3 → -20%   развивающиеся рынки
#  TIER4 → -35%   страны с низкой покупательной способностью
#
# ─────────────────────────────────────────────────────────────────────────────

TIER_MULTIPLIERS = {
    "TIER1": 1.20,   # +20%
    "TIER2": 1.00,   #   0%
    "TIER3": 0.90,   # -10%
    "TIER4": 0.75,   # -25%
}

TIER_COUNTRIES = {
    "TIER1": {
        "US", "CA", "AU", "NZ", "GB", "IE",
        "CH", "NO", "SE", "DK", "FI", "LU",
        "DE", "FR", "NL", "BE", "AT", "IT", "ES",
        "SG", "HK", "TW", "JP", "KR", "IL",
        "AE", "SA", "KW", "QA", "OM", "BH",
    },
    "TIER2": {
        "PL", "CZ", "SK", "SI", "HR", "HU",
        "GR", "RO", "BG",
        "LT", "LV", "EE",
        "IS", "LI", "MC", "SM", "VA",
        "CY", "MT",
        "CL", "UY",
        "MY", "GI", "MO",
    },
    "TIER3": {
        "RU", "KZ", "TR",
        "MX", "BR", "AR", "CO", "PE", "EC", "BO", "PY", "VE", "SR", "BZ",
        "ZA",
        "BY", "UA",
        "GE", "AM", "AZ",
        "KG", "UZ", "TJ", "TM",
        "JO", "LB",
        "EG", "MA", "DZ", "TN", "IQ",
        "RS", "BA", "AL", "MK", "MD",
        "CN",
    },
    "TIER4": {
        "IN", "ID", "PH", "TH", "VN",
        "PK", "BD", "NP", "LK", "MM", "KH", "LA", "MN",
        "NG", "KE", "GH", "TZ", "UG", "RW", "SN", "CI",
        "CM", "CD", "MZ", "ZM", "ZW", "NA", "BW", "MU", "SC",
        "FJ", "PG", "WS", "VU", "SB", "TO", "FM",
        "GT", "HN", "SV", "NI", "CR", "PA", "DO", "JM",
        "TT", "BS", "HT", "KN", "LC", "GD", "DM", "AG", "AW",
        "TC", "VG", "KY", "BM",
        "LY",
        "ML", "BF", "NE", "TD", "CF",
        "CG", "GA", "GW", "GN", "SL", "LR", "GM", "TG", "BJ",
        "DJ", "ER", "SO",
        "MV", "KM",
        "YE",
    },
}

# Обратный индекс: region_code → tier_name (строится автоматически)
_REGION_TO_TIER = {
    country: tier
    for tier, countries in TIER_COUNTRIES.items()
    for country in countries
}

def get_tier_multiplier(region_code: str) -> tuple[str, float]:
    """Возвращает (tier_name, multiplier) для региона. Default: TIER2."""
    tier = _REGION_TO_TIER.get(region_code, "TIER2")
    return tier, TIER_MULTIPLIERS[tier]

# ─── МОДЕЛЬ НАЛОГОВ В GOOGLE PLAY ─────────────────────────────────────────────
#
#  DECIMAL-валюты (EUR, GBP, BRL, TRY, DZD, SEK…):
#    Покупатель платит РОВНО ту сумму, что мы отправляем в API.
#
#    Google's convertRegionPrices возвращает цену в двух вариантах:
#      taxInclusive=False → pre-tax база (чистая конвертация без НДС)
#                           → используем напрямую
#      taxInclusive=True  → цена уже включает местный НДС
#                           → делим на (1+tax), чтобы получить
#                              чистую валютную цену без налоговой наценки
#
#    В обоих случаях: округляем до .99/.49 и отправляем.
#    НДС Google вычтет из поступлений разработчика сам.
#
#  STEP-валюты (INR, JPY, RUB, KRW, CRC…):
#    taxInclusive=True  → отправляем rounded(converted).
#    taxInclusive=False → Play Store добавит НДС сверху,
#                         нужно найти base = converted / (1+tax).
#
# ─────────────────────────────────────────────────────────────────────────────

TAX_RATES = {
    # Евросоюз
    "AT": 0.20, "BE": 0.21, "BG": 0.20, "CY": 0.19, "CZ": 0.21,
    "DE": 0.19, "DK": 0.25, "EE": 0.20, "ES": 0.21, "FI": 0.24,
    "FR": 0.20, "GR": 0.24, "HR": 0.25, "HU": 0.27, "IE": 0.23,
    "IT": 0.22, "LT": 0.21, "LU": 0.17, "LV": 0.21, "MT": 0.18,
    "NL": 0.21, "PL": 0.23, "PT": 0.23, "RO": 0.19, "SE": 0.25,
    "SI": 0.22, "SK": 0.20,
    # EEA / Европа вне ЕС
    "CH": 0.077, "IS": 0.24, "LI": 0.077, "NO": 0.25,
    "GB": 0.20, "GI": 0.00, "MC": 0.20, "SM": 0.22, "VA": 0.22,
    "RS": 0.20, "BA": 0.17, "AL": 0.20, "MK": 0.18, "MD": 0.20,
    "BY": 0.20, "UA": 0.20,
    # СНГ
    "RU": 0.20, "KZ": 0.12, "UZ": 0.12, "KG": 0.12,
    "AM": 0.20, "AZ": 0.18, "GE": 0.18, "TJ": 0.15, "TM": 0.15,
    # Азия
    "JP": 0.10, "KR": 0.10, "TW": 0.05, "HK": 0.00, "MO": 0.00,
    "SG": 0.09, "MY": 0.10, "TH": 0.07, "PH": 0.12, "VN": 0.10,
    "ID": 0.11, "IN": 0.18, "BD": 0.15, "LK": 0.18, "NP": 0.13,
    "PK": 0.17, "MM": 0.05, "KH": 0.10, "LA": 0.10, "MN": 0.10,
    # Австралия / Океания
    "AU": 0.10, "NZ": 0.15, "FJ": 0.09, "PG": 0.10,
    "WS": 0.15, "VU": 0.125, "SB": 0.09, "TO": 0.15, "FM": 0.00,
    # Ближний Восток
    "SA": 0.15, "AE": 0.05, "BH": 0.10, "KW": 0.00, "OM": 0.05,
    "QA": 0.00, "JO": 0.16, "IL": 0.17, "IQ": 0.00, "LB": 0.11,
    "YE": 0.05,
    # Африка
    "EG": 0.14, "MA": 0.20, "DZ": 0.19, "TN": 0.19, "LY": 0.00,
    "ZA": 0.15, "NG": 0.075, "KE": 0.16, "GH": 0.125, "TZ": 0.18,
    "UG": 0.18, "RW": 0.18, "SN": 0.18, "CI": 0.18,
    "CM": 0.1925, "CD": 0.16, "MZ": 0.17, "ZM": 0.16, "ZW": 0.15,
    "NA": 0.15, "BW": 0.12, "MU": 0.15, "SC": 0.15,
    "ML": 0.18, "BF": 0.18, "NE": 0.19, "TD": 0.18, "CF": 0.19,
    "CG": 0.18, "GA": 0.18, "GW": 0.15, "GN": 0.18, "SL": 0.15,
    "LR": 0.10, "GM": 0.15, "TG": 0.18, "BJ": 0.18,
    "DJ": 0.10, "ER": 0.05, "SO": 0.00, "MV": 0.16, "KM": 0.10,
    # Северная/Центральная Америка
    "US": 0.00, "CA": 0.05, "MX": 0.16,
    "GT": 0.12, "BZ": 0.125, "HN": 0.15, "SV": 0.13, "NI": 0.15,
    "CR": 0.13, "PA": 0.07, "DO": 0.18, "JM": 0.15, "TT": 0.125,
    "BS": 0.10, "HT": 0.10, "KN": 0.17, "LC": 0.15,
    "GD": 0.15, "DM": 0.15, "AG": 0.15, "AW": 0.02,
    "TC": 0.00, "VG": 0.00, "KY": 0.00, "BM": 0.00,
    # Южная Америка
    "BR": 0.17, "AR": 0.21, "CL": 0.19, "CO": 0.19, "PE": 0.18,
    "EC": 0.12, "BO": 0.13, "PY": 0.10, "UY": 0.22, "VE": 0.16,
    "SR": 0.10,
    # Прочее
    "TR": 0.20,
}

# ─── КЛАССИФИКАЦИЯ ВАЛЮТ ──────────────────────────────────────────────────────

# Паритетные валюты — цена = TARGET_PRICE_EUR × tier_multiplier (курс Google игнорируется).
# EUR, GBP, CHF держатся Google искусственно близко к USD,
# поэтому берём EUR-цену напрямую. TODO
PARITY_CURRENCIES = {"EUR", "GBP", "CHF", "GIP", "BAM", "AZN", "AWG", "BGN"}

# USD и привязанные к нему валюты — считаются от EUR через EUR_TO_USD_RATE + USD_MARKUP
USD_CURRENCIES = {"USD", "CAD", "AUD", "NZD", "SGD", "HKD", "MOP"}

# Дробные валюты без привязки — конвертируются по курсу Google
FRACTIONAL_CURRENCIES = {"USD", "CAD", "AUD", "NZD", "SGD", "HKD", "MOP"}

X99_CURRENCIES = {
    "SEK", "NOK", "DKK", "ISK",
    "PLN", "CZK", "RON", "HRK", "RSD", "ALL", "MKD", "MDL",
    "UAH", "GEL", "AMD", "BYR",
    "BRL", "MXN", "ARS", "PEN", "BOB", "UYU", "VEF",
    "ILS", "MAD", "DZD", "TND", "EGP", "LYD",
    "ZAR", "GHS", "MZN", "NAD", "BWP", "ZMW",
    "TRY", "TTD",
}

END9_STEP = {
    "RUB": 10,
    "INR": 10,
    "KZT": 10,
    "UZS": 100,
    "KGS": 10,
    "TJS": 10,
}

STEP_CURRENCIES = {
    "JPY": 10,   "KRW": 100,  "IDR": 500,  "VND": 1000,
    "THB": 5,    "PHP": 5,    "TWD": 5,    "MYR": 1,
    "PKR": 10,   "BDT": 10,   "LKR": 10,   "NPR": 10,
    "MMK": 100,  "KHR": 1000, "LAK": 1000, "MNT": 100,
    "AED": 1,    "SAR": 1,    "QAR": 1,
    "KWD": 1,    "BHD": 1,    "OMR": 1,    "JOD": 1,
    "IQD": 250,  "YER": 100,
    "NGN": 50,   "KES": 5,    "TZS": 500,  "UGX": 500,
    "RWF": 100,  "ETB": 5,    "GNF": 1000, "SLL": 1000,
    "GMD": 5,    "LRD": 5,    "MUR": 5,    "SCR": 5,
    "DJF": 100,  "KMF": 100,  "HTG": 10,
    "CLP": 50,   "COP": 100,  "PYG": 500,
    "GTQ": 5,    "HNL": 5,    "NIO": 5,
    "CRC": 50,   "DOP": 5,    "JMD": 10,
    "XOF": 100,  "XAF": 100,  "VUV": 100,
    "FJD": 1,    "SBD": 1,    "WST": 1,    "TOP": 1,
    "HUF": 10,   "MVR": 1,    "MWK": 100,
}


# TEST
# exchange rate for exclusion currencies
EXCLUSION_CURRENCIES_EXCHANGE = {
    "BGP": 0.86,
}


# ─── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ──────────────────────────────────────────────────

def _nearest_x99(total_minor: int) -> int:
    """Ближайшее значение, оканчивающееся на .49 или .99 (в минорных единицах)."""
    base = total_minor // 100
    candidates = [
        base * 100 + 49,
        base * 100 + 99,
        (base + 1) * 100 + 49,
    ]
    if base > 0:
        candidates.append((base - 1) * 100 + 99)
    return min(candidates, key=lambda c: abs(c - total_minor))


def _nearest_end9(value: int, step: int) -> int:
    low  = (value // step) * step - 1
    high = low + step
    return low if abs(value - low) <= abs(value - high) else high


def _cents_to_units_nanos(cents: int) -> tuple:
    nanos = cents * 10_000_000
    return nanos // 1_000_000_000, nanos % 1_000_000_000


def _round_step(value_nanos: int, currency: str) -> tuple:
    value = round(value_nanos / 1_000_000_000)
    if currency in END9_STEP:
        return _nearest_end9(value, END9_STEP[currency]), 0
    if currency in STEP_CURRENCIES:
        step = STEP_CURRENCIES[currency]
        return round(value / step) * step, 0
    return value, 0


# ─── ЦЕНООБРАЗОВАНИЕ ──────────────────────────────────────────────────────────

def price_decimal(target_eur: float, converted: dict,
                  tax_inclusive: bool, region_code: str,
                  use_parity: bool, use_usd_markup: bool) -> dict:
    """
    Decimal-валюты (EUR, GBP, CAD, BRL, SEK…).

    Покупатель платит РОВНО то, что мы отправляем.

      use_parity=True     → цена = target_eur (тир уже учтён снаружи).
                            EUR/GBP/CHF берём напрямую от EUR-базы.
      use_usd_markup=True → к конвертированной цене Google добавляем USD_MARKUP.
                            Для CAD, AUD, SGD, HKD и других USD-привязанных.
      иначе               → цена от Google как есть (pre-tax или strip VAT).

    Итог округляем до .99/.49 и отправляем.
    """
    currency = converted["currencyCode"]
    tax_rate = TAX_RATES.get(region_code, 0.0)
    conv_nanos = (int(converted.get("units", 0)) * 1_000_000_000
                  + converted.get("nanos", 0))

    if use_parity:
        # EUR, GBP, CHF… — берём EUR-цену с тиром напрямую
        source_cents = round(target_eur * 100)
        method = f"parity EUR→{currency}"
    elif use_usd_markup:
        # USD, CAD, AUD… — считаем от EUR-базы с наценкой, курс Google не нужен
        source_cents = round(target_eur * (1 + USD_MARKUP) * 100)
        method = f"EUR×{1+USD_MARKUP:.2f} (USD markup)"
    elif tax_inclusive and tax_rate > 0:
        # Остальные decimal-валюты с НДС в цене — убираем налоговую наценку
        source_cents = round(conv_nanos / (1 + tax_rate) / 10_000_000)
        method = f"converted÷{1+tax_rate:.3f} (strip VAT)"
    else:
        # pre-tax или нет налога — берём как есть
        source_cents = round(conv_nanos / 10_000_000)
        method = "converted (pre-tax)"

    consumer_cents = _nearest_x99(source_cents)
    u, n = _cents_to_units_nanos(consumer_cents)
    print(f"         [{method}] {currency} raw={source_cents/100:.2f} "
          f"→ send={consumer_cents/100:.2f}")
    return {"currencyCode": currency, "units": str(u), "nanos": n}


def price_step(converted: dict, tax_inclusive: bool, region_code: str) -> dict:
    """
    Step/end9-валюты (JPY, INR, RUB, KRW, CRC…).

    taxInclusive=True  → отправляем rounded(converted).
    taxInclusive=False → Play Store добавит НДС сверху,
                         ищем base = converted / (1+tax) методом floor/ceil.
    """
    currency = converted["currencyCode"]
    tax_rate = TAX_RATES.get(region_code, 0.0)
    conv_nanos = (int(converted.get("units", 0)) * 1_000_000_000
                  + converted.get("nanos", 0))

    if tax_inclusive or tax_rate == 0:
        u, n = _round_step(conv_nanos, currency)
    else:
        exact_base = conv_nanos / (1 + tax_rate)

        if currency in END9_STEP:
            step_nanos = END9_STEP[currency] * 1_000_000_000
        elif currency in STEP_CURRENCIES:
            step_nanos = STEP_CURRENCIES[currency] * 1_000_000_000
        else:
            step_nanos = 1_000_000_000

        floor_n = _math.floor(exact_base / step_nanos) * step_nanos
        ceil_n  = floor_n + step_nanos

        u_f, n_f = _round_step(floor_n, currency)
        u_c, n_c = _round_step(ceil_n, currency)

        pays_f = (u_f * 1_000_000_000 + n_f) * (1 + tax_rate)
        pays_c = (u_c * 1_000_000_000 + n_c) * (1 + tax_rate)

        u, n = (u_f, n_f) if abs(pays_f - conv_nanos) <= abs(pays_c - conv_nanos) \
               else (u_c, n_c)

    return {"currencyCode": currency, "units": str(u), "nanos": n}


# ─── ПОЛУЧЕНИЕ ЦЕН ────────────────────────────────────────────────────────────

def get_all_region_prices(target_eur: float, target_usd_api: float) -> dict:
    """
    target_eur      — базовая цена в EUR (для паритетных валют)
    target_usd_api  — цена для API = target_eur × EUR_TO_USD_RATE (без USD_MARKUP)
    """
    units = str(int(target_usd_api))
    nanos = int(round((target_usd_api - int(target_usd_api)) * 1_000_000_000))

    print(f"\n💱 Конвертируем ${target_usd_api:.4f} через Google Play API…")
    response = service.monetization().convertRegionPrices(
        packageName=PACKAGE_NAME,
        body={"price": {"currencyCode": "USD", "units": units, "nanos": nanos}}
    ).execute()

    converted = response.get("convertedRegionPrices", {})
    print(f"   Получено регионов: {len(converted)}\n")

    price_map = {}

    for region_code, data in converted.items():
        target_price  = data["price"]
        tax_inclusive = data.get("taxInclusive", False)
        currency      = target_price["currencyCode"]
        tax_rate      = TAX_RATES.get(region_code, 0)

        # ── Тир-множитель ─────────────────────────────────────────────────────
        tier_name, multiplier = get_tier_multiplier(region_code)

        # EUR-цена с тиром (для паритетных валют)
        effective_eur = target_eur * multiplier

        # Масштабируем сконвертированную Google-цену тем же множителем
        raw_nanos    = (int(target_price.get("units", 0)) * 1_000_000_000
                        + target_price.get("nanos", 0))
        scaled_nanos = int(round(raw_nanos * multiplier))
        scaled_price = {
            "currencyCode": currency,
            "units": str(scaled_nanos // 1_000_000_000),
            "nanos": scaled_nanos % 1_000_000_000,
        }
        # ─────────────────────────────────────────────────────────────────────

        raw  = f"{target_price.get('units', 0)}.{str(target_price.get('nanos', 0)).zfill(9)[:2]}"
        flag = "incl" if tax_inclusive else "excl"
        tier_label = f"{tier_name}×{multiplier:.2f}"
        print(f"   [{region_code:2s}] {currency} {raw:>10s} tax={flag}/{int(tax_rate*100)}% [{tier_label}]")

        is_parity      = currency in PARITY_CURRENCIES
        is_usd_related = currency in USD_CURRENCIES
        is_decimal     = is_parity or is_usd_related or currency in X99_CURRENCIES

        if is_decimal:
            price_map[region_code] = price_decimal(
                effective_eur, scaled_price, tax_inclusive, region_code,
                use_parity=is_parity,
                use_usd_markup=is_usd_related and not is_parity)
        else:
            price_map[region_code] = price_step(
                scaled_price, tax_inclusive, region_code)

    return price_map


# === АВТОРИЗАЦИЯ ===
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('androidpublisher', 'v3', credentials=credentials)


def update_products(products: list):
    price_map = get_all_region_prices(TARGET_PRICE_EUR, TARGET_PRICE_USD)
    requests_list = []

    for product_id in products:
        print(f"\n➡️  Обрабатываем продукт: {product_id}")

        product = service.monetization().onetimeproducts().get(
            packageName=PACKAGE_NAME, productId=product_id).execute()

        regions_version = product.get("regionsVersion")
        if not regions_version:
            print(f"   ❌ Нет regionsVersion, пропускаем {product_id}")
            continue

        existing_options = product.get("purchaseOptions", [])
        print(f"   Найдено purchaseOptions: {len(existing_options)}")

        updated_options = []
        for opt in existing_options:
            print(f"   → option: {opt.get('purchaseOptionId')} (state: {opt.get('state')})")

            existing_region_map = {
                cfg["regionCode"]: cfg
                for cfg in opt.get("regionalPricingAndAvailabilityConfigs", [])
            }
            new_regional = []

            for region_code, cfg in existing_region_map.items():
                if region_code in price_map:
                    price    = price_map[region_code]
                    tax_rate = TAX_RATES.get(region_code, 0)
                    n_str    = str(price.get("nanos", 0)).zfill(9)[:2]
                    tax_note = f" [НДС {int(tax_rate*100)}%]" if tax_rate > 0 else ""
                    new_regional.append({**cfg, "price": price, "availability": "AVAILABLE"})
                    print(f"      ✓ {region_code} → {price['currencyCode']} "
                          f"{price['units']}.{n_str}{tax_note}")
                else:
                    new_regional.append(cfg)
                    print(f"      ⚠️  {region_code}: без изменений")

            for region_code, price in price_map.items():
                if region_code not in existing_region_map:
                    tax_rate = TAX_RATES.get(region_code, 0)
                    n_str    = str(price.get("nanos", 0)).zfill(9)[:2]
                    tax_note = f" [НДС {int(tax_rate*100)}%]" if tax_rate > 0 else ""
                    new_regional.append({
                        "regionCode": region_code,
                        "price": price,
                        "availability": "AVAILABLE"
                    })
                    print(f"      + {region_code} → {price['currencyCode']} "
                          f"{price['units']}.{n_str}{tax_note}")

            updated_options.append({
                **opt,
                "regionalPricingAndAvailabilityConfigs": new_regional
            })

        requests_list.append({
            "oneTimeProduct": {
                "packageName": PACKAGE_NAME,
                "productId": product_id,
                "purchaseOptions": updated_options,
            },
            "updateMask": "purchaseOptions",
            "regionsVersion": regions_version,
        })

    if not requests_list:
        print("\n⚠️  Нечего обновлять.")
        return

    body = {"requests": requests_list}

    print("\n📡 Отправляем batchUpdate…")
    response = service.monetization().onetimeproducts().batchUpdate(
        packageName=PACKAGE_NAME, body=body).execute()

    print("✅ ГОТОВО")
    print(json.dumps(response, indent=2, ensure_ascii=False))


# === СПИСОК ПРОДУКТОВ ===
products = [
    'tickets1',
    'tickets2',
]

# === ЗАПУСК ===
update_products(products)
print("\n🏁 ЗАВЕРШЕНО")