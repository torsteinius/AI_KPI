import random
import yfinance as yf

class AksjeInfo:
    def __init__(self, ticker=None):
        # Liste over noen norske aksjer fra Oslo Børs
        self.norske_aksjer = ["EQNR.OL", "NHY.OL", "DNB.OL", "TEL.OL", "ORK.OL", "YAR.OL", "MOWI.OL", "AKERBP.OL"]
        
        # Hvis ingen ticker er angitt, velges en tilfeldig norsk aksje
        self.ticker = ticker if ticker else random.choice(self.norske_aksjer)
        self.aksje = yf.Ticker(self.ticker)
        self.data = self.aksje.info

    def hent_nokkeltall(self):
        """
        Henter viktige nøkkeltall for aksjen.
        """
        return {
            "Ticker": self.ticker,
            "Aksjekurs": self.data.get("currentPrice", "Ikke tilgjengelig"),
            "Antall aksjer": self.data.get("sharesOutstanding", "Ikke tilgjengelig"),
            "Markedsverdi": self.data.get("marketCap", "Ikke tilgjengelig"),
            "P/E-forhold": self.data.get("trailingPE", "Ikke tilgjengelig"),
            "Utbytteavkastning": self.data.get("dividendYield", "Ikke tilgjengelig"),
            "Beta": self.data.get("beta", "Ikke tilgjengelig"),
        }

    def vis_info(self):
        """
        Viser aksjeinformasjon i konsollen.
        """
        info = self.hent_nokkeltall()
        print("\nAksjeinformasjon:")
        for key, value in info.items():
            print(f"{key}: {value}")


# Eksempel på bruk
if __name__ == "__main__":
    aksje = AksjeInfo()  # Velger en tilfeldig aksje
    aksje.vis_info()

    spesifikk_aksje = AksjeInfo("REACH.OL")  # Henter info for en spesifikk aksje
    spesifikk_aksje.vis_info()
