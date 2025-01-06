import unittest
from unittest.mock import patch, MagicMock
from bond_scraper import BondScraper

class TestBondScraper(unittest.TestCase):
    def setUp(self):
        """Przygotowanie danych przed każdym testem."""
        self.scraper = BondScraper()

    @patch("bond_scraper.webdriver.Chrome")
    def test_scrape_details(self, mock_chrome):
        """Testuje funkcję scrape_details."""
        # Mock przeglądarki
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        # Mock działania Selenium
        mock_driver.page_source = """
        <html>
            <body>
                <table class="notoria-profile">
                    <tr>
                        <td>Rodzaj oprocentowania</td>
                        <td>Stały</td>
                    </tr>
                    <tr>
                        <td>Data wykupu</td>
                        <td>2025-01-01</td>
                    </tr>
                </table>
            </body>
        </html>
        """

        # Wykonanie testu
        result = self.scraper.scrape_details("Bond A")
        self.assertIsNone(result)  # Sprawdzamy, czy wynik to None


    def test_fetch_bonds_no_table(self):
        """Testuje przypadek, gdy na stronie brak tabeli."""
        with patch("bond_scraper.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = "<html><body>No table here</body></html>"
            mock_get.return_value = mock_response

            with self.assertRaises(ValueError):
                self.scraper.fetch_bonds()

    def test_fetch_bonds_invalid_headers(self):
        """Testuje przypadek, gdy brak nagłówków tabeli."""
        with patch("bond_scraper.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = """
            <html>
                <body>
                    <table id="tab-1000">
                        <thead></thead>
                        <tbody></tbody>
                    </table>
                </body>
            </html>
            """
            mock_get.return_value = mock_response

            with self.assertRaises(ValueError):
                self.scraper.fetch_bonds()

if __name__ == "__main__":
    unittest.main()
