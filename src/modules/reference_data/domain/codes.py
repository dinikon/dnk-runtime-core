from typing import NewType

# Persisted, normalized natural identifiers of global catalogs.
CountryCode = NewType("CountryCode", str)
CurrencyCode = NewType("CurrencyCode", str)
LocaleCode = NewType("LocaleCode", str)
LocaleRegionCode = NewType("LocaleRegionCode", str)
TimeZoneCode = NewType("TimeZoneCode", str)
