from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from app.modules.agent.schemas import MarketResult

class MarketProvider(ABC):
    """Abstract base class for Mandi market price data providers."""
    
    @abstractmethod
    def get_market_data(self, commodity: str, location: Optional[str] = None) -> MarketResult:
        pass

class DemoMarketProvider(MarketProvider):
    """
    Static APMC Mandi dataset provider for academic final-year project demonstration.
    Clearly flags responses with is_demo_data=True and source='Curated Demo APMC Dataset'.
    """

    STATIC_DATASET: Dict[str, Dict[str, Any]] = {
        "tomato": {
            "commodity": "Tomato",
            "mandi": "Mandya APMC Market",
            "state": "Karnataka",
            "min_price": 1800.0,
            "max_price": 2400.0,
            "modal_price": 2200.0,
            "trend": "Upward (+4.2%)",
            "advisory": "Prices are currently firm due to moderate arrivals. Optimal window for harvesting quality produce."
        },
        "rice": {
            "commodity": "Rice / Paddy (Common)",
            "mandi": "Karnal APMC Grain Market",
            "state": "Haryana",
            "min_price": 2100.0,
            "max_price": 2350.0,
            "modal_price": 2250.0,
            "trend": "Stable",
            "advisory": "Government MSP procurement active. Prices holding steady around modal rates."
        },
        "paddy": {
            "commodity": "Rice / Paddy (Common)",
            "mandi": "Karnal APMC Grain Market",
            "state": "Haryana",
            "min_price": 2100.0,
            "max_price": 2350.0,
            "modal_price": 2250.0,
            "trend": "Stable",
            "advisory": "Government MSP procurement active. Prices holding steady around modal rates."
        },
        "wheat": {
            "commodity": "Wheat (Sharbati / HD)",
            "mandi": "Khanna APMC Market",
            "state": "Punjab",
            "min_price": 2275.0,
            "max_price": 2450.0,
            "modal_price": 2350.0,
            "trend": "Upward (+2.1%)",
            "advisory": "Strong miller demand observed. High-grade grain fetching premium prices."
        },
        "potato": {
            "commodity": "Potato (Jyoti)",
            "mandi": "Agra Central Mandi",
            "state": "Uttar Pradesh",
            "min_price": 1400.0,
            "max_price": 1750.0,
            "modal_price": 1600.0,
            "trend": "Downward (-3.0%)",
            "advisory": "Cold storage arrivals increasing market supply. Consider gradual release."
        },
        "cotton": {
            "commodity": "Raw Cotton (Medium Staple)",
            "mandi": "Rajkot APMC Mandi",
            "state": "Gujarat",
            "min_price": 6800.0,
            "max_price": 7450.0,
            "modal_price": 7150.0,
            "trend": "Stable",
            "advisory": "Textile mill procurement active. Good demand for low-trash lint quality."
        },
        "soybean": {
            "commodity": "Soybean (Yellow)",
            "mandi": "Indore APMC Market",
            "state": "Madhya Pradesh",
            "min_price": 4200.0,
            "max_price": 4650.0,
            "modal_price": 4450.0,
            "trend": "Upward (+1.5%)",
            "advisory": "Solvent extraction plant demand supporting price levels."
        }
    }

    def get_market_data(self, commodity: str, location: Optional[str] = None) -> MarketResult:
        key = commodity.lower().strip() if commodity else "tomato"
        data = self.STATIC_DATASET.get(key)
        
        if not data:
            # Fallback for unlisted commodity
            return MarketResult(
                commodity=commodity.capitalize() if commodity else "Agricultural Crop",
                mandi="Regional APMC Market",
                state="India",
                minimum_price=1800.0,
                maximum_price=2200.0,
                modal_price=2000.0,
                unit="₹ / quintal",
                trend="Stable",
                data_date="2026-03-15",
                source="Curated Demo APMC Dataset",
                is_demo_data=True,
                advisory=f"Estimated APMC market range for {commodity}. Verify locally at regional Mandi."
            )

        return MarketResult(
            commodity=data["commodity"],
            mandi=data["mandi"],
            state=data["state"],
            minimum_price=data["min_price"],
            maximum_price=data["max_price"],
            modal_price=data["modal_price"],
            unit="₹ / quintal",
            trend=data["trend"],
            data_date="2026-03-15",
            source="Curated Demo APMC Dataset",
            is_demo_data=True,
            advisory=data["advisory"]
        )

# Instantiate default provider
default_market_provider = DemoMarketProvider()

def get_market_prices(commodity: str, state_or_mandi: str = "") -> MarketResult:
    """
    Public lookup function for APMC Mandi commodity market prices.
    """
    return default_market_provider.get_market_data(commodity, location=state_or_mandi)

@tool
def market_tool(commodity: str, location: str = "") -> str:
    """Looks up current Mandi market commodity prices (₹/quintal) and trends."""
    res = get_market_prices(commodity, state_or_mandi=location)
    return (
        f"Mandi Price for {res.commodity} at {res.mandi} ({res.state}): "
        f"Modal Price: ₹{res.modal_price:,.0f} / quintal (Range: ₹{res.minimum_price:,.0f} - ₹{res.maximum_price:,.0f}). "
        f"Trend: {res.trend}. Advisory: {res.advisory} (Source: {res.source})"
    )
